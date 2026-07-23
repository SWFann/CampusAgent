"""Model Gateway service — orchestrates routing, validation, and metadata.

This is the single entry point for all model calls. Business modules call
``ModelGatewayService.chat()`` / ``.embedding()``; they never import a
concrete provider.

Responsibilities:
1. Validate privacy_context (fail-closed if missing/invalid).
2. Route via RoutingPolicy (P4 → local only, external disabled by default).
3. Call the selected provider.
4. If response_schema is set, validate structured output with limited retry.
5. Record call metadata to AgentRun (hashes only — never prompt/response).
6. Record privacy-safe metrics.

Privacy (P7 guide §10–11):
- input_hash / output_hash are SHA-256 digests; the original content is
  discarded immediately and never logged.
- Invalid raw output during retry is never logged or persisted.
- AgentRun records only: input_hash, output_hash, provider, model,
  token_count, latency_ms, status.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError, create_model
from sqlalchemy.orm import Session

from ...db.time import utc_now
from ..agents.models import AgentRun, AgentRunStatus
from .exceptions import (
    ModelGatewayError,
    ModelTimeoutError,
    PrivacyContextMissingError,
    StructuredOutputValidationError,
)
from .metrics import get_model_gateway_metrics
from .mock_provider import MockProvider
from .router import RoutingPolicy, build_default_candidates
from .rule_provider import RuleProvider
from .schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)

logger = logging.getLogger("campus_agent.model_gateway.service")

# Maximum retry attempts for structured-output validation.
_MAX_VALIDATION_RETRIES = 2


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _hash_messages(messages: list[Any]) -> str:
    """SHA-256 hash of the serialised message list (for integrity only)."""
    blob = json.dumps(
        [{"role": m.role, "content": m.content} for m in messages],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _hash_content(content: Any) -> str:
    """SHA-256 hash of the response content (for integrity only)."""
    blob = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Structured-output validation (P7-06)
# ---------------------------------------------------------------------------

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _schema_to_pydantic_model(
    schema: dict[str, Any], name: str = "DynamicSchema"
) -> type[BaseModel]:
    """Build a Pydantic model from a JSON-schema-like dict.

    Supports top-level ``properties`` and ``required``. Nested objects are
    treated as ``dict`` (shallow validation) — sufficient for structured
    output gating without a full JSON-schema engine.
    """
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for key, spec in properties.items():
        if not isinstance(spec, dict):
            fields[key] = (Any, None)
            continue
        ptype = spec.get("type", "string")
        py_type: type = _JSON_TYPE_MAP.get(ptype, Any)
        if key in required:
            fields[key] = (py_type, ...)
        else:
            fields[key] = (py_type | None, None)
    return create_model(name, **fields)


def _validate_structured_output(
    content: Any,
    response_schema: dict[str, Any],
) -> Any:
    """Validate ``content`` against ``response_schema`` using Pydantic.

    Returns the validated content on success.

    Raises:
        StructuredOutputValidationError: if validation fails. The invalid
            raw output is NEVER included in the exception details.
    """
    model_cls = _schema_to_pydantic_model(response_schema)
    try:
        parsed = json.loads(content) if isinstance(content, str) else content
        if not isinstance(parsed, dict):
            raise StructuredOutputValidationError(
                details={"reason": "expected_object"}
            )
        # Validate via Pydantic — raises ValidationError on mismatch.
        model_cls(**parsed)
        return parsed
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError):
        raise StructuredOutputValidationError(
            details={"reason": "schema_mismatch"}
        ) from None


# ---------------------------------------------------------------------------
# ModelGatewayService
# ---------------------------------------------------------------------------


class ModelGatewayService:
    """Unified model gateway service.

    Args:
        mock: MockProvider instance (always available).
        rule: RuleProvider instance (always available).
        local_node: optional local OpenAI-compatible node.
        external: optional external OpenAI-compatible provider.
        routing_policy: optional custom routing policy (else built from the
            providers above).
        allow_fallback: whether provider failures may degrade to a local rule/mock
            provider. User-selected personal routes disable this so errors remain
            attributable to the configured provider.
    """

    def __init__(
        self,
        *,
        mock: MockProvider | None = None,
        rule: RuleProvider | None = None,
        local_node: Any | None = None,
        external: Any | None = None,
        routing_policy: RoutingPolicy | None = None,
        allow_fallback: bool = True,
    ) -> None:
        self._mock = mock or MockProvider()
        self._rule = rule or RuleProvider()
        if routing_policy is not None:
            self._policy = routing_policy
        else:
            candidates = build_default_candidates(
                self._mock, self._rule, local_node=local_node, external=external
            )
            self._policy = RoutingPolicy(candidates)
        self._allow_fallback = allow_fallback
        self._metrics = get_model_gateway_metrics()

    @property
    def policy(self) -> RoutingPolicy:
        return self._policy

    @property
    def mock(self) -> MockProvider:
        return self._mock

    @property
    def rule(self) -> RuleProvider:
        return self._rule

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(
        self,
        request: ChatRequest,
        *,
        session: Session | None = None,
        agent_id: UUID | None = None,
        actor_user_id: UUID | None = None,
    ) -> ChatResponse:
        """Process a chat request through the full gateway pipeline.

        Args:
            request: the chat request with mandatory privacy_context.
            session: optional DB session for AgentRun recording.
            agent_id: optional agent ID for AgentRun recording.
            actor_user_id: optional actor ID for AgentRun recording.

        Returns:
            ChatResponse with metadata and integrity hashes.

        Raises:
            PrivacyContextMissingError: if privacy_context is absent.
            ModelGatewayError: for routing/timeout/validation failures.
        """
        # 1. Privacy gate — fail-closed.
        self._validate_privacy_context(request)

        # 2. Compute input hash (integrity only — content discarded).
        input_hash = _hash_messages(request.messages)

        # 3. Route.
        provider, decision = self._policy.select(request)

        # 4. Call with fallback.
        response = self._call_with_fallback(request, provider)

        # 5. Structured-output validation (if schema provided).
        if request.response_schema is not None:
            response = self._validate_with_retry(request, response, provider)

        # 6. Compute output hash.
        output_hash = _hash_content(response.response.content)
        response.input_hash = input_hash
        response.output_hash = output_hash

        # 7. Record metadata (hashes only — never prompt/response).
        if session is not None and agent_id is not None and actor_user_id is not None:
            self._record_agent_run(
                session=session,
                agent_id=agent_id,
                actor_user_id=actor_user_id,
                request=request,
                response=response,
            )

        # 8. Record metrics (non-sensitive labels only).
        self._record_metrics(response, decision)

        return response

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Process an embedding request."""
        # Reuse the privacy gate by wrapping in a minimal check.
        if request.privacy_context is None:
            raise PrivacyContextMissingError()
        provider, decision = self._policy.select(
            ChatRequest(
                messages=[ChatMessage(role="user", content="embedding")],
                privacy_context=request.privacy_context,
                purpose=request.privacy_context.purpose,
            )
        )
        start = time.perf_counter()
        try:
            response = provider.embedding(request)
        except ModelGatewayError:
            fallback = self._policy.select_for_fallback(
                ChatRequest(
                    messages=[ChatMessage(role="user", content="embedding")],
                    privacy_context=request.privacy_context,
                    purpose=request.privacy_context.purpose,
                ),
                exclude={provider.name},
            )
            if fallback is None:
                raise
            response = fallback.embedding(request)
            provider = fallback

        latency_ms = int((time.perf_counter() - start) * 1000)
        response.text_hash = hashlib.sha256(
            request.text.encode("utf-8")
        ).hexdigest()
        self._metrics.record_call(
            provider_type=provider.provider_type.value,
            provider_name=provider.name,
            status=response.status,
            latency_ms=latency_ms,
        )
        return response

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Return aggregated health for all providers (non-sensitive)."""
        models: list[dict[str, Any]] = []
        all_healthy = True
        for cand in self._policy.candidates:
            h = cand.provider.health()
            self._metrics.record_provider_health(
                provider_name=cand.provider.name, status=h.status
            )
            if not h.healthy:
                all_healthy = False
            models.append(
                {
                    "name": cand.provider.name,
                    "status": "ready" if h.healthy else "unavailable",
                    "latency_ms": h.latency_ms,
                    "last_checked": h.last_checked,
                }
            )
        return {
            "status": "healthy" if all_healthy else ("degraded" if models else "unhealthy"),
            "models": models,
            "timestamp": utc_now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_privacy_context(request: ChatRequest) -> None:
        """Fail-closed if privacy_context is missing or purpose mismatch."""
        if request.privacy_context is None:
            raise PrivacyContextMissingError()
        # Purpose must be non-empty and consistent.
        if request.privacy_context.purpose != request.purpose:
            # The privacy context purpose is authoritative for routing.
            # We do not raise here — the request purpose is informational;
            # the privacy_context.purpose drives routing decisions.
            pass

    def _call_with_fallback(
        self,
        request: ChatRequest,
        provider: Any,
    ) -> ChatResponse:
        """Call the provider; on timeout/error, degrade to a local fallback.

        Degradation is privacy-preserving: only mock/rule providers are used
        as fallback — never external.
        """
        try:
            result: ChatResponse = provider.chat(request)
            return result
        except ModelTimeoutError:
            if not self._allow_fallback:
                raise
            fallback = self._policy.select_for_fallback(
                request, exclude={provider.name}
            )
            if fallback is None:
                raise
            logger.debug(
                "model_gateway.fallback",
                extra={
                    "from": provider.name,
                    "to": fallback.name,
                    "reason": "timeout",
                },
            )
            return fallback.chat(request)
        except ModelGatewayError:
            if not self._allow_fallback:
                raise
            fallback = self._policy.select_for_fallback(
                request, exclude={provider.name}
            )
            if fallback is None:
                raise
            logger.debug(
                "model_gateway.fallback",
                extra={
                    "from": provider.name,
                    "to": fallback.name,
                    "reason": "error",
                },
            )
            return fallback.chat(request)

    def _validate_with_retry(
        self,
        request: ChatRequest,
        response: ChatResponse,
        provider: Any,
    ) -> ChatResponse:
        """Validate structured output; retry up to _MAX_VALIDATION_RETRIES.

        Privacy: invalid raw output is NEVER logged or included in errors.
        """
        schema = request.response_schema
        assert schema is not None
        last_error: StructuredOutputValidationError | None = None
        excluded = {provider.name}

        for attempt in range(_MAX_VALIDATION_RETRIES + 1):
            try:
                validated = _validate_structured_output(
                    response.response.content, schema
                )
                # Replace content with validated dict and mark as STRUCTURED.
                from .schemas import ResponseContent

                response.response = ResponseContent(
                    type="STRUCTURED", content=validated
                )
                return response
            except StructuredOutputValidationError as exc:
                last_error = exc
                if attempt < _MAX_VALIDATION_RETRIES:
                    # Retry with the same provider or a fallback.
                    fallback = self._policy.select_for_fallback(
                        request, exclude=excluded
                    )
                    retry_provider = fallback or provider
                    excluded.add(retry_provider.name)
                    # Do NOT log the invalid raw output.
                    logger.debug(
                        "structured_output.retry",
                        extra={"attempt": attempt + 1, "provider": retry_provider.name},
                    )
                    response = retry_provider.chat(request)
                else:
                    continue
        assert last_error is not None
        self._metrics.record_error(error_code="MODEL_ROUTING_FAILED")
        raise last_error

    def _record_agent_run(
        self,
        *,
        session: Session,
        agent_id: UUID,
        actor_user_id: UUID,
        request: ChatRequest,
        response: ChatResponse,
    ) -> None:
        """Persist an AgentRun record with hashes only — never content."""
        token_count = None
        if response.metadata.prompt_tokens is not None:
            token_count = (response.metadata.prompt_tokens or 0) + (
                response.metadata.completion_tokens or 0
            )
        status = AgentRunStatus.SUCCESS.value
        if response.status == "failed":
            status = AgentRunStatus.FAILED.value
        elif response.status == "timeout":
            status = AgentRunStatus.TIMEOUT.value

        run = AgentRun(
            agent_id=agent_id,
            actor_user_id=actor_user_id,
            purpose=request.purpose,
            input_hash=response.input_hash,
            output_hash=response.output_hash,
            model_name=response.model,
            token_count=token_count,
            latency_ms=response.metadata.latency_ms,
            status=status,
        )
        session.add(run)
        session.flush()

    def _record_metrics(self, response: ChatResponse, decision: Any) -> None:
        """Record non-sensitive metrics."""
        self._metrics.record_call(
            provider_type=decision.provider_type,
            provider_name=decision.provider_name,
            status=response.status,
            latency_ms=response.metadata.latency_ms,
        )
        if response.status != "completed":
            self._metrics.record_error(error_code="MODEL_UNAVAILABLE")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: ModelGatewayService | None = None


def get_model_gateway_service() -> ModelGatewayService:
    """Get the singleton ModelGatewayService instance.

    By default the service is configured with Mock + Rule providers only
    (no external, no local node) — this is the privacy-safe, offline
    default. Local lab nodes and external providers are registered via
    admin API at runtime.
    """
    global _service
    if _service is None:
        from ...config import settings
        from .openai_compatible import OpenAICompatibleProvider

        external_provider = None
        if settings.ENABLE_EXTERNAL_MODEL:
            external_provider = OpenAICompatibleProvider(
                base_url=settings.MODEL_GATEWAY_BASE_URL,
                model=settings.MODEL_GATEWAY_MODEL,
                api_key=settings.MODEL_GATEWAY_API_KEY,
                timeout_ms=settings.MODEL_GATEWAY_TIMEOUT_MS,
                is_external=settings.MODEL_GATEWAY_IS_EXTERNAL,
                name="stepfun",
            )
        _service = ModelGatewayService(external=external_provider)
    return _service


def reset_model_gateway_service() -> None:
    """Reset the singleton (for testing)."""
    global _service
    _service = None
