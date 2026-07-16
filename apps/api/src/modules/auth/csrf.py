"""
CSRF double-submit cookie validation for CampusAgent.

This module provides:
- ``generate_csrf_token()``: generate a cryptographically secure CSRF token.
- ``validate_csrf(request: Request) -> None``: validate the CSRF token.
- ``require_csrf(request: Request) -> None``: FastAPI dependency for CSRF enforcement.

Error codes:
- ``CSRF_TOKEN_MISSING`` (403): missing X-CSRF-Token header or csrf_token cookie.
- ``CSRF_TOKEN_MISMATCH`` (403): header and cookie values do not match.
"""

from __future__ import annotations

import secrets

from fastapi import Request

from .exceptions import CsrfTokenMismatchError, CsrfTokenMissingError

# Cookie and header names
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """Generate a cryptographically secure random CSRF token.

    Returns:
        A URL-safe random string.
    """
    return secrets.token_urlsafe(32)


def validate_csrf(request: Request) -> None:
    """Validate the CSRF double-submit cookie.

    Compares the ``X-CSRF-Token`` header value with the ``csrf_token``
    cookie value. Raises on failure.

    Args:
        request: The incoming FastAPI request.

    Raises:
        CsrfTokenMissingError: If header or cookie is missing.
        CsrfTokenMismatchError: If values do not match.
    """
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)

    if not csrf_cookie or not csrf_header:
        raise CsrfTokenMissingError()

    if csrf_cookie != csrf_header:
        raise CsrfTokenMismatchError()


def require_csrf(request: Request) -> None:
    """FastAPI dependency that enforces CSRF validation.

    Usage in route definitions:
        @router.post("/some-write-endpoint")
        def my_endpoint(_=Depends(require_csrf)):
            ...

    Raises:
        CsrfTokenMissingError / CsrfTokenMismatchError on failure.
    """
    validate_csrf(request)
