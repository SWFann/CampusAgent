"""
Pydantic schemas for the conversations module.

Design principles:
- Input schemas use frozen-contract field names.
- Output schemas do NOT include email, student_no, password_hash, token, or session info.
- Message output does NOT include payload_json (internal).
- Deleted messages return content=None.
- Private preference fields are never accepted in input.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Conversation schemas
# ---------------------------------------------------------------------------


class PrivateConversationCreateRequest(BaseModel):
    """POST /api/v1/conversations/private request body."""

    target_user_id: UUID


class GroupConversationCreateRequest(BaseModel):
    """POST /api/v1/conversations request body for group creation."""

    title: str | None = Field(default=None, max_length=200)
    participant_user_ids: list[UUID] = Field(default_factory=list)
    organization_id: UUID | None = None


class ConversationRead(BaseModel):
    """Safe conversation output."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str | None = None
    organization_id: UUID | None = None
    created_by: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class ConversationListItem(BaseModel):
    """Conversation list item — minimal safe projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str | None = None
    organization_id: UUID | None = None
    status: str
    last_message_at: datetime | None = None
    participant_count: int = 0


class ConversationListResponse(BaseModel):
    """Response for GET /api/v1/conversations."""

    conversations: list[ConversationListItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Participant schemas
# ---------------------------------------------------------------------------


class ParticipantAddRequest(BaseModel):
    """POST /api/v1/conversations/{id}/participants request body."""

    user_id: UUID
    role: str = Field(default="MEMBER", max_length=40)


class ParticipantRead(BaseModel):
    """Safe participant output — no email, student_no, password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    participant_type: str
    participant_user_id: UUID | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    role: str
    status: str
    joined_at: datetime
    left_at: datetime | None = None


class ParticipantListResponse(BaseModel):
    """Response for GET /api/v1/conversations/{id}/participants."""

    participants: list[ParticipantRead]
    total: int


# ---------------------------------------------------------------------------
# Message schemas
# ---------------------------------------------------------------------------


class MessageCreateRequest(BaseModel):
    """POST /api/v1/conversations/{id}/messages request body."""

    content: str = Field(..., min_length=1, max_length=5000)
    message_type: str = Field(default="TEXT", max_length=40)
    idempotency_key: str | None = Field(default=None, max_length=200)


class MessageRead(BaseModel):
    """Safe message output.

    Deleted messages return content=None.
    payload_json is never exposed to clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    sender_type: str
    sender_user_id: UUID | None = None
    sender_agent_id: UUID | None = None
    message_type: str
    content: str | None = None
    status: str
    sequence: int = 0
    created_at: datetime
    deleted_at: datetime | None = None


class MessageListResponse(BaseModel):
    """Response for GET /api/v1/conversations/{id}/messages."""

    messages: list[MessageRead]
    total: int
    page: int
    page_size: int
