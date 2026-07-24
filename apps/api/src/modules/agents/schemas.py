"""Agent API schemas (Pydantic models)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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


class WorkspaceChatMessage(BaseModel):
    """A user-visible turn sent from the personal workspace."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _trim_content(self) -> WorkspaceChatMessage:
        self.content = self.content.strip()
        if not self.content:
            raise ValueError("message content must not be blank")
        return self


class WorkspaceChatRequest(BaseModel):
    """One new user turn in an owner-only workspace thread."""

    thread_id: UUID | None = None
    message: str | None = Field(default=None, max_length=4000)
    # Temporary backward compatibility for clients from before task persistence.
    messages: list[WorkspaceChatMessage] | None = Field(default=None, min_length=1, max_length=20)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_conversation(self) -> WorkspaceChatRequest:
        if self.message is not None:
            self.message = self.message.strip()
        if not self.message and not self.messages:
            raise ValueError("message is required")
        if self.messages:
            if self.messages[-1].role != "user":
                raise ValueError("the last message must be from the user")
            if sum(len(message.content) for message in self.messages) > 24000:
                raise ValueError("conversation is too long")
        return self


class WorkspaceChatResponse(BaseModel):
    thread_id: str
    thread_title: str
    reply: str
    provider: str
    model: str | None = None
    request_id: str | None = None


class WorkspaceThreadCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)

    model_config = {"extra": "forbid"}


class WorkspaceMessageRead(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class WorkspaceThreadRead(BaseModel):
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    message_count: int = 0


class WorkspaceThreadDetail(WorkspaceThreadRead):
    messages: list[WorkspaceMessageRead]


class AgentModelRouteUpdate(BaseModel):
    mode: Literal["PLATFORM", "PERSONAL"]
    profile_id: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    name: str | None = Field(default=None, max_length=60)
    provider: Literal["OPENAI", "DEEPSEEK", "STEPFUN", "CUSTOM"] | None = None
    base_url: str | None = Field(default=None, max_length=500)
    model: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:/-]+$")
    api_key: str | None = Field(default=None, min_length=8, max_length=512)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_personal_route(self) -> AgentModelRouteUpdate:
        if self.name is not None:
            self.name = self.name.strip()
        if self.base_url is not None:
            self.base_url = self.base_url.strip()
        if self.model is not None:
            self.model = self.model.strip()
        if self.api_key is not None:
            self.api_key = self.api_key.strip()
        if self.mode == "PERSONAL":
            if not self.model:
                raise ValueError("model is required for a personal route")
            if not self.provider:
                raise ValueError("provider is required for a personal route")
        return self


class AgentModelRouteProfileRead(BaseModel):
    id: str
    name: str
    provider: Literal["OPENAI", "DEEPSEEK", "STEPFUN", "CUSTOM"]
    model: str
    base_url: str
    has_api_key: bool


class AgentModelRouteRead(BaseModel):
    mode: Literal["PLATFORM", "PERSONAL"]
    active_profile_id: str | None = None
    profiles: list[AgentModelRouteProfileRead]
    provider: str
    model: str
    base_url: str
    has_api_key: bool


class AgentModelRouteTestResponse(BaseModel):
    healthy: bool
    status: str
    latency_ms: int | None = None
    model: str
