"""
Request context middleware for CampusAgent API.

This middleware:
- Extracts or generates a request ID (X-Correlation-ID compatible).
- If the client provides a valid UUID, it is reused.
- If no valid UUID is provided, a new UUID v4 is generated.
- Stores the request ID in ``request.state.request_id``.
- Echoes the request ID back in the ``X-Correlation-ID`` response header.
- Records request duration in ``request.state.request_duration_ms``.
- Logs request start/end with structured fields.
- Actor summary is ``anonymous`` until auth is implemented (P3).
- Does NOT log Authorization headers, cookies, request body, prompts,
  or any private data.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("campus_agent.request")

# Headers that must NEVER be logged — they may contain secrets or PII.
_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
    }
)


def _is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def extract_request_id(request: Request) -> str:
    """Extract a request ID from the incoming request.

    Resolution order:
    1. ``X-Correlation-ID`` header if it contains a valid UUID.
    2. ``X-Request-ID`` header if it contains a valid UUID.
    3. A freshly generated UUID v4.

    If a non-UUID value is provided in either header, a new UUID v4
    is generated and the original value is ignored (not logged).
    """
    # Try X-Correlation-ID first (backward compatibility).
    correlation_id = request.headers.get("X-Correlation-ID")
    if correlation_id and _is_valid_uuid(correlation_id):
        return str(correlation_id)

    # Try X-Request-ID as a fallback.
    request_id = request.headers.get("X-Request-ID")
    if request_id and _is_valid_uuid(request_id):
        return str(request_id)

    # Generate a new UUID v4.
    return str(uuid.uuid4())


def get_safe_headers(request: Any) -> dict[str, str]:
    """Return a dict of non-sensitive request headers for logging.

    Sensitive headers (authorization, cookie, etc.) are excluded.
    Only safe headers like User-Agent, Content-Type, X-Correlation-ID
    are included.
    """
    safe: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() not in _SENSITIVE_HEADERS:
            safe[key] = value
    return safe


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that adds request ID, duration, and structured logging."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Extract or generate request ID.
        request_id = extract_request_id(request)
        request.state.request_id = request_id
        request.state.correlation_id = request_id  # backward compat

        # Record start time.
        start_time = time.perf_counter()

        # Log request start (no sensitive data).
        logger.info(
            "request.start",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "actor": "anonymous",  # No auth yet (P3)
            },
        )

        # Process the request.
        try:
            response = await call_next(request)
        except Exception:
            # Log the exception without sensitive details.
            duration_ms = (time.perf_counter() - start_time) * 1000
            request.state.request_duration_ms = duration_ms
            logger.error(
                "request.error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "actor": "anonymous",
                },
            )
            raise

        # Calculate duration.
        duration_ms = (time.perf_counter() - start_time) * 1000
        request.state.request_duration_ms = duration_ms

        # Set response header.
        response.headers["X-Correlation-ID"] = request_id

        # Log request end (no sensitive data).
        logger.info(
            "request.end",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "actor": "anonymous",
            },
        )

        return response
