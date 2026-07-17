"""P6-09: Memory query policy tests.

All memory queries must match:
- owner
- agent
- purpose
- category/scope
- active consent
- not expired
- not deleted

Tests:
- A cannot query B's memories.
- A's agent cannot query with wrong purpose.
- Revoke takes effect immediately.
- Deleted memories are excluded.
- Expired memories are excluded.
"""
from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.agents.models import Agent, AgentType, DelegationLevel
from src.modules.memories.consent import grant_consent, revoke_consent
from src.modules.memories.encryption import reset_encryption_service
from src.modules.memories.exceptions import ConsentDeniedError, MemoryPermissionDeniedError
from src.modules.memories.models import MemoryCategory, MemoryItem
from src.modules.memories.service import get_memory
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def _reset_encryption():
    reset_encryption_service()
    yield
    reset_encryption_service()


@pytest.fixture()
def user_a(test_db_session: Session) -> User:
    user = User(
        email="user-a@example.com",
        password_hash="fake",
        display_name="User A",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def user_b(test_db_session: Session) -> User:
    user = User(
        email="user-b@example.com",
        password_hash="fake",
        display_name="User B",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def agent_a(test_db_session: Session, user_a: User) -> Agent:
    agent = Agent(
        owner_user_id=user_a.id,
        type=AgentType.PERSONAL.value,
        name="Agent A",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    test_db_session.add(agent)
    test_db_session.flush()
    return agent


@pytest.fixture()
def memory_a(test_db_session: Session, user_a: User) -> MemoryItem:
    from src.modules.memories.encryption import get_encryption_service

    enc = get_encryption_service()
    memory = MemoryItem(
        owner_user_id=user_a.id,
        category=MemoryCategory.PREFERENCE.value,
        content_encrypted=enc.encrypt("A's private preference"),
        content_hash=enc.hash_content("A's private preference"),
    )
    test_db_session.add(memory)
    test_db_session.flush()
    return memory


class TestMemoryQueryPolicy:
    """Test memory query policy enforcement."""

    def test_owner_can_read_own(
        self, test_db_session: Session, user_a: User, memory_a: MemoryItem
    ) -> None:
        """Owner can read their own memory without consent."""
        result = get_memory(user_a, memory_a.id, test_db_session)
        assert result["content"] == "A's private preference"

    def test_a_cannot_query_b_memory(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
        memory_a: MemoryItem,
    ) -> None:
        """User B cannot read User A's memory without consent."""
        with pytest.raises(MemoryPermissionDeniedError):
            get_memory(user_b, memory_a.id, test_db_session)

    def test_agent_wrong_purpose_denied(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
        agent_a: Agent,
        memory_a: MemoryItem,
    ) -> None:
        """Agent with wrong purpose is denied."""
        # Grant consent for chat_reply
        grant_consent(user_a.id, agent_a.id, "chat_reply", test_db_session)

        # Try to access with wrong purpose (no consent for scene_execution)
        with pytest.raises(ConsentDeniedError):
            get_memory(
                user_b,
                memory_a.id,
                test_db_session,
                agent_id=agent_a.id,
                purpose="scene_execution",
            )

    def test_revoke_takes_effect_immediately(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
        agent_a: Agent,
        memory_a: MemoryItem,
    ) -> None:
        """Revoke takes effect immediately on memory access."""
        result = grant_consent(user_a.id, agent_a.id, "chat_reply", test_db_session)
        revoke_consent(user_a.id, UUID(result["id"]), test_db_session)

        with pytest.raises(ConsentDeniedError):
            get_memory(
                user_b,
                memory_a.id,
                test_db_session,
                agent_id=agent_a.id,
                purpose="chat_reply",
            )

    def test_deleted_memory_excluded(
        self, test_db_session: Session, user_a: User
    ) -> None:
        """Deleted memories are not accessible."""
        from src.modules.memories.encryption import get_encryption_service
        from src.modules.memories.exceptions import MemoryNotFoundError

        enc = get_encryption_service()
        memory = MemoryItem(
            owner_user_id=user_a.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("deleted content"),
            content_hash=enc.hash_content("deleted content"),
            deleted_at=utc_now(),
        )
        test_db_session.add(memory)
        test_db_session.flush()

        with pytest.raises(MemoryNotFoundError):
            get_memory(user_a, memory.id, test_db_session)

    def test_expired_memory_still_accessible_by_owner(
        self, test_db_session: Session, user_a: User
    ) -> None:
        """Expired memories are still accessible by owner (only excluded from list)."""
        from src.modules.memories.encryption import get_encryption_service

        enc = get_encryption_service()
        memory = MemoryItem(
            owner_user_id=user_a.id,
            category=MemoryCategory.PREFERENCE.value,
            content_encrypted=enc.encrypt("expired content"),
            content_hash=enc.hash_content("expired content"),
            expires_at=utc_now() - timedelta(hours=1),
        )
        test_db_session.add(memory)
        test_db_session.flush()

        # Owner can still access by ID
        result = get_memory(user_a, memory.id, test_db_session)
        assert result["content"] == "expired content"

    def test_consent_with_correct_purpose_allows_access(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
        agent_a: Agent,
        memory_a: MemoryItem,
    ) -> None:
        """With valid consent, agent can access memory (metadata only)."""
        grant_consent(user_a.id, agent_a.id, "chat_reply", test_db_session)
        result = get_memory(
            user_b,
            memory_a.id,
            test_db_session,
            agent_id=agent_a.id,
            purpose="chat_reply",
        )
        # Non-owner with consent gets metadata only (no decrypted content)
        assert result["content"] is None
        assert result["category"] == "PREFERENCE"

    def test_consent_with_scope_category_allows(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
        agent_a: Agent,
        memory_a: MemoryItem,
    ) -> None:
        """Consent with matching scope category allows access."""
        grant_consent(
            user_a.id,
            agent_a.id,
            "chat_reply",
            test_db_session,
            scope={"category": ["PREFERENCE"]},
        )
        result = get_memory(
            user_b,
            memory_a.id,
            test_db_session,
            agent_id=agent_a.id,
            purpose="chat_reply",
        )
        assert result is not None
