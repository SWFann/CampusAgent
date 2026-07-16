"""
Unified API response envelope for CampusAgent.

This module defines the standard success and error envelope shapes
used across all API responses. It also provides a stable error code
mapping for common HTTP error types.

Design principles:
- Success envelope: ``{"success": true, "data": ..., "request_id": "..."}``
- Error envelope: ``{"success": false, "error": {code, message, details}, "request_id": "..."}``
- Health endpoints (/health/live, /health/ready) are exempt — they
  return their own simple format for liveness probes.
- Unknown exceptions are caught and mapped to a generic
  ``INTERNAL_ERROR`` without leaking internal details.
- ``request_id`` is populated from the request context (correlation_id).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

# Mapping from common exception types to stable error codes.
# These codes are part of the API contract and must not change
# without a major version bump.
ERROR_CODE_VALIDATION = "VALIDATION_ERROR"
ERROR_CODE_AUTHENTICATION = "AUTH_FAILED"
ERROR_CODE_AUTHORIZATION = "PERMISSION_DENIED"
ERROR_CODE_NOT_FOUND = "NOT_FOUND"
ERROR_CODE_INTERNAL = "INTERNAL_ERROR"
ERROR_CODE_RATE_LIMITED = "RATE_LIMITED"
ERROR_CODE_CONFLICT = "CONFLICT"
ERROR_CODE_UNPROCESSABLE = "UNPROCESSABLE_ENTITY"

# HTTP status code to error code mapping for standard errors.
_HTTP_STATUS_TO_CODE: dict[int, str] = {
    400: ERROR_CODE_VALIDATION,
    401: ERROR_CODE_AUTHENTICATION,
    403: ERROR_CODE_AUTHORIZATION,
    404: ERROR_CODE_NOT_FOUND,
    409: ERROR_CODE_CONFLICT,
    422: ERROR_CODE_UNPROCESSABLE,
    429: ERROR_CODE_RATE_LIMITED,
    500: ERROR_CODE_INTERNAL,
}


def error_code_for_status(status_code: int) -> str:
    """Map an HTTP status code to a stable error code.

    Unknown status codes map to ``INTERNAL_ERROR``.
    """
    return _HTTP_STATUS_TO_CODE.get(status_code, ERROR_CODE_INTERNAL)


# ---------------------------------------------------------------------------
# Envelope models
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Error detail object in the error envelope."""

    code: str = Field(description="Stable error code, e.g. VALIDATION_ERROR")
    message: str = Field(description="Safe user-facing error message")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context (no sensitive data)",
    )


class SuccessEnvelope(BaseModel):
    """Standard success response envelope."""

    success: bool = True
    data: Any = None
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""

    success: bool = False
    error: ErrorDetail
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def success(
    data: Any = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a success envelope dict.

    Args:
        data: The response payload.
        request_id: The request correlation ID, if available.

    Returns:
        A dict matching the success envelope shape.
    """
    return {"success": True, "data": data, "request_id": request_id}


def error(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build an error envelope dict.

    Args:
        code: Stable error code.
        message: Safe user-facing error message.
        details: Optional additional context (no sensitive data).
        request_id: The request correlation ID, if available.

    Returns:
        A dict matching the error envelope shape.
    """
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "request_id": request_id,
    }


def internal_error(request_id: str | None = None) -> dict[str, Any]:
    """Build a generic internal error envelope.

    This should be used for unhandled exceptions to avoid leaking
    internal details.
    """
    return error(
        code=ERROR_CODE_INTERNAL,
        message="An internal server error occurred.",
        request_id=request_id,
    )
