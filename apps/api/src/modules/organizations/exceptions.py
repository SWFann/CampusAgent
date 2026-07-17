"""
Module-owned exceptions for the organizations module.

These exceptions extend ``AppError`` so they are automatically translated
to the unified error envelope by the global exception handler.

Error codes are aligned with the API contract:
- ORG_NOT_FOUND (404)
- ORG_PERMISSION_DENIED (403)
- ORG_MEMBER_ALREADY_EXISTS (409)
- ORG_LAST_OWNER_CANNOT_LEAVE (409)
- ORG_INVALID_JOIN_POLICY (400)
- ORG_CAPACITY_EXCEEDED (409)
"""

from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class OrganizationNotFoundError(AppError):
    """Raised when an organization is not found or has been deleted."""

    def __init__(
        self, message: str = "组织不存在", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="ORG_NOT_FOUND",
            message=message,
            status_code=404,
            details=details,
        )


class OrganizationPermissionDeniedError(AppError):
    """Raised when the actor lacks permission for an organization action."""

    def __init__(
        self, message: str = "无权执行此组织操作", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="ORG_PERMISSION_DENIED",
            message=message,
            status_code=403,
            details=details,
        )


class OrganizationMemberAlreadyExistsError(AppError):
    """Raised when a user is already an active/pending/invited member."""

    def __init__(
        self, message: str = "用户已是组织成员", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="ORG_MEMBER_ALREADY_EXISTS",
            message=message,
            status_code=409,
            details=details,
        )


class OrganizationLastOwnerError(AppError):
    """Raised when trying to remove, demote, or let leave the last OWNER."""

    def __init__(
        self,
        message: str = "最后一个所有者不能退出、被移除或降级",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ORG_LAST_OWNER_CANNOT_LEAVE",
            message=message,
            status_code=409,
            details=details,
        )


class OrganizationInvalidJoinPolicyError(AppError):
    """Raised when the join policy does not allow self-service joining."""

    def __init__(
        self,
        message: str = "当前加入策略不允许自助加入",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ORG_INVALID_JOIN_POLICY",
            message=message,
            status_code=400,
            details=details,
        )


class OrganizationCapacityExceededError(AppError):
    """Raised when the organization has reached its member capacity."""

    def __init__(
        self,
        message: str = "组织成员数已达上限",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code="ORG_CAPACITY_EXCEEDED",
            message=message,
            status_code=409,
            details=details,
        )
