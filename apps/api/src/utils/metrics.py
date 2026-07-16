"""
Basic observability metrics for CampusAgent API.

This module provides:
- ``RequestMetrics``: in-memory request counter and latency tracker.
- ``MetricsMiddleware``: middleware that records request metrics.
- A ``/metrics`` endpoint that returns basic Prometheus-style text output.

This is a minimal observability baseline — it does NOT require Prometheus
or any external metrics backend. P3+ can replace this with a real
Prometheus exporter or OpenTelemetry.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestMetrics:
    """In-memory request metrics collector.

    Tracks:
    - Total request count by method and path.
    - Total request count by status code.
    - Request latency (count, sum, min, max).
    """

    def __init__(self) -> None:
        self._request_count: dict[str, int] = defaultdict(int)
        self._status_count: dict[int, int] = defaultdict(int)
        self._latency_count: int = 0
        self._latency_sum: float = 0.0
        self._latency_min: float = float("inf")
        self._latency_max: float = 0.0

    def record(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Record a completed request."""
        key = f"{method}:{path}"
        self._request_count[key] += 1
        self._status_count[status_code] += 1
        self._latency_count += 1
        self._latency_sum += duration_ms
        self._latency_min = min(self._latency_min, duration_ms)
        self._latency_max = max(self._latency_max, duration_ms)

    def to_prometheus_text(self) -> str:
        """Render metrics as Prometheus-style text."""
        lines: list[str] = []

        # Request count
        lines.append("# TYPE http_requests_total counter")
        for key, count in sorted(self._request_count.items()):
            method, path = key.split(":", 1)
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}"}} {count}'
            )

        # Status code distribution
        lines.append("# TYPE http_status_total counter")
        for status, count in sorted(self._status_count.items()):
            lines.append(f'http_status_total{{status="{status}"}} {count}')

        # Latency summary
        lines.append("# TYPE http_request_duration_ms summary")
        avg = self._latency_sum / self._latency_count if self._latency_count else 0.0
        lines.append(
            f'http_request_duration_ms{{quantile="avg"}} {avg:.2f}'
        )
        if self._latency_count > 0:
            lines.append(
                f'http_request_duration_ms{{quantile="min"}} {self._latency_min:.2f}'
            )
            lines.append(
                f'http_request_duration_ms{{quantile="max"}} {self._latency_max:.2f}'
            )

        return "\n".join(lines)

    @property
    def total_requests(self) -> int:
        """Total number of recorded requests."""
        return self._latency_count


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records request metrics."""

    def __init__(self, app, metrics: RequestMetrics) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            self._metrics.record(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            self._metrics.record(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise


def register_metrics_endpoint(app: FastAPI, metrics: RequestMetrics) -> None:
    """Register a /metrics endpoint on the given FastAPI app."""
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        """Prometheus-style metrics endpoint."""
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(
            content=metrics.to_prometheus_text(),
            media_type="text/plain; version=0.0.4",
        )
