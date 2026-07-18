"""Pydantic schemas for Node and Deployment admin API.

Privacy:
- Node responses never include endpoint/credential plaintext.
- List responses redact endpoint entirely; detail responses include only
  the host (not userinfo/query/token).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Node schemas
# ---------------------------------------------------------------------------


class NodeCreate(BaseModel):
    """Request body for POST /api/v1/admin/nodes."""

    name: str = Field(..., min_length=1, max_length=100)
    endpoint: str = Field(..., min_length=1, max_length=500)
    credential: str | None = None
    namespace: str | None = Field(default=None, max_length=100)
    exposure_type: str = Field(..., pattern="^(INGRESS|NODEPORT|LOCAL|MOCK)$")
    capabilities: list[str] | None = None
    models_supported: list[str] | None = None
    max_concurrent_requests: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class NodeUpdate(BaseModel):
    """Request body for PATCH /api/v1/admin/nodes/{node_id}."""

    status: str | None = Field(default=None, pattern="^(registering|healthy|degraded|maintenance|offline|deleted)$")
    max_concurrent_requests: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class NodeRead(BaseModel):
    """Node response — never includes credential, redacts endpoint in list."""

    node_id: UUID
    name: str
    endpoint: str | None = None  # only in detail view, host only
    status: str
    health_status: str
    exposure_type: str
    namespace: str | None = None
    capabilities: list[str] | None = None
    models_supported: list[str] | None = None
    max_concurrent_requests: int | None = None
    current_requests: int | None = None
    uptime_seconds: int | None = None
    last_heartbeat: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class NodeListRead(BaseModel):
    """Node list item — endpoint fully redacted."""

    node_id: UUID
    name: str
    status: str
    health_status: str
    capabilities: list[str] | None = None
    last_heartbeat: datetime | None = None
    created_at: datetime

    model_config = {"extra": "forbid"}


class HealthCheckResult(BaseModel):
    """Result of a manual health check."""

    node_id: UUID
    status: str
    checks: dict[str, str]
    latency_ms: int
    checked_at: str

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Model definition schemas
# ---------------------------------------------------------------------------


class ModelDefinitionCreate(BaseModel):
    """Request body for POST /api/v1/admin/models."""

    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(default="1.0.0", max_length=50)
    provider: str = Field(..., pattern="^(local|external|mock|rule)$")
    model_type: str = Field(..., pattern="^(chat|embedding)$")
    capabilities: list[str] | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    default_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    enabled: bool = True
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class ModelDefinitionRead(BaseModel):
    """Model definition response."""

    model_id: UUID
    name: str
    version: str
    provider: str
    model_type: str
    enabled: bool
    capabilities: list[str] | None = None
    max_tokens: int | None = None
    default_temperature: float | None = None
    created_at: datetime
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Deployment schemas
# ---------------------------------------------------------------------------


class DeploymentCreate(BaseModel):
    """Request body for POST /api/v1/admin/deployments."""

    model_id: UUID
    node_id: UUID
    version: str = Field(default="1.0.0", max_length=50)
    status: str = Field(default="deployed", pattern="^(deployed|pending|failed|retired)$")
    priority: int = Field(default=100, ge=1, le=999)
    capabilities: list[str] | None = None
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}


class DeploymentRead(BaseModel):
    """Deployment response."""

    deployment_id: UUID
    model_id: UUID
    node_id: UUID
    version: str
    status: str
    priority: int
    capabilities: list[str] | None = None
    deployed_at: datetime
    created_at: datetime

    model_config = {"extra": "forbid"}
