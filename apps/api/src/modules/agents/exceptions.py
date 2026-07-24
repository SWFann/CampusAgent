"""Agent module exceptions."""

from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class AgentNotFoundError(AppError):
    def __init__(
        self, message: str = "智能体不存在", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(code="AGENT_NOT_FOUND", message=message, status_code=404, details=details)


class AgentPermissionDeniedError(AppError):
    def __init__(
        self, message: str = "无权操作此智能体", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AGENT_PERMISSION_DENIED", message=message, status_code=403, details=details
        )


class AgentAlreadyExistsError(AppError):
    def __init__(
        self, message: str = "个人智能体已存在", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="AGENT_ALREADY_EXISTS", message=message, status_code=409, details=details
        )


class InvalidDelegationLevelError(AppError):
    def __init__(
        self, message: str = "无效的委托级别", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="INVALID_DELEGATION_LEVEL", message=message, status_code=400, details=details
        )


class WorkspaceThreadNotFoundError(AppError):
    def __init__(
        self, message: str = "个人任务不存在", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            code="WORKSPACE_THREAD_NOT_FOUND", message=message, status_code=404, details=details
        )


class AgentModelRouteError(AppError):
    def __init__(
        self, message: str = "模型路由设置无效", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(code="AGENT_MODEL_ROUTE_INVALID", message=message, status_code=400, details=details)
