"""
Conversation, ConversationParticipant, and Message ORM models for CampusAgent.

This module defines the P5 conversation tables:
- ``Conversation``: a chat container (PRIVATE / GROUP / ORG_GROUP / SCENE).
- ``ConversationParticipant``: user/agent membership in a conversation.
- ``Message``: a single message in a conversation.

Design principles:
- UUID primary keys (UUID v4 via ``new_uuid``).
- All timestamps are timezone-aware UTC via ``utc_now()``.
- Enums are stored as strings for cross-database compatibility.
- ``__repr__`` does NOT leak message content or payload.
- Soft-delete for conversations and messages (deleted_at).
- Idempotency key on messages for deduplication.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid

# ---------------------------------------------------------------------------
# Enums (stored as strings in the database)
# ---------------------------------------------------------------------------


class ConversationType(StrEnum):
    """Types of conversations."""

    PRIVATE = "PRIVATE"
    GROUP = "GROUP"
    ORG_GROUP = "ORG_GROUP"
    SCENE = "SCENE"


class ConversationStatus(StrEnum):
    """Lifecycle status of a conversation."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class ParticipantType(StrEnum):
    """Types of conversation participants."""

    USER = "USER"
    AGENT = "AGENT"


class ConversationRole(StrEnum):
    """Roles within a conversation."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    GUEST = "GUEST"


class ParticipantStatus(StrEnum):
    """Lifecycle status of a participant."""

    ACTIVE = "ACTIVE"
    LEFT = "LEFT"
    REMOVED = "REMOVED"


class MessageType(StrEnum):
    """Types of messages."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    FILE = "FILE"
    SYSTEM = "SYSTEM"
    AGENT_PUBLIC = "AGENT_PUBLIC"
    SCENE_CARD = "SCENE_CARD"
    VOTE = "VOTE"
    PROPOSAL = "PROPOSAL"
    RESULT = "RESULT"
    PRIVACY_NOTICE = "PRIVACY_NOTICE"


class MessageStatus(StrEnum):
    """Lifecycle status of a message."""

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class SenderType(StrEnum):
    """Sender type for messages — aligned with WebSocket contract §4.3.1."""

    USER = "USER"
    AGENT = "AGENT"
    SYSTEM = "SYSTEM"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class Conversation(Base):
    """Conversation entity — a chat container.

    Types:
    - PRIVATE: two-person direct message.
    - GROUP: multi-person group chat.
    - ORG_GROUP: organization default group chat.
    - SCENE: scene-bound conversation (placeholder for P8+).
    """

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=ConversationStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    participants: Mapped[list[ConversationParticipant]] = relationship(
        "ConversationParticipant",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id} type={self.type} "
            f"status={self.status}>"
        )


class ConversationParticipant(Base):
    """Participant in a conversation.

    P5 only supports USER participants. AGENT is a schema-level
    placeholder for future phases (P6+).
    """

    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "participant_type",
            "participant_user_id",
            "participant_agent_id",
            name="uq_conversation_participants_unique",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    participant_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ParticipantType.USER.value,
    )
    participant_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    participant_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid, nullable=True  # FK to agents table added in P6
    )
    role: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=ConversationRole.MEMBER.value,
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=ParticipantStatus.ACTIVE.value,
    )
    joined_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="participants"
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationParticipant id={self.id} "
            f"conversation_id={self.conversation_id} "
            f"type={self.participant_type} "
            f"user_id={self.participant_user_id} "
            f"role={self.role} status={self.status}>"
        )


class Message(Base):
    """A single message in a conversation.

    Privacy:
    - ``__repr__`` does NOT output content or payload_json.
    - Deleted messages return empty content in API responses.
    - content/payload must not contain private preference fields.
    """

    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SenderType.USER.value,
    )
    sender_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    sender_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid, nullable=True  # FK to agents table added in P6
    )
    message_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=MessageType.TEXT.value,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=MessageStatus.ACTIVE.value,
    )
    sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        """repr must not leak content or payload."""
        return (
            f"<Message id={self.id} "
            f"conversation_id={self.conversation_id} "
            f"sender_type={self.sender_type} "
            f"message_type={self.message_type} "
            f"status={self.status}>"
        )
