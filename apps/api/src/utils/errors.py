"""
Custom error types
"""

from __future__ import annotations


class AppError(Exception):
    """Base application error"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppError):
    """Authentication failed"""

    def __init__(self, message: str = "Authentication failed", details: dict | None = None):
        super().__init__(
            code="AUTH_FAILED",
            message=message,
            status_code=401,
            details=details,
        )


class AuthorizationError(AppError):
    """Authorization failed"""

    def __init__(self, message: str = "Permission denied", details: dict | None = None):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=403,
            details=details,
        )


class NotFoundError(AppError):
    """Resource not found"""

    def __init__(self, resource: str, details: dict | None = None):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found",
            status_code=404,
            details=details,
        )
