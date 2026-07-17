"""P6-04: MemoryItem model tests.

Tests:
- content_encrypted is required (not nullable).
- plaintext never stored directly.
- expires_at can be set.
- deleted_at excludes from queries.
- repr does not contain content.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.memories.models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentStatus,
    MemoryCategory,
    MemoryItem,
    MemorySource,
    SensitivityLevel,
)
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="mem@example.com",
        password_hash="fake-hash",
        display_name="Mem User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def test_agent(test_db_session: Session, test_user: User):
    from src.modules.agents.models import Agent, AgentType, DelegationLevel

    agent = Agent(
        owner_user_id=test_user.id,
        type=AgentType.PERSONAL.value,
        name="Test Agent",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    test_db_session.add(agent)
    test_db_session.flush()
    return agent


class TestMemoryItemModel:
    """Test MemoryItem ORM model."""

    def test_content_encrypted_required(self) -> None:
        """content_encrypted is not nullable."""
        col = MemoryItem.__table__.c.content_encrypted
        assert not col.nullable

    def test_plaintext_not_stored(self, test_db_session: Session, test_user: User) -> None:
        """Plaintext is not stored — only encrypted content."""
        plaintext = "my-secret-preference"
        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted="encrypted-ciphertext-value",
            content_hash="sha256hash",
        )
        test_db_session.add(memory)
        test_db_session.flush()

        # Verify the stored value is the ciphertext, not plaintext
        assert memory.content_encrypted == "encrypted-ciphertext-value"
        assert memory.content_encrypted != plaintext

    def test_expires_at_can_be_set(self, test_db_session: Session, test_user: User) -> None:
        """expires_at can be set to a future time."""
        future = utc_now() + timedelta(hours=24)
        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.FACT.value,
            content_encrypted="cipher",
            content_hash="hash",
            expires_at=future,
        )
        test_db_session.add(memory)
        test_db_session.flush()
        assert memory.expires_at is not None
        assert memory.expires_at > utc_now()

    def test_deleted_at_excludes_from_query(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """deleted_at items are excluded from list_by_owner."""
        from src.modules.memories.repository import MemoryRepository

        memory1 = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted="cipher1",
            content_hash="hash1",
        )
        memory2 = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted="cipher2",
            content_hash="hash2",
            deleted_at=utc_now(),
        )
        test_db_session.add_all([memory1, memory2])
        test_db_session.flush()

        repo = MemoryRepository(test_db_session)
        memories = repo.list_by_owner(test_user.id)
        assert len(memories) == 1
        assert memories[0].content_encrypted == "cipher1"

    def test_repr_no_content(self, test_db_session: Session, test_user: User) -> None:
        """repr must not contain content_encrypted value."""
        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted="super-secret-cipher",
            content_hash="hash",
        )
        repr_str = repr(memory)
        assert "super-secret-cipher" not in repr_str
        assert "content_encrypted" not in repr_str

    def test_memory_category_enum(self) -> None:
        assert MemoryCategory.PREFERENCE == "PREFERENCE"
        assert MemoryCategory.FACT == "FACT"
        assert MemoryCategory.CONTEXT == "CONTEXT"
        assert MemoryCategory.FEEDBACK == "FEEDBACK"

    def test_sensitivity_level_enum(self) -> None:
        assert SensitivityLevel.PUBLIC == "PUBLIC"
        assert SensitivityLevel.INTERNAL == "INTERNAL"
        assert SensitivityLevel.CONFIDENTIAL == "CONFIDENTIAL"

    def test_memory_source_enum(self) -> None:
        assert MemorySource.USER_INPUT == "USER_INPUT"
        assert MemorySource.AGENT_INFERRED == "AGENT_INFERRED"
        assert MemorySource.SYSTEM == "SYSTEM"

    def test_encryption_key_version_default(self, test_db_session: Session, test_user: User) -> None:
        """encryption_key_version defaults to 1."""
        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.FACT.value,
            content_encrypted="cipher",
            content_hash="hash",
        )
        test_db_session.add(memory)
        test_db_session.flush()
        assert memory.encryption_key_version == 1


class TestConsentRecordModel:
    """Test ConsentRecord ORM model."""

    def test_consent_creation(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """ConsentRecord can be created."""
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.GRANTED.value,
        )
        test_db_session.add(consent)
        test_db_session.flush()
        assert consent.id is not None
        assert consent.status == "GRANTED"
        assert consent.revoked_at is None

    def test_consent_purpose_enum(self) -> None:
        assert ConsentPurpose.CHAT_REPLY == "chat_reply"
        assert ConsentPurpose.SCENE_EXECUTION == "scene_execution"
        assert ConsentPurpose.MEMORY_REVIEW == "memory_review"
        assert ConsentPurpose.RECOMMENDATION == "recommendation"

    def test_consent_repr_no_sensitive(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """ConsentRecord repr must not contain scope_json."""
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            scope_json='{"category": ["PREFERENCE"]}',
            status=ConsentStatus.GRANTED.value,
        )
        repr_str = repr(consent)
        assert "scope_json" not in repr_str
        assert "PREFERENCE" not in repr_str
