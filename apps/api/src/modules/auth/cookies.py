"""
Cookie helpers for CampusAgent auth.

This module provides:
- ``generate_csrf_token()``: generate a random CSRF token.
- ``set_auth_cookies(response, access_token, refresh_token, csrf_token, settings)``:
  set all three auth cookies on a response.
- ``clear_auth_cookies(response, settings)``: clear all auth cookies.

Cookie attributes are aligned with the API contract:
- access_token: HttpOnly, SameSite=Lax, Path=/api/v1, Max-Age=3600
- refresh_token: HttpOnly, SameSite=Lax, Path=/api/v1/auth, Max-Age=604800
- csrf_token: non-HttpOnly, SameSite=Lax, Path=/, Max-Age=604800

Secure is True in production, False in development/test.
"""

from __future__ import annotations

import secrets

from fastapi import Response

from ...config import AppEnv, Settings

# Cookie attribute constants
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"

ACCESS_TOKEN_MAX_AGE = 3600  # 1 hour
REFRESH_TOKEN_MAX_AGE = 604800  # 7 days
CSRF_MAX_AGE = 604800  # 7 days

ACCESS_TOKEN_PATH = "/api/v1"
REFRESH_TOKEN_PATH = "/api/v1/auth"
CSRF_PATH = "/"


def _is_secure(settings: Settings) -> bool:
    """Return True if cookies should have the Secure flag."""
    return settings.APP_ENV == AppEnv.PRODUCTION


def generate_csrf_token() -> str:
    """Generate a cryptographically secure random CSRF token.

    Returns:
        A URL-safe random string (43 chars).
    """
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    """Set access_token, refresh_token, and csrf_token cookies on a response.

    Args:
        response: The FastAPI/Starlette Response to attach cookies to.
        access_token: The JWT access token string.
        refresh_token: The JWT refresh token string.
        csrf_token: The CSRF token string.
        settings: Application settings (for Secure flag).
    """
    secure = _is_secure(settings)

    # access_token: HttpOnly, SameSite=Lax, Path=/api/v1, Max-Age=3600
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=ACCESS_TOKEN_PATH,
        max_age=ACCESS_TOKEN_MAX_AGE,
    )

    # refresh_token: HttpOnly, SameSite=Lax, Path=/api/v1/auth, Max-Age=604800
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=REFRESH_TOKEN_PATH,
        max_age=REFRESH_TOKEN_MAX_AGE,
    )

    # csrf_token: non-HttpOnly, SameSite=Lax, Path=/, Max-Age=604800
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite="lax",
        path=CSRF_PATH,
        max_age=CSRF_MAX_AGE,
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Clear all auth cookies by setting Max-Age=0.

    Args:
        response: The FastAPI/Starlette Response to attach cookies to.
        settings: Application settings (for Secure flag).
    """
    secure = _is_secure(settings)

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value="",
        httponly=True,
        secure=secure,
        samesite="lax",
        path=ACCESS_TOKEN_PATH,
        max_age=0,
    )

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value="",
        httponly=True,
        secure=secure,
        samesite="lax",
        path=REFRESH_TOKEN_PATH,
        max_age=0,
    )

    response.set_cookie(
        key=CSRF_COOKIE,
        value="",
        httponly=False,
        secure=secure,
        samesite="lax",
        path=CSRF_PATH,
        max_age=0,
    )
