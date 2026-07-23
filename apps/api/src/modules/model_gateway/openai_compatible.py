"""OpenAI-compatible provider adapter.

Speaks the OpenAI Chat Completions / Embeddings HTTP protocol so it is
compatible with vLLM and llama.cpp server backends without depending on any
vendor SDK. Only ``httpx`` (already a project dependency) is used.

Security (P7 guide §8):
- ``api_key`` is stored as ``SecretStr`` and never appears in ``repr`` or logs.
- Request and response bodies are NEVER logged.
- Only a host hash of the endpoint is recorded for observability — never the
  full URL with query/token.

The adapter is disabled by default (``is_external=True``) so the routing
policy rejects it unless ``allow_external`` is explicitly set. Local lab
nodes (vLLM/llama.cpp on the campus k8s cluster) should be registered with
``is_external=False``.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import SecretStr

from ...db.time import utc_now
from .exceptions import ExternalProviderError, ModelTimeoutError
from .providers import ProviderType
from .schemas import (
    CallMetadata,
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderHealth,
    ProviderHealthStatus,
    ResponseContent,
)

logger = logging.getLogger("campus_agent.model_gateway.openai_compatible")

# Retry defaults
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_RETRY_BACKOFF_MS = 200


def _host_hash(base_url: str) -> str:
    """Return a non-reversible hash of the endpoint host for observability.

    Never includes path, query, or userinfo — only a SHA-256 of the host.
    """
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:16]


def _add_json_only_instruction(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a retry payload that asks for JSON without response_format.

    Some OpenAI-compatible providers implement chat completions but do not
    accept the newer ``json_schema`` response_format parameter. The fallback
    keeps privacy behavior identical while relying on prompt instruction plus
    downstream schema validation.
    """
    retry_payload = dict(payload)
    retry_payload.pop("response_format", None)
    messages = [
        dict(message)
        for message in retry_payload.get("messages", [])
        if isinstance(message, dict)
    ]
    instruction = (
        "\n\n请只返回一个 JSON 对象，不要使用 Markdown，不要添加解释文字。"
    )
    if messages:
        messages[-1]["content"] = f"{messages[-1].get('content', '')}{instruction}"
    else:
        messages.append({"role": "user", "content": instruction.strip()})
    retry_payload["messages"] = messages
    return retry_payload


def _safe_upstream_error_details(resp: httpx.Response, host_hash: str) -> dict[str, Any]:
    """Keep only non-sensitive machine-readable upstream error metadata."""
    details: dict[str, Any] = {"host_hash": host_hash, "status": resp.status_code}
    try:
        payload = resp.json()
    except Exception:
        return details
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return details
    for source_key, target_key in (("code", "upstream_code"), ("type", "upstream_type")):
        value = error.get(source_key)
        if isinstance(value, str) and 0 < len(value) <= 80:
            details[target_key] = value
    return details


