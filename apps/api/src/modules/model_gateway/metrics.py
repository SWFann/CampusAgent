"""Model Gateway metrics — privacy-safe call and provider-health tracking.

Privacy contract (P7 guide §15):
- Labels NEVER include prompt, user email, raw endpoint with token, or
  private data.
- Only non-sensitive labels are used: provider_type, provider_name,
  status, error_code, host_hash.

Metrics tracked:
- calls_total (counter by provider_type, status)
- latency_ms (summary by provider_type)
- errors_total (counter by error_code)
- provider_health (gauge by provider_name)
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import TypedDict

from .schemas import ProviderHealthStatus


class LatencySummary(TypedDict):
    count: int
    avg: float
    min: int
    max: int


class MetricsSnapshot(TypedDict):
    calls_total: dict[str, int]
    latency_ms: dict[str, LatencySummary]
    errors_total: dict[str, int]
    provider_health: dict[str, str]


class ModelGatewayMetrics:
    """Thread-safe in-memory metrics for model gateway calls.

    All labels are non-sensitive. No prompt/response/user data is ever
    recorded as a label or value.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # calls_total keyed by (provider_type, status)
        self._calls_total: dict[tuple[str, str], int] = defaultdict(int)
        # latency_ms samples keyed by provider_type
        self._latency: dict[str, list[int]] = defaultdict(list)
        # errors_total keyed by error_code
        self._errors_total: dict[str, int] = defaultdict(int)
        # provider_health keyed by provider_name → status string
        self._provider_health: dict[str, str] = {}

    def record_call(
        self,
        *,
        provider_type: str,
        provider_name: str,
        status: str,
        latency_ms: int,
    ) -> None:
        """Record a completed (or failed) model call."""
        with self._lock:
            self._calls_total[(provider_type, status)] += 1
            # Cap stored latency samples to avoid unbounded memory.
            samples = self._latency[provider_type]
            if len(samples) < 10000:
                samples.append(latency_ms)

    def record_error(self, *, error_code: str) -> None:
        """Record an error by stable error code (never by content)."""
        with self._lock:
            self._errors_total[error_code] += 1

    def record_provider_health(
        self,
        *,
        provider_name: str,
        status: ProviderHealthStatus,
    ) -> None:
        """Record the latest health status of a provider."""
        with self._lock:
            self._provider_health[provider_name] = status.value

    # ------------------------------------------------------------------
    # Snapshot / export
    # ------------------------------------------------------------------

    def snapshot(self) -> MetricsSnapshot:
        """Return a non-sensitive snapshot for admin/metrics endpoints."""
        with self._lock:
            calls = {
                f"{ptype}:{status}": count
                for (ptype, status), count in sorted(self._calls_total.items())
            }
            latency_summary: dict[str, LatencySummary] = {}
            for ptype, samples in self._latency.items():
                if samples:
                    latency_summary[ptype] = LatencySummary(
                        count=len(samples),
                        avg=round(sum(samples) / len(samples), 2),
                        min=min(samples),
                        max=max(samples),
                    )
            errors = dict(sorted(self._errors_total.items()))
            health = dict(sorted(self._provider_health.items()))
        return {
            "calls_total": calls,
            "latency_ms": latency_summary,
            "errors_total": errors,
            "provider_health": health,
        }

    def to_prometheus_text(self) -> str:
        """Render metrics as Prometheus-style text (no sensitive labels)."""
        snap = self.snapshot()
        lines: list[str] = []
        lines.append("# TYPE model_gateway_calls_total counter")
        for key, count in snap["calls_total"].items():
            ptype, status = key.split(":", 1)
            lines.append(
                f'model_gateway_calls_total{{provider_type="{ptype}",status="{status}"}} {count}'
            )
        lines.append("# TYPE model_gateway_latency_ms summary")
        for ptype, stats in snap["latency_ms"].items():
            lines.append(
                f'model_gateway_latency_ms{{provider_type="{ptype}",quantile="avg"}} {stats["avg"]}'
            )
        lines.append("# TYPE model_gateway_errors_total counter")
        for code, count in snap["errors_total"].items():
            lines.append(
                f'model_gateway_errors_total{{error_code="{code}"}} {count}'
            )
        lines.append("# TYPE model_gateway_provider_health gauge")
        status_map = {"ONLINE": 1, "DEGRADED": 0, "OFFLINE": -1}
        for name, status in snap["provider_health"].items():
            val = status_map.get(str(status), -1)
            lines.append(
                f'model_gateway_provider_health{{provider_name="{name}"}} {val}'
            )
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._lock:
            self._calls_total.clear()
            self._latency.clear()
            self._errors_total.clear()
            self._provider_health.clear()


# Singleton instance
_metrics: ModelGatewayMetrics | None = None


def get_model_gateway_metrics() -> ModelGatewayMetrics:
    """Get the singleton ModelGatewayMetrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = ModelGatewayMetrics()
    return _metrics


def reset_model_gateway_metrics() -> None:
    """Reset the singleton (for testing)."""
    global _metrics
    _metrics = None
