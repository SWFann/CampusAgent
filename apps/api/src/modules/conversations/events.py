"""
Domain events for the conversations module.

These events use the P2 ``DomainEvent`` base class and the shared
``default_event_bus``. They are published AFTER a successful commit.

Privacy requirements:
- Events do NOT contain message content, payload, email, student_no, password_hash, token, or session info.
- Events only store IDs, types, and status — no private content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...events.bus import DomainEvent


@dataclass(frozen=True)
class ConversationCreated(DomainEvent):
    """Published when a new conversation is created."""

    event_id: str
    conversation_id: UUID
    actor_id: UUID
    conversation_type: str
    occurred_at: datetime


@dataclass(frozen=True)
class ParticipantJoined(DomainEvent):
    """Published when a user joins or is added to a conversation."""

    event_id: str
    conversation_id: UUID
    user_id: UUID
    actor_id: UUID
    role: str
    status: str
    occurred_at: datetime


@dataclass(frozen=True)
class ParticipantLeft(DomainEvent):
    """Published when a user leaves or is removed from a conversation."""

    event_id: str
    conversation_id: UUID
    user_id: UUID
    actor_id: UUID
    action: str  # "left" or "removed"
    occurred_at: datetime


@dataclass(frozen=True)
class MessageCreated(DomainEvent):
    """Published when a new message is created.

    NOTE: This event does NOT carry content or payload — those are
    fetched via HTTP API. The event only carries IDs and metadata
    for the realtime pubsub layer.
    """

    event_id: str
    conversation_id: UUID
    message_id: UUID
    sender_type: str
    sender_user_id: UUID | None
    sender_agent_id: UUID | None
    message_type: str
    sequence: int
    occurred_at: datetime


@dataclass(frozen=True)
class MessageDeleted(DomainEvent):
    """Published when a message is soft-deleted."""

    event_id: str
    conversation_id: UUID
    message_id: UUID
    actor_id: UUID
    occurred_at: datetime
