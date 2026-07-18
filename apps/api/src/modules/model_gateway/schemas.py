"""Model Gateway schemas — request/response models for unified model access.

Privacy contract (frozen):
- These schemas NEVER carry prompt/response content into logs, metrics, or
  AgentRun records. Only hashes and metadata are persisted.
- PrivacyContext is mandatory on every request (fail-closed if missing).
- P4 data forces requires_local=True and allow_external=False.
- P3 data forces allow_external=False.

Aligned with docs/api/API_CONTRACT.md EP-MODEL-058/059/060.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Data classification (P0–P4 per docs/privacy data inventory)
# ---------------------------------------------------------------------------


class DataClassification(StrEnum):
    """Data sensitivity tiers. P0=public, P4=most sensitive."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


# Classifications that must NEVER be routed to an external provider.
_SENSITIVE_EXTERNAL_BLOCKED = frozenset(
    {DataClassification.P3, DataClassification.P4}
)


# ---------------------------------------------------------------------------
# PrivacyContext
# ---------------------------------------------------------------------------


class PrivacyContext(BaseModel):
    """Mandatory privacy context attached to every model request.

    Fields (per P7 guide §5):
    - data_classification: P0/P1/P2/P3/P4
    - allow_external: whether routing to an external provider is permitted
    - requires_local: whether only local/mock/rule providers may be used
    - contains_personal_data: whether the payload carries personal data
    - purpose: the declared use purpose (e.g. meal_planning, agent_chat)
    """

    data_classification: DataClassification
    allow_external: bool = False
    requires_local: bool = False
    contains_personal_data: bool = False
    purpose: str = Field(..., min_length=1, max_length=50)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _enforce_sensitive_defaults(self) -> PrivacyContext:
        """P4 forces local-only; P3/P4 forbid external routing."""
        if self.data_classification == DataClassification.P4:
            self.requires_local = True
            self.allow_external = False
        if self.data_classification in _SENSITIVE_EXTERNAL_BLOCKED:
            self.allow_external = False
        return self

    @property
    def is_external_blocked(self) -> bool:
        """True when external routing must be rejected."""
        return (
            self.data_classification in _SENSITIVE_EXTERNAL_BLOCKED
            or not self.allow_external
            or self.requires_local
        )


# ---------------------------------------------------------------------------
# Chat request / response
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., min_length=1, max_length=20)
    content: str = Field(..., min_length=0)

    model_config = {"extra": "forbid"}


class ChatRequest(BaseModel):
    """Unified chat request.

    Fields (per P7 guide §5):
    - messages: conversation turns
    - privacy_context: mandatory privacy envelope
    - timeout_ms: per-call timeout ceiling
    - response_schema: optional JSON schema for structured-output validation
    - purpose: declared purpose (must match privacy_context.purpose)
    - request_id: correlation id
    """

    messages: list[ChatMessage] = Field(..., min_length=1)
    privacy_context: PrivacyContext
    timeout_ms: int = Field(default=30000, ge=100, le=300000)
    response_schema: dict[str, Any] | None = None
    purpose: str = Field(..., min_length=1, max_length=50)
    request_id: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    # De-identified preference capsule for P4 scenarios. Raw P4 data must
    # never be placed in messages.content; it travels only via this capsule.
    preference_capsule: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class ResponseContent(BaseModel):
    """Model response content."""

    type: str = "TEXT"  # TEXT or STRUCTURED
    content: Any = None

    model_config = {"extra": "forbid"}


class CallMetadata(BaseModel):
    """Call metadata — never includes prompt/response content."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int
    provider: str
    model: str | None = None

    model_config = {"extra": "forbid"}


class ChatResponse(BaseModel):
    """Unified chat response."""

    request_id: str | None = None
    model: str | None = None
    status: str  # completed / failed / timeout
    response: ResponseContent
    metadata: CallMetadata
    input_hash: str | None = None
    output_hash: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Embedding request / response
# ---------------------------------------------------------------------------


class EmbeddingRequest(BaseModel):
    """Unified embedding request."""

    text: str = Field(..., min_length=1)
    privacy_context: PrivacyContext
    model: str | None = None
    dimension: int | None = Field(default=None, ge=1, le=4096)
    timeout_ms: int = Field(default=30000, ge=100, le=300000)
    request_id: str | None = None

    model_config = {"extra": "forbid"}


class EmbeddingResponse(BaseModel):
    """Unified embedding response."""

    request_id: str | None = None
    model: str | None = None
    status: str
    embedding: list[float]
    dimension: int
    metadata: CallMetadata
    text_hash: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Provider health
# ---------------------------------------------------------------------------


class ProviderHealthStatus(StrEnum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class ProviderHealth(BaseModel):
    """Health snapshot for a provider."""

    provider_name: str
    healthy: bool
    status: ProviderHealthStatus
    latency_ms: int | None = None
    last_checked: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Routing decision (for observability without sensitive labels)
# ---------------------------------------------------------------------------


class RoutingDecision(BaseModel):
    """Non-sensitive summary of a routing decision.

    Never includes prompt, response, user email, or raw endpoint with token.
    """

    provider_type: str
    provider_name: str
    reason: str
    privacy_blocked_external: bool = False

    model_config = {"extra": "forbid"}
