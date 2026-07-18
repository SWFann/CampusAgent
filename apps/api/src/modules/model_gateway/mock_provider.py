"""Mock Provider — deterministic, offline, reproducible model stand-in.

Used as the default provider for local development, CI, and as a
privacy-safe fallback when real nodes are unhealthy.

Privacy:
- Never logs prompt or response content.
- Output is synthetic and contains no user data.
- Supports delay/failure injection for testing degradation paths.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

from ...db.time import utc_now
from .exceptions import ModelUnavailableError
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

# Default fixed response returned when no response_schema is requested.
_DEFAULT_MOCK_TEXT = "Mock model response (deterministic)."


class MockProvider:
    """Deterministic mock provider with optional delay/failure injection.

    Reproducibility: the same input always yields the same output (seeded by
    a stable hash of the request), so tests are deterministic.

    Args:
        name: provider identifier (default "mock").
        delay_ms: simulated latency in milliseconds (default 0).
        fail_rate: fraction in [0.0, 1.0] of calls that raise (default 0.0).
        fixed_output: optional fixed text returned for plain chat requests.
    """

    def __init__(
        self,
        *,
        name: str = "mock",
        delay_ms: int = 0,
        fail_rate: float = 0.0,
        fixed_output: str | None = None,
    ) -> None:
        self.name = name
        self.provider_type = ProviderType.MOCK
        self.is_external = False
        self._delay_ms = max(0, delay_ms)
        self._fail_rate = max(0.0, min(1.0, fail_rate))
        self._fixed_output = fixed_output or _DEFAULT_MOCK_TEXT
        self._call_count = 0
        self._error_count = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stable_hash(text: str) -> str:
        """Return a stable SHA-256 hex digest for reproducibility."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _maybe_inject_delay(self) -> None:
        if self._delay_ms > 0:
            time.sleep(self._delay_ms / 1000.0)

    def _maybe_inject_failure(self) -> None:
        """Deterministically decide whether to inject a failure.

        Uses a stable hash of the call counter so failure is reproducible
        within a test session while still being controllable by ``fail_rate``.
        """
        if self._fail_rate <= 0.0:
            return
        # Deterministic pseudo-random based on call count.
        bucket = (self._call_count * 2654435761) % 10000 / 10000.0
        if bucket < self._fail_rate:
            self._error_count += 1
            raise ModelUnavailableError(
                details={"provider": self.name, "injected": True}
            )

    @staticmethod
    def _build_structured_response(request: ChatRequest) -> dict[str, Any]:
        """Build a deterministic structured response honouring response_schema.

        The response is synthetic — it never echoes user input. It fills
        common top-level keys with placeholder values so schema validation
        can succeed for typical candidate/summary shapes used by P9.
        """
        schema = request.response_schema or {}
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        result: dict[str, Any] = {}
        for key, spec in properties.items():
            if not isinstance(spec, dict):
                result[key] = None
                continue
            ptype = spec.get("type")
            if ptype == "array":
                result[key] = []
            elif ptype == "object":
                result[key] = {}
            elif ptype == "string":
                result[key] = "mock-value"
            elif ptype in ("integer", "number"):
                result[key] = 0
            elif ptype == "boolean":
                result[key] = False
            else:
                result[key] = None
        # If the schema expects a "candidates" array, provide at least one
        # synthetic candidate so downstream P9 aggregation has something to
        # operate on without depending on real model output.
        if "candidates" in result and isinstance(result["candidates"], list):
            result["candidates"] = [
                {"id": "mock-candidate-1", "name": "Mock 候选", "score": 0.5}
            ]
        return result

    # ------------------------------------------------------------------
    # ModelProvider protocol
    # ------------------------------------------------------------------

    def chat(self, request: ChatRequest) -> ChatResponse:
        """Return a deterministic mock chat response."""
        self._call_count += 1
        self._maybe_inject_delay()
        self._maybe_inject_failure()

        start = time.perf_counter()
        request_id = request.request_id or f"mock-{self._call_count}"

        if request.response_schema is not None:
            content_obj: Any = self._build_structured_response(request)
            content = ResponseContent(type="STRUCTURED", content=content_obj)
        else:
            content = ResponseContent(type="TEXT", content=self._fixed_output)

        latency_ms = int((time.perf_counter() - start) * 1000) + self._delay_ms
        prompt_tokens = sum(len(m.content) // 4 + 1 for m in request.messages)
        completion_tokens = 20

        return ChatResponse(
            request_id=request_id,
            model=request.model or "mock-model",
            status="completed",
            response=content,
            metadata=CallMetadata(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                provider=self.name,
                model=request.model or "mock-model",
            ),
        )

    def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Return a deterministic mock embedding vector."""
        self._call_count += 1
        self._maybe_inject_delay()
        self._maybe_inject_failure()

        start = time.perf_counter()
        dimension = request.dimension or 8
        # Deterministic pseudo-embedding from a hash — no real semantics.
        digest = self._stable_hash(request.text)
        # Expand the hash to fill the requested dimension.
        values: list[float] = []
        for i in range(dimension):
            byte_val = int(digest[(i % len(digest))], 16)
            values.append((byte_val / 15.0) * 2.0 - 1.0)

        latency_ms = int((time.perf_counter() - start) * 1000) + self._delay_ms
        return EmbeddingResponse(
            request_id=request.request_id,
            model=request.model or "mock-embedding",
            status="completed",
            embedding=values,
            dimension=dimension,
            metadata=CallMetadata(
                prompt_tokens=len(request.text) // 4 + 1,
                completion_tokens=None,
                latency_ms=latency_ms,
                provider=self.name,
                model=request.model or "mock-embedding",
            ),
        )

    def health(self) -> ProviderHealth:
        """Mock provider is always online unless injecting failures."""
        now = utc_now().isoformat()
        healthy = self._fail_rate < 1.0
        status = ProviderHealthStatus.ONLINE if healthy else ProviderHealthStatus.OFFLINE
        return ProviderHealth(
            provider_name=self.name,
            healthy=healthy,
            status=status,
            latency_ms=self._delay_ms,
            last_checked=now,
        )

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @property
    def call_count(self) -> int:
        """Number of calls processed (for test assertions)."""
        return self._call_count

    @property
    def error_count(self) -> int:
        """Number of injected failures (for test assertions)."""
        return self._error_count

    def __repr__(self) -> str:
        return (
            f"<MockProvider name={self.name} delay_ms={self._delay_ms} "
            f"fail_rate={self._fail_rate}>"
        )
