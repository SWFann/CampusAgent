"""Module-owned exceptions for the nodes module.

All exceptions carry stable error codes aligned with the frozen API contract.
"""
from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class NodesError(AppError):
    """Base error for node-module failures."""


class AdminPermissionDeniedError(NodesError):
    """Actor lacks the required admin role."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="ADMIN_PERMISSION_DENIED",
            message="管理员权限不足",
            status_code=403,
            details=details,
        )


class NodeNotFoundError(NodesError):
    """Node does not exist or has been deleted."""

    def __init__(self) -> None:
        super().__init__(
            code="NODE_NOT_FOUND",
            message="边缘节点不存在",
            status_code=404,
        )


class ModelNotFoundError(NodesError):
    """Model definition does not exist."""

    def __init__(self) -> None:
        super().__init__(
            code="MODEL_NOT_FOUND",
            message="模型配置不存在",
            status_code=404,
        )


class NodeInUseError(NodesError):
    """Node is processing requests and cannot be deleted."""

    def __init__(self) -> None:
        super().__init__(
            code="NODE_IN_USE",
            message="节点正在处理请求，无法删除",
            status_code=409,
        )


class NodeOfflineError(NodesError):
    """Node is offline."""

    def __init__(self) -> None:
        super().__init__(
            code="NODE_OFFLINE",
            message="节点离线",
            status_code=503,
        )
