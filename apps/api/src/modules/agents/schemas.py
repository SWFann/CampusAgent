"""Agent API schemas (Pydantic models)."""
from __future__ import annotations

from pydantic import BaseModel


class AgentRead(BaseModel):
    id: str
    owner_user_id: str
    type: str
    name: str
    avatar_url: str | None = None
    public_persona: str | None = None
    delegation_level: str
    status: str
    has_private_config: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class AgentListResponse(BaseModel):
    agents: list[AgentRead]
    total: int


class AgentUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    public_persona: str | None = None
    delegation_level: str | None = None
    private_config_encrypted: str | None = None
