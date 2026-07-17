"""
Repository for Conversation, ConversationParticipant, and Message entities.

Provides query helpers for common lookups. The repository only does
queries and basic persistence — no permission decisions.

Permission and business logic are handled in the service layer.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...db.repositories import BaseRepository
from .models import (
    Conversation,
    ConversationParticipant,
    ConversationStatus,
    Message,
    MessageStatus,
    ParticipantStatus,
    ParticipantType,
)


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for the ``Conversation`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Conversation)

    def get_by_id(self, id_: UUID) -> Conversation | None:
        """Get a conversation by primary key (including soft-deleted)."""
        return self._session.get(Conversation, id_)

    def get_active_by_id(self, id_: UUID) -> Conversation | None:
        """Get a conversation by ID, excluding soft-deleted."""
        conv = self._session.get(Conversation, id_)
        if conv is None or conv.status == ConversationStatus.DELETED.value:
            return None
        return conv

    def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        """List active conversations where the user is an active participant."""
        stmt = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(
                ConversationParticipant.participant_user_id == user_id,
                ConversationParticipant.participant_type
                == ParticipantType.USER.value,
                ConversationParticipant.status == ParticipantStatus.ACTIVE.value,
                Conversation.status != ConversationStatus.DELETED.value,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    def find_private_conversation(
        self, user_a_id: UUID, user_b_id: UUID
    ) -> Conversation | None:
        """Find an existing private conversation between two users.

        A private conversation has exactly two participants. If both
        users are participants in the same PRIVATE conversation, return it.
        """
        from .models import ConversationType

        stmt = (
            select(Conversation)
            .where(
                Conversation.type == ConversationType.PRIVATE.value,
                Conversation.status != ConversationStatus.DELETED.value,
            )
        )
        conversations = list(self._session.execute(stmt).scalars().all())
        for conv in conversations:
            participants = self._get_participants(conv.id)
            active_user_ids = {
                p.participant_user_id
                for p in participants
                if p.status == ParticipantStatus.ACTIVE.value
                and p.participant_type == ParticipantType.USER.value
            }
            if {user_a_id, user_b_id} == active_user_ids:
                return conv
        return None

    def _get_participants(
        self, conversation_id: UUID
    ) -> list[ConversationParticipant]:
        """Get all participants for a conversation."""
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id
        )
        return list(self._session.execute(stmt).scalars().all())

    def find_org_group(
        self, organization_id: UUID
    ) -> Conversation | None:
        """Find the ORG_GROUP conversation for an organization."""
        from .models import ConversationType

        stmt = select(Conversation).where(
            Conversation.organization_id == organization_id,
            Conversation.type == ConversationType.ORG_GROUP.value,
            Conversation.status != ConversationStatus.DELETED.value,
        )
        return self._session.execute(stmt).scalars().first()

    def count_active_participants(self, conversation_id: UUID) -> int:
        """Count active participants in a conversation."""
        stmt = (
            select(func.count())
            .select_from(ConversationParticipant)
            .where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.status == ParticipantStatus.ACTIVE.value,
            )
        )
        result = self._session.execute(stmt).scalar()
        return int(result or 0)


class ConversationParticipantRepository(
    BaseRepository[ConversationParticipant]
):
    """Repository for the ``ConversationParticipant`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ConversationParticipant)

    def get_by_id(self, id_: UUID) -> ConversationParticipant | None:
        """Get a participant by primary key."""
        return self._session.get(ConversationParticipant, id_)

    def get_active_by_conversation_user(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant | None:
        """Get an ACTIVE participant for a (conversation, user) pair."""
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.participant_user_id == user_id,
            ConversationParticipant.participant_type
            == ParticipantType.USER.value,
            ConversationParticipant.status == ParticipantStatus.ACTIVE.value,
        )
        return self._session.execute(stmt).scalars().first()

    def get_any_by_conversation_user(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationParticipant | None:
        """Get any participant row for a (conversation, user) pair."""
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.participant_user_id == user_id,
            ConversationParticipant.participant_type
            == ParticipantType.USER.value,
        )
        return self._session.execute(stmt).scalars().first()

    def list_active_by_conversation(
        self, conversation_id: UUID
    ) -> list[ConversationParticipant]:
        """List all ACTIVE participants for a conversation."""
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.status == ParticipantStatus.ACTIVE.value,
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_active_by_user(
        self, user_id: UUID
    ) -> list[ConversationParticipant]:
        """List all ACTIVE participations for a user."""
        stmt = select(ConversationParticipant).where(
            ConversationParticipant.participant_user_id == user_id,
            ConversationParticipant.participant_type
            == ParticipantType.USER.value,
            ConversationParticipant.status == ParticipantStatus.ACTIVE.value,
        )
        return list(self._session.execute(stmt).scalars().all())


class MessageRepository(BaseRepository[Message]):
    """Repository for the ``Message`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Message)

    def get_by_id(self, id_: UUID) -> Message | None:
        """Get a message by primary key (including soft-deleted)."""
        return self._session.get(Message, id_)

    def get_active_by_id(self, id_: UUID) -> Message | None:
        """Get a message by ID, excluding soft-deleted."""
        msg = self._session.get(Message, id_)
        if msg is None or msg.status == MessageStatus.DELETED.value:
            return None
        return msg

    def list_by_conversation(
        self,
        conversation_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Message], int]:
        """List messages in a conversation with pagination.

        Returns (messages, total_count). Messages are ordered by
        created_at DESC (newest first).
        """
        offset = (page - 1) * page_size
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        messages = list(self._session.execute(stmt).scalars().all())

        count_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        total = int(self._session.execute(count_stmt).scalar() or 0)

        return messages, total

    def get_by_idempotency_key(
        self, conversation_id: UUID, idempotency_key: str
    ) -> Message | None:
        """Get a message by idempotency key within a conversation."""
        stmt = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.idempotency_key == idempotency_key,
        )
        return self._session.execute(stmt).scalars().first()

    def get_next_sequence(self, conversation_id: UUID) -> int:
        """Get the next sequence number for a conversation."""
        stmt = (
            select(func.max(Message.sequence))
            .where(Message.conversation_id == conversation_id)
        )
        result = self._session.execute(stmt).scalar()
        return int(result or 0) + 1

    def get_last_message_at(
        self, conversation_id: UUID
    ) -> UUID | None:
        """Not used — placeholder for future optimization."""
        return None
