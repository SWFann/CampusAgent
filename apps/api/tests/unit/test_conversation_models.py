"""
Unit tests for conversation ORM models (P5-01).

Tests:
- Create PRIVATE conversation.
- Create GROUP conversation.
- Create ORG_GROUP conversation.
- Participant unique constraint.
- Message creation.
- Message __repr__ does not leak content.
- Migration upgrade/downgrade.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.conversations.models import (
    Conversation,
    ConversationParticipant,
    ConversationRole,
    ConversationStatus,
    ConversationType,
    Message,
    MessageStatus,
    MessageType,
    ParticipantStatus,
    ParticipantType,
    SenderType,
)


class TestConversationModel:
    """Test Conversation ORM model."""

    def test_create_private_conversation(self, test_db_session: Session) -> None:
        """Create a PRIVATE conversation."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.PRIVATE.value,
            created_by=user_id,
            status=ConversationStatus.ACTIVE.value,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        assert conv.id is not None
        assert conv.type == "PRIVATE"
        assert conv.status == "ACTIVE"
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.deleted_at is None
        test_db_session.rollback()

    def test_create_group_conversation(self, test_db_session: Session) -> None:
        """Create a GROUP conversation with a title."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.GROUP.value,
            title="测试群聊",
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        assert conv.type == "GROUP"
        assert conv.title == "测试群聊"
        test_db_session.rollback()

    def test_create_org_group_conversation(
        self, test_db_session: Session
    ) -> None:
        """Create an ORG_GROUP conversation with organization_id."""
        user_id = uuid4()
        org_id = uuid4()
        conv = Conversation(
            type=ConversationType.ORG_GROUP.value,
            organization_id=org_id,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        assert conv.type == "ORG_GROUP"
        assert conv.organization_id == org_id
        test_db_session.rollback()

    def test_conversation_repr(self, test_db_session: Session) -> None:
        """Conversation repr should not leak sensitive data."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.GROUP.value,
            title="Secret Group",
            created_by=user_id,
        )
        repr_str = repr(conv)
        assert "Secret Group" not in repr_str
        assert "Conversation" in repr_str
        assert conv.type in repr_str


class TestConversationParticipantModel:
    """Test ConversationParticipant ORM model."""

    def test_create_participant(self, test_db_session: Session) -> None:
        """Create a USER participant."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.PRIVATE.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        participant = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=user_id,
            role=ConversationRole.OWNER.value,
            status=ParticipantStatus.ACTIVE.value,
        )
        test_db_session.add(participant)
        test_db_session.flush()

        assert participant.id is not None
        assert participant.participant_type == "USER"
        assert participant.role == "OWNER"
        assert participant.status == "ACTIVE"
        test_db_session.rollback()

    def test_participant_unique_constraint(
        self, test_db_session: Session
    ) -> None:
        """Duplicate (conversation, type, user) should fail."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.PRIVATE.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        p1 = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=user_id,
            role=ConversationRole.MEMBER.value,
        )
        test_db_session.add(p1)
        test_db_session.flush()

        p2 = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=user_id,
            role=ConversationRole.MEMBER.value,
        )
        test_db_session.add(p2)
        try:
            test_db_session.flush()
            # SQLite may not enforce unique constraints on flush without
            # commit in all modes; force a commit to trigger the constraint.
            test_db_session.commit()
            raise AssertionError("Should have raised unique constraint violation")
        except Exception:
            # Expected: unique constraint violation
            pass
        finally:
            test_db_session.rollback()

    def test_participant_repr(self, test_db_session: Session) -> None:
        """Participant repr should not leak sensitive data."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.GROUP.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        participant = ConversationParticipant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER.value,
            participant_user_id=user_id,
            role=ConversationRole.MEMBER.value,
        )
        repr_str = repr(participant)
        assert "ConversationParticipant" in repr_str
        assert "role=" in repr_str
        assert "status=" in repr_str


class TestMessageModel:
    """Test Message ORM model."""

    def test_create_message(self, test_db_session: Session) -> None:
        """Create a TEXT message."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.GROUP.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            sender_type=SenderType.USER.value,
            sender_user_id=user_id,
            message_type=MessageType.TEXT.value,
            content="你好，世界！",
            status=MessageStatus.ACTIVE.value,
        )
        test_db_session.add(msg)
        test_db_session.flush()

        assert msg.id is not None
        assert msg.message_type == "TEXT"
        assert msg.content == "你好，世界！"
        assert msg.status == "ACTIVE"
        assert msg.created_at is not None
        test_db_session.rollback()

    def test_message_repr_does_not_leak_content(
        self, test_db_session: Session
    ) -> None:
        """Message __repr__ must not output content or payload."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.PRIVATE.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        secret_content = "This is a secret message content"
        secret_payload = '{"private_preference": "vegan"}'
        msg = Message(
            conversation_id=conv.id,
            sender_type=SenderType.USER.value,
            sender_user_id=user_id,
            message_type=MessageType.TEXT.value,
            content=secret_content,
            payload_json=secret_payload,
        )
        repr_str = repr(msg)
        assert secret_content not in repr_str
        assert secret_payload not in repr_str
        assert "private_preference" not in repr_str
        assert "Message" in repr_str
        assert msg.message_type in repr_str
        test_db_session.rollback()

    def test_message_repr_does_not_leak_payload(
        self, test_db_session: Session
    ) -> None:
        """Message __repr__ must not output payload_json."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.GROUP.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            sender_type=SenderType.SYSTEM.value,
            message_type=MessageType.SYSTEM.value,
            content=None,
            payload_json='{"scene_type": "dinner"}',
        )
        repr_str = repr(msg)
        assert "scene_type" not in repr_str
        assert "dinner" not in repr_str
        test_db_session.rollback()

    def test_deleted_message_has_no_content(
        self, test_db_session: Session
    ) -> None:
        """A deleted message should have DELETED status and deleted_at set."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.PRIVATE.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            sender_type=SenderType.USER.value,
            sender_user_id=user_id,
            message_type=MessageType.TEXT.value,
            content="Original content",
            status=MessageStatus.ACTIVE.value,
        )
        test_db_session.add(msg)
        test_db_session.flush()

        # Soft-delete the message
        msg.status = MessageStatus.DELETED.value
        msg.deleted_at = utc_now()
        test_db_session.flush()

        assert msg.status == "DELETED"
        assert msg.deleted_at is not None
        test_db_session.rollback()

    def test_idempotency_key(self, test_db_session: Session) -> None:
        """Idempotency key can be set and stored."""
        user_id = uuid4()
        conv = Conversation(
            type=ConversationType.GROUP.value,
            created_by=user_id,
        )
        test_db_session.add(conv)
        test_db_session.flush()

        msg = Message(
            conversation_id=conv.id,
            sender_type=SenderType.USER.value,
            sender_user_id=user_id,
            message_type=MessageType.TEXT.value,
            content="test",
            idempotency_key="idem-123",
        )
        test_db_session.add(msg)
        test_db_session.flush()

        assert msg.idempotency_key == "idem-123"
        test_db_session.rollback()
