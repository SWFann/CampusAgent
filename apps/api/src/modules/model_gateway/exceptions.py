"""Module-owned exceptions for the model_gateway module.

All exceptions carry a stable error code aligned with the frozen API contract
(docs/api/API_CONTRACT.md §1.6). Privacy failures use dedicated PRIVACY_*
codes; routing/model failures use MODEL_* codes. None of these exceptions
ever transport prompt, response, or credential content.
"""
from __future__ import annotations

from typing import Any

from ...utils.errors import AppError


class ModelGatewayError(AppError):
    """Base error for all model gateway failures."""


# --- Privacy-context failures (fail-closed) ---


class PrivacyContextMissingError(ModelGatewayError):
    """privacy_context is missing — request must be rejected before any call."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="PRIVACY_CONTEXT_MISSING",
            message="缺少隐私上下文（privacy_context），请求被拒绝",
            status_code=403,
            details=details,
        )


class PrivacyContextInvalidError(ModelGatewayError):
    """privacy_context fields are invalid or data classification is wrong."""

    def __init__(self, message: str = "隐私上下文字段无效或数据分类不符",
                 details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="PRIVACY_CONTEXT_INVALID",
            message=message,
            status_code=403,
            details=details,
        )


class PrivacyContextSensitiveExternalBlockedError(ModelGatewayError):
    """Sensitive data (P3/P4) must not be routed to an external provider."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED",
            message="敏感数据（P3/P4）禁止路由到外部模型",
            status_code=403,
            details=details,
        )


# --- Routing / availability failures ---


class ModelUnavailableError(ModelGatewayError):
    """Model service is unavailable (all candidates unhealthy)."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="MODEL_UNAVAILABLE",
            message="模型服务不可用",
            status_code=503,
            details=details,
        )


class ModelTimeoutError(ModelGatewayError):
    """Model call exceeded the configured timeout."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="MODEL_TIMEOUT",
            message="模型调用超时",
            status_code=504,
            details=details,
        )


class ModelRoutingFailedError(ModelGatewayError):
    """Routing could not select any valid provider."""

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="MODEL_ROUTING_FAILED",
            message="模型路由失败",
            status_code=502,
            details=details,
        )


class ExternalProviderError(ModelGatewayError):
    """External provider returned an error after being explicitly allowed."""

    def __init__(self, message: str = "外部模型供应商返回错误",
                 details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="EXTERNAL_PROVIDER_ERROR",
            message=message,
            status_code=502,
            details=details,
        )


# --- Structured output validation failure ---


class StructuredOutputValidationError(ModelGatewayError):
    """Structured output failed schema validation after limited retries.

    Privacy: the invalid raw output is never included in details or logs.
    """

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="MODEL_ROUTING_FAILED",
            message="模型输出结构化校验失败",
            status_code=502,
            details=details,
        )
