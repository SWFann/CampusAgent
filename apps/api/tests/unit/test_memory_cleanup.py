"""P6-14: TTL cleanup task tests.

Tests:
- Expired memory is soft-deleted.
- Repeated cleanup is a no-op (reentrant).
- Revoked consent cleanup works.
- run_cleanup is reentrant.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.memories.cleanup import (
    cleanup_expired_memories,
    cleanup_revoked_consents,
    run_cleanup,
)
from src.modules.memories.encryption import get_encryption_service, reset_encryption_service
from src.modules.memories.models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentStatus,
    MemoryCategory,
    MemoryItem,
)
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def _reset_encryption():
    reset_encryption_service()
    yield
    reset_encryption_service()


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="cleanup@example.com",
        password_hash="fake",
        display_name="Cleanup User",
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
        name="Cleanup Agent",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    test_db_session.add(agent)
    test_db_session.flush()
    return agent


class TestCleanupExpiredMemories:
    """Test cleanup_expired_memories."""

    def test_expired_memory_soft_deleted(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Expired memory is soft-deleted by cleanup."""
        enc = get_encryption_service()
        past = utc_now() - timedelta(hours=1)

        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("expired content"),
            content_hash=enc.hash_content("expired content"),
            expires_at=past,
        )
        test_db_session.add(memory)
        test_db_session.flush()

        result = cleanup_expired_memories(test_db_session)
        assert result["expired_memories_deleted"] == 1

        # Verify it's soft-deleted
        test_db_session.refresh(memory)
        assert memory.deleted_at is not None

    def test_non_expired_not_deleted(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Non-expired memory is not affected by cleanup."""
        enc = get_encryption_service()
        future = utc_now() + timedelta(hours=24)

        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("active content"),
            content_hash=enc.hash_content("active content"),
            expires_at=future,
        )
        test_db_session.add(memory)
        test_db_session.flush()

        result = cleanup_expired_memories(test_db_session)
        assert result["expired_memories_deleted"] == 0

        test_db_session.refresh(memory)
        assert memory.deleted_at is None

    def test_no_expiry_not_deleted(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Memory without expiry is not affected by cleanup."""
        enc = get_encryption_service()
        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("no expiry"),
            content_hash=enc.hash_content("no expiry"),
        )
        test_db_session.add(memory)
        test_db_session.flush()

        result = cleanup_expired_memories(test_db_session)
        assert result["expired_memories_deleted"] == 0

    def test_repeated_cleanup_noop(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Repeated cleanup is a no-op for already-processed items."""
        enc = get_encryption_service()
        past = utc_now() - timedelta(hours=1)

        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("expired"),
            content_hash=enc.hash_content("expired"),
            expires_at=past,
        )
        test_db_session.add(memory)
        test_db_session.flush()

        # First cleanup
        r1 = cleanup_expired_memories(test_db_session)
        assert r1["expired_memories_deleted"] == 1

        # Second cleanup — should find nothing new
        r2 = cleanup_expired_memories(test_db_session)
        assert r2["expired_memories_deleted"] == 0

    def test_already_deleted_not_reprocessed(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Already soft-deleted expired memories are not reprocessed."""
        enc = get_encryption_service()
        past = utc_now() - timedelta(hours=1)

        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("already deleted"),
            content_hash=enc.hash_content("already deleted"),
            expires_at=past,
            deleted_at=utc_now(),
        )
        test_db_session.add(memory)
        test_db_session.flush()

        result = cleanup_expired_memories(test_db_session)
        assert result["expired_memories_deleted"] == 0


class TestCleanupRevokedConsents:
    """Test cleanup_revoked_consents."""

    def test_revoked_consent_found(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """Revoked consent is found by cleanup."""
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.REVOKED.value,
            revoked_at=utc_now(),
        )
        test_db_session.add(consent)
        test_db_session.flush()

        result = cleanup_revoked_consents(test_db_session)
        assert result["revoked_consents_found"] == 1

    def test_active_consent_not_counted(
        self, test_db_session: Session, test_user: User, test_agent
    ) -> None:
        """Active consent is not counted by cleanup."""
        consent = ConsentRecord(
            grantor_user_id=test_user.id,
            grantee_agent_id=test_agent.id,
            purpose=ConsentPurpose.CHAT_REPLY.value,
            status=ConsentStatus.GRANTED.value,
        )
        test_db_session.add(consent)
        test_db_session.flush()

        result = cleanup_revoked_consents(test_db_session)
        assert result["revoked_consents_found"] == 0


class TestRunCleanup:
    """Test run_cleanup (full cycle)."""

    def test_run_cleanup_reentrant(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """run_cleanup is reentrant — running twice is safe."""
        enc = get_encryption_service()
        past = utc_now() - timedelta(hours=1)

        memory = MemoryItem(
            owner_user_id=test_user.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("expired"),
            content_hash=enc.hash_content("expired"),
            expires_at=past,
        )
        test_db_session.add(memory)
        test_db_session.flush()

        r1 = run_cleanup(test_db_session)
        assert r1["expired_memories_deleted"] == 1

        r2 = run_cleanup(test_db_session)
        assert r2["expired_memories_deleted"] == 0

    def test_run_cleanup_returns_both_counts(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """run_cleanup returns both expired_memories and revoked_consents counts."""
        result = run_cleanup(test_db_session)
        assert "expired_memories_deleted" in result
        assert "revoked_consents_found" in result
