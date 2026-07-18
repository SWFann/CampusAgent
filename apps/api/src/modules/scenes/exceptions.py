"""Module-owned exceptions for the scenes module.

All exceptions carry stable error codes aligned with the frozen API contract.
Privacy: exceptions never transport private payload, capsule, or individual
scores.
"""
from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class SceneError(AppError):
    """Base error for all scene failures."""


class SceneNotFoundError(SceneError):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_NOT_FOUND",
            message="场景不存在",
            status_code=404,
            details=details,
        )


class SceneStateTransitionError(SceneError):
    """Illegal state transition attempted."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_INVALID_TRANSITION",
            message="场景状态转换不合法",
            status_code=409,
            details=details,
        )


class ScenePermissionDeniedError(SceneError):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_PERMISSION_DENIED",
            message="无权操作此场景",
            status_code=403,
            details=details,
        )


class SceneConsentRequiredError(SceneError):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_CONSENT_REQUIRED",
            message="需要场景级授权才能提交私有输入",
            status_code=403,
            details=details,
        )


class SceneSubmissionError(SceneError):
    def __init__(self, message: str = "私有提交失败",
                 details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_SUBMISSION_FAILED",
            message=message,
            status_code=400,
            details=details,
        )


class ScenePluginError(SceneError):
    def __init__(self, message: str = "场景插件执行失败",
                 details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_PLUGIN_ERROR",
            message=message,
            status_code=502,
            details=details,
        )


class SceneAlreadyExistsError(SceneError):
    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_ALREADY_EXISTS",
            message="场景已存在",
            status_code=409,
            details=details,
        )


class SceneConcurrencyError(SceneError):
    """Optimistic lock failure — another request modified the scene."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="SCENE_CONCURRENCY_CONFLICT",
            message="场景状态已被其他请求修改",
            status_code=409,
            details=details,
        )
