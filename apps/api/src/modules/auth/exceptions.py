"""
Module-owned exceptions for the auth module.

These exceptions extend ``AppError`` so they are automatically translated
to the unified error envelope by the global exception handler in
``main.py``.

Error codes are aligned with the API contract:
- AUTH_WEAK_PASSWORD (400)
- AUTH_INVALID_CREDENTIALS (401)
- AUTH_INVALID_TOKEN (401)
- AUTH_REFRESH_TOKEN_REVOKED (401)
- AUTH_REFRESH_TOKEN_EXPIRED (401)
- USER_ALREADY_EXISTS (409)
- CSRF_TOKEN_MISSING (403)
- CSRF_TOKEN_MISMATCH (403)
"""

from __future__ import annotations

from typing import Any

from ...utils.errors import AppError

# ---------------------------------------------------------------------------
# Password / registration errors
# ---------------------------------------------------------------------------


class WeakPasswordError(AppError):
    """Raised when a password does not meet strength requirements."""

    def __init__(self, message: str = "密码强度不足", details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="AUTH_WEAK_PASSWORD",
            message=message,
            status_code=400,
            details=details,
        )


class UserAlreadyExistsError(AppError):
    """Raised when email or student_no is already registered."""

    def __init__(
        self, message: str = "邮箱或学号已被注册", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="USER_ALREADY_EXISTS",
            message=message,
            status_code=409,
            details=details,
        )


# ---------------------------------------------------------------------------
# Credential / token errors
# ---------------------------------------------------------------------------


class InvalidCredentialsError(AppError):
    """Raised when login credentials are invalid.

    This error MUST NOT distinguish between 'user not found' and
    'wrong password' to prevent account enumeration.
    """

    def __init__(
        self, message: str = "邮箱或密码错误", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AUTH_INVALID_CREDENTIALS",
            message=message,
            status_code=401,
            details=details,
        )


class InvalidTokenError(AppError):
    """Raised when an access token is missing, invalid, or expired."""

    def __init__(
        self, message: str = "访问令牌无效或已过期", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AUTH_INVALID_TOKEN",
            message=message,
            status_code=401,
            details=details,
        )


class RefreshTokenRevokedError(AppError):
    """Raised when a refresh token has been revoked (including replay detection)."""

    def __init__(
        self, message: str = "Refresh Token 已被撤销", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AUTH_REFRESH_TOKEN_REVOKED",
            message=message,
            status_code=401,
            details=details,
        )


class RefreshTokenExpiredError(AppError):
    """Raised when a refresh token has expired."""

    def __init__(
        self, message: str = "Refresh Token 已过期", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AUTH_REFRESH_TOKEN_EXPIRED",
            message=message,
            status_code=401,
            details=details,
        )


# ---------------------------------------------------------------------------
# CSRF errors
# ---------------------------------------------------------------------------


class CsrfTokenMissingError(AppError):
    """Raised when a required CSRF token header is missing."""

    def __init__(
        self, message: str = "缺少 CSRF Token", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="CSRF_TOKEN_MISSING",
            message=message,
            status_code=403,
            details=details,
        )


class CsrfTokenMismatchError(AppError):
    """Raised when the CSRF header value does not match the cookie value."""

    def __init__(
        self, message: str = "CSRF Token 不匹配", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="CSRF_TOKEN_MISMATCH",
            message=message,
            status_code=403,
            details=details,
        )


# ---------------------------------------------------------------------------
# Account status errors
# ---------------------------------------------------------------------------


class AccountDisabledError(AppError):
    """Raised when a user account is disabled or deleted."""

    def __init__(
        self, message: str = "邮箱或密码错误", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AUTH_INVALID_CREDENTIALS",
            message=message,
            status_code=401,
            details=details,
        )
