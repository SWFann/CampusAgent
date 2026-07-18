"""Node health checking with circuit breaker.

Implements (P7 guide §13):
- Timeout-bounded health probes.
- Circuit breaker: repeated failures open the circuit → OFFLINE.
- Heartbeat tracking with last_heartbeat_at.
- State machine: ONLINE → DEGRADED → OFFLINE → (recovery) → ONLINE.

Privacy: health probes never log endpoint, credential, or request content.
Only status and latency are recorded.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from ...db.time import utc_now
from .models import ModelNode, NodeHealthStatus

logger = logging.getLogger("campus_agent.nodes.health")

# Circuit-breaker thresholds.
_FAILURE_THRESHOLD = 3  # consecutive failures to open the circuit.
_RECOVERY_TIMEOUT_SECONDS = 60  # cool-down before half-open probe.
_HEALTH_TIMEOUT_SECONDS = 5.0


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    """Per-node circuit breaker.

    - CLOSED: requests flow normally; failures increment the counter.
    - OPEN: requests are rejected immediately; after ``recovery_timeout``
      the breaker moves to HALF_OPEN.
    - HALF_OPEN: a single probe is allowed; success → CLOSED, failure → OPEN.
    """

    failure_threshold: int = _FAILURE_THRESHOLD
    recovery_timeout: float = _RECOVERY_TIMEOUT_SECONDS
    _failure_count: int = 0
    _state: CircuitState = CircuitState.CLOSED
    _last_failure_at: float | None = field(default=None, repr=False)

    @property
    def state(self) -> CircuitState:
        """Current state, transitioning OPEN → HALF_OPEN after cool-down."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_at is not None
            and time.monotonic() - self._last_failure_at >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Return True if a request/probe is permitted."""
        state = self.state
        return state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful call — resets the breaker to CLOSED."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_at = None

    def record_failure(self) -> None:
        """Record a failed call — may open the circuit."""
        self._failure_count += 1
        self._last_failure_at = time.monotonic()
        if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset to CLOSED (for testing)."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_at = None


class NodeHealthChecker:
    """Health checker that probes node endpoints with circuit breakers.

    The checker maintains one ``CircuitBreaker`` per node ID. Probes are
    timeout-bounded HTTP GETs to ``{endpoint}/v1/models`` (OpenAI-compatible
    health endpoint used by vLLM/llama.cpp).
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = _HEALTH_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._transport = transport
        self._breakers: dict[str, CircuitBreaker] = {}

    def _breaker(self, node_id: str) -> CircuitBreaker:
        if node_id not in self._breakers:
            self._breakers[node_id] = CircuitBreaker()
        return self._breakers[node_id]

    def check(self, node: ModelNode, *, decrypted_endpoint: str) -> dict[str, Any]:
        """Probe a node and return a health-check result dict.

        Args:
            node: the ModelNode ORM record.
            decrypted_endpoint: the decrypted endpoint URL (plaintext, used
                only for the outbound probe — never logged).

        Returns:
            dict with: status, checks, latency_ms, checked_at, circuit_state.
        """
        breaker = self._breaker(str(node.id))
        now = utc_now()
        checked_at = now.isoformat()

        # If the circuit is open, skip the probe and report OFFLINE.
        if not breaker.allow_request():
            return {
                "status": NodeHealthStatus.OFFLINE.value,
                "checks": {"model_gateway": "skipped"},
                "latency_ms": 0,
                "checked_at": checked_at,
                "circuit_state": breaker.state.value,
            }

        start = time.perf_counter()
        checks: dict[str, str] = {}
        healthy = False

        try:
            kwargs: dict[str, Any] = {"timeout": httpx.Timeout(self._timeout)}
            if self._transport is not None:
                kwargs["transport"] = self._transport
            with httpx.Client(**kwargs) as client:
                # Probe the OpenAI-compatible /v1/models endpoint.
                probe_url = decrypted_endpoint.rstrip("/") + "/models"
                resp = client.get(probe_url)
            latency_ms = int((time.perf_counter() - start) * 1000)
            if resp.status_code == 200:
                checks["model_gateway"] = "passed"
                checks["endpoint_reachable"] = "passed"
                healthy = True
                breaker.record_success()
            else:
                checks["model_gateway"] = f"failed:{resp.status_code}"
                checks["endpoint_reachable"] = "passed"
                breaker.record_failure()
        except httpx.TimeoutException:
            latency_ms = int((time.perf_counter() - start) * 1000)
            checks["model_gateway"] = "timeout"
            breaker.record_failure()
        except httpx.HTTPError:
            latency_ms = int((time.perf_counter() - start) * 1000)
            checks["model_gateway"] = "error"
            breaker.record_failure()
        except Exception:
            latency_ms = int((time.perf_counter() - start) * 1000)
            checks["model_gateway"] = "error"
            breaker.record_failure()

        # Determine status from breaker state and probe result.
        breaker_state = breaker.state
        if healthy and breaker_state == CircuitState.CLOSED or healthy and breaker_state == CircuitState.HALF_OPEN:
            status = NodeHealthStatus.ONLINE.value
        elif breaker_state == CircuitState.OPEN:
            status = NodeHealthStatus.OFFLINE.value
        else:
            # CLOSED or HALF_OPEN with a failure → degraded.
            status = NodeHealthStatus.DEGRADED.value

        return {
            "status": status,
            "checks": checks,
            "latency_ms": latency_ms,
            "checked_at": checked_at,
            "circuit_state": breaker_state.value,
        }

    def get_breaker_state(self, node_id: str) -> CircuitState:
        """Return the current circuit-breaker state for a node."""
        return self._breaker(node_id).state

    def reset_breaker(self, node_id: str) -> None:
        """Force-reset a node's breaker (for testing / admin override)."""
        self._breaker(node_id).reset()

    def record_call_success(self, node_id: str) -> None:
        """Record a successful real call (updates breaker without probing)."""
        self._breaker(node_id).record_success()

    def record_call_failure(self, node_id: str) -> None:
        """Record a failed real call (updates breaker without probing)."""
        self._breaker(node_id).record_failure()


# Singleton
_checker: NodeHealthChecker | None = None


def get_node_health_checker() -> NodeHealthChecker:
    """Get the singleton NodeHealthChecker."""
    global _checker
    if _checker is None:
        _checker = NodeHealthChecker()
    return _checker


def reset_node_health_checker() -> None:
    """Reset the singleton (for testing)."""
    global _checker
    _checker = None