class OpenAICompatibleProvider:
    """HTTP adapter for OpenAI-compatible endpoints (vLLM / llama.cpp).

    Args:
        base_url: e.g. ``http://vllm.inference.svc.cluster.local:8000/v1``.
        model: default model name sent in the request body.
        api_key: bearer token (SecretStr — never logged).
        timeout_ms: per-request timeout.
        max_retries: number of retries on transient errors (5xx / network).
        is_external: when True (default) the routing policy treats this as an
            external provider and blocks it unless ``allow_external`` is set.
            Set to False for local campus-lab nodes.
        name: provider identifier.
        transport: optional ``httpx`` transport for testing (MockTransport).
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | SecretStr = "",
        timeout_ms: int = 30000,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        is_external: bool = True,
        name: str = "openai_compatible",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.name = name
        self.provider_type = ProviderType.OPENAI_COMPATIBLE
        self.is_external = is_external
        self._base_url = base_url.rstrip("/")
        self._model = model
        if isinstance(api_key, SecretStr):
            self._api_key = api_key
        else:
            self._api_key = SecretStr(api_key or "")
        self._timeout_ms = max(100, timeout_ms)
        self._max_retries = max(0, max_retries)
        self._host_hash = _host_hash(base_url)
        self._transport = transport
        self._call_count = 0
        self._error_count = 0
        self._last_health: ProviderHealth | None = None

    # ------------------------------------------------------------------
    # Internal HTTP helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.Client:
        """Build a short-lived httpx client.

        A fresh client per call avoids shared connection state and keeps the
        SecretStr out of any global pool. The ``transport`` param is used
        only for testing.
        """
        kwargs: dict[str, Any] = {
            "timeout": httpx.Timeout(self._timeout_ms / 1000.0),
        }
        if self._transport is not None:
            kwargs["transport"] = self._transport
        return httpx.Client(**kwargs)

    def _auth_headers(self) -> dict[str, str]:
        """Return Authorization header. The key value never enters logs."""
        key = self._api_key.get_secret_value()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _request_with_retry(
        self,
        *,
        url: str,
        payload: dict[str, Any],
    ) -> httpx.Response:
        """POST with bounded retry on transient errors.

        Privacy: payload (request body) is never logged. Only the host hash
        and HTTP status are recorded at debug level.
        """
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                with self._client() as client:
                    resp = client.post(url, json=payload, headers=self._auth_headers())
                # Retry on 5xx (transient server errors).
                if 500 <= resp.status_code < 600 and attempt < self._max_retries:
                    logger.debug(
                        "openai_compatible.retry",
                        extra={
                            "host_hash": self._host_hash,
                            "status": resp.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                    time.sleep(_DEFAULT_RETRY_BACKOFF_MS / 1000.0 * (attempt + 1))
                    continue
                return resp
            except httpx.TimeoutException as exc:
                last_exc = exc
                self._error_count += 1
                if attempt < self._max_retries:
                    time.sleep(_DEFAULT_RETRY_BACKOFF_MS / 1000.0 * (attempt + 1))
                    continue
                raise ModelTimeoutError(
                    details={"host_hash": self._host_hash, "timeout_ms": self._timeout_ms}
                ) from None
            except httpx.HTTPError as exc:
                last_exc = exc
                self._error_count += 1
                if attempt < self._max_retries:
                    time.sleep(_DEFAULT_RETRY_BACKOFF_MS / 1000.0 * (attempt + 1))
                    continue
                raise ExternalProviderError(
                    message="外部模型供应商连接失败",
                    details={"host_hash": self._host_hash},
                ) from None
        # Should not reach here, but satisfy the type checker.
        raise ExternalProviderError(
            message="外部模型供应商连接失败",
            details={"host_hash": self._host_hash, "last_error": str(last_exc)},
        )

    # ------------------------------------------------------------------
    # ModelProvider protocol
    # ------------------------------------------------------------------

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Call ``/v1/chat/completions`` and map to ChatResponse."""
        self._call_count += 1
        start = time.perf_counter()
        request_id = request.request_id or f"oai-{self._call_count}"

        payload: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "schema": request.response_schema,
            }

        url = f"{self._base_url}/chat/completions"
        resp = self._request_with_retry(url=url, payload=payload)

        if (
            resp.status_code in (400, 422)
            and request.response_schema is not None
            and "response_format" in payload
        ):
            resp = self._request_with_retry(
                url=url,
                payload=_add_json_only_instruction(payload),
            )

        if resp.status_code != 200:
            self._error_count += 1
            raise ExternalProviderError(
                message="外部模型供应商返回错误",
                details=_safe_upstream_error_details(resp, self._host_hash),
            )

        try:
            data = resp.json()
        except Exception:
            self._error_count += 1
            raise ExternalProviderError(
                message="外部模型供应商返回非法 JSON",
                details={"host_hash": self._host_hash, "status": resp.status_code},
            ) from None

        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        raw_content = message.get("content", "")
        usage = data.get("usage") or {}

        # Determine if structured output was requested.
        if request.response_schema is not None:
            import json

            try:
                parsed = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
            except (json.JSONDecodeError, TypeError):
                self._error_count += 1
                raise ExternalProviderError(
                    message="外部模型供应商返回的结构化输出无法解析",
                    details={"host_hash": self._host_hash},
                ) from None
            content = ResponseContent(type="STRUCTURED", content=parsed)
        else:
            content = ResponseContent(type="TEXT", content=raw_content)

        latency_ms = int((time.perf_counter() - start) * 1000)
        model_name = data.get("model") or payload["model"]

        return ChatResponse(
            request_id=request_id,
            model=model_name,
            status="completed",
            response=content,
            metadata=CallMetadata(
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                latency_ms=latency_ms,
                provider=self.name,
                model=model_name,
            ),
        )

    def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Call ``/v1/embeddings`` and map to EmbeddingResponse."""
        self._call_count += 1
        start = time.perf_counter()

        payload: dict[str, Any] = {
            "model": request.model or self._model,
            "input": request.text,
        }
        url = f"{self._base_url}/embeddings"
        resp = self._request_with_retry(url=url, payload=payload)

        if resp.status_code != 200:
            self._error_count += 1
            raise ExternalProviderError(
                message="外部模型供应商返回错误",
                details={"host_hash": self._host_hash, "status": resp.status_code},
            )

        try:
            data = resp.json()
        except Exception:
            self._error_count += 1
            raise ExternalProviderError(
                message="外部模型供应商返回非法 JSON",
                details={"host_hash": self._host_hash},
            ) from None

        embeddings = data.get("data") or []
        vector = embeddings[0].get("embedding", []) if embeddings else []
        usage = data.get("usage") or {}
        latency_ms = int((time.perf_counter() - start) * 1000)
        model_name = data.get("model") or payload["model"]

        return EmbeddingResponse(
            request_id=request.request_id,
            model=model_name,
            status="completed",
            embedding=list(vector),
            dimension=len(vector),
            metadata=CallMetadata(
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=None,
                latency_ms=latency_ms,
                provider=self.name,
                model=model_name,
            ),
        )

    def health(self) -> ProviderHealth:
        """Probe ``/v1/models`` (or the base) to determine health."""
        try:
            with self._client() as client:
                resp = client.get(
                    f"{self._base_url}/models",
                    headers=self._auth_headers(),
                )
            healthy = resp.status_code == 200
            status = ProviderHealthStatus.ONLINE if healthy else ProviderHealthStatus.DEGRADED
            self._last_health = ProviderHealth(
                provider_name=self.name,
                healthy=healthy,
                status=status,
                latency_ms=int(resp.elapsed.total_seconds() * 1000),
                last_checked=utc_now().isoformat(),
            )
            return self._last_health
        except httpx.TimeoutException:
            self._error_count += 1
            self._last_health = ProviderHealth(
                provider_name=self.name,
                healthy=False,
                status=ProviderHealthStatus.OFFLINE,
                latency_ms=self._timeout_ms,
                last_checked=utc_now().isoformat(),
            )
            return self._last_health
        except httpx.HTTPError:
            self._error_count += 1
            self._last_health = ProviderHealth(
                provider_name=self.name,
                healthy=False,
                status=ProviderHealthStatus.OFFLINE,
                last_checked=utc_now().isoformat(),
            )
            return self._last_health

    # ------------------------------------------------------------------
    # Properties / repr
    # ------------------------------------------------------------------

    @property
    def host_hash(self) -> str:
        """Non-reversible host hash for metrics/observability."""
        return self._host_hash

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def __repr__(self) -> str:
        # api_key is intentionally absent — never appear in repr.
        return (
            f"<OpenAICompatibleProvider name={self.name} "
            f"model={self._model} host_hash={self._host_hash} "
            f"is_external={self.is_external}>"
        )
