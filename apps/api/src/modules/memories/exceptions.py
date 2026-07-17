"""Memory module exceptions."""
from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class MemoryNotFoundError(AppError):
    def __init__(self, message: str = "记忆不存在", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="MEMORY_NOT_FOUND", message=message, status_code=404, details=details)


class MemoryPermissionDeniedError(AppError):
    def __init__(self, message: str = "无权操作此记忆", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="MEMORY_PERMISSION_DENIED", message=message, status_code=403, details=details)


class ConsentNotFoundError(AppError):
    def __init__(self, message: str = "授权记录不存在", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="CONSENT_NOT_FOUND", message=message, status_code=404, details=details)


class ConsentDeniedError(AppError):
    def __init__(self, message: str = "授权不足，拒绝访问记忆", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="CONSENT_DENIED", message=message, status_code=403, details=details)


class EncryptionError(AppError):
    def __init__(self, message: str = "加密或解密失败", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="ENCRYPTION_ERROR", message=message, status_code=500, details=details)
