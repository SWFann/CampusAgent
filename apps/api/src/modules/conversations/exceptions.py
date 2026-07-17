"""
Module-owned exceptions for the conversations module.

Error codes are aligned with the API contract:
- CONVERSATION_NOT_FOUND (404)
- CONVERSATION_PERMISSION_DENIED (403)
- CONVERSATION_ALREADY_EXISTS (409)
- CONVERSATION_PARTICIPANT_LIMIT (400)
- MESSAGE_NOT_FOUND (404)
- MESSAGE_IDEMPOTENCY_CONFLICT (409)
- MESSAGE_SENSITIVE_CONTENT (422)
"""

from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class ConversationNotFoundError(AppError):
    """Raised when a conversation is not found or has been deleted."""

    def __init__(
        self, message: str = "会话不存在", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="CONVERSATION_NOT_FOUND",
            message=message,
            status_code=404,
            details=details,
        )


class ConversationPermissionDeniedError(AppError):
    """Raised when the actor lacks permission for a conversation action."""

    def __init__(
        self,
        message: str = "无权执行此会话操作",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CONVERSATION_PERMISSION_DENIED",
            message=message,
            status_code=403,
            details=details,
        )


class ConversationAlreadyExistsError(AppError):
    """Raised when a private conversation already exists between two users."""

    def __init__(
        self,
        message: str = "私聊会话已存在",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CONVERSATION_ALREADY_EXISTS",
            message=message,
            status_code=409,
            details=details,
        )


class ConversationParticipantLimitError(AppError):
    """Raised when a conversation has reached its participant limit."""

    def __init__(
        self,
        message: str = "会话参与者数量已达上限",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="CONVERSATION_PARTICIPANT_LIMIT",
            message=message,
            status_code=400,
            details=details,
        )


class MessageNotFoundError(AppError):
    """Raised when a message is not found or has been deleted."""

    def __init__(
        self, message: str = "消息不存在", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="MESSAGE_NOT_FOUND",
            message=message,
            status_code=404,
            details=details,
        )


class MessageIdempotencyConflictError(AppError):
    """Raised when a message with the same idempotency_key already exists."""

    def __init__(
        self,
        message: str = "消息幂等键冲突",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="MESSAGE_IDEMPOTENCY_CONFLICT",
            message=message,
            status_code=409,
            details=details,
        )


class MessageSensitiveContentError(AppError):
    """Raised when message content or payload contains sensitive fields."""

    def __init__(
        self,
        message: str = "消息内容包含敏感字段，已被拒绝",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="MESSAGE_SENSITIVE_CONTENT",
            message=message,
            status_code=422,
            details=details,
        )
