"""P6-15: Privacy tests for memory and consent system.

Covers:
- A/B isolation: User A cannot read User B's memories.
- Admin rejection: Admin has no content-reading interface.
- Revoke immediate effect: Consent revoke takes effect immediately.
- Encryption fail-closed: Missing key or decryption failure rejects requests.
- Audit no content: Audit logs never contain memory content.
- Metrics/log no content: Logs do not contain memory plaintext.
"""
from __future__ import annotations

import logging
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.agents.models import Agent, AgentType, DelegationLevel
from src.modules.audit.repository import AuditRepository
from src.modules.memories.consent import grant_consent, revoke_consent
from src.modules.memories.encryption import (
    EncryptionService,
    reset_encryption_service,
)
from src.modules.memories.exceptions import ConsentDeniedError, MemoryPermissionDeniedError
from src.modules.memories.service import create_memory, get_memory, list_memories
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def _reset_encryption():
    reset_encryption_service()
    yield
    reset_encryption_service()


@pytest.fixture()
def user_a(test_db_session: Session) -> User:
    user = User(
        email="priv-a@example.com",
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
        email="priv-b@example.com",
        password_hash="fake",
        display_name="User B",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def admin_user(test_db_session: Session) -> User:
    user = User(
        email="priv-admin@example.com",
        password_hash="fake",
        display_name="Admin",
        global_role=GlobalRole.SYSTEM_ADMIN.value,
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


class TestABIsolation:
    """User A cannot access User B's memories."""

    def test_a_cannot_read_b_memory(
        self, test_db_session: Session, user_a: User, user_b: User
    ) -> None:
        """User A cannot read User B's memory without consent."""
        # User B creates a memory
        create_memory(
            user_b,
            {"content": "B's secret", "category": "PREFERENCE"},
            test_db_session,
        )

        # User A tries to list — should only see their own (empty)
        result = list_memories(user_a, test_db_session)
        assert result["total"] == 0

    def test_a_cannot_get_b_memory_by_id(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
    ) -> None:
        """User A cannot get User B's memory by ID without consent."""
        created = create_memory(
            user_b,
            {"content": "B's secret", "category": "PREFERENCE"},
            test_db_session,
        )
        with pytest.raises(MemoryPermissionDeniedError):
            get_memory(user_a, UUID(created["id"]), test_db_session)

    def test_a_list_only_own(
        self, test_db_session: Session, user_a: User, user_b: User
    ) -> None:
        """User A list returns only A's memories."""
        create_memory(
            user_a, {"content": "A's data", "category": "PREFERENCE"}, test_db_session
        )
        create_memory(
            user_b, {"content": "B's data", "category": "PREFERENCE"}, test_db_session
        )

        result_a = list_memories(user_a, test_db_session)
        result_b = list_memories(user_b, test_db_session)

        assert result_a["total"] == 1
        assert result_b["total"] == 1
        assert result_a["memories"][0]["content"] == "A's data"
        assert result_b["memories"][0]["content"] == "B's data"


class TestAdminNoContent:
    """Admin has no content-reading interface."""

    def test_admin_cannot_read_memory_content(
        self,
        test_db_session: Session,
        admin_user: User,
        user_a: User,
    ) -> None:
        """Admin cannot read memory content — no admin memory API exists."""
        # Create a memory as user_a
        create_memory(
            user_a,
            {"content": "A's private preference", "category": "PREFERENCE"},
            test_db_session,
        )

        # There is no admin API to read memory content.
        # The only memory API is /api/v1/memories which is owner-only.
        # list_memories only returns the current user's memories.
        admin_result = list_memories(admin_user, test_db_session)
        assert admin_result["total"] == 0  # Admin has no memories

    def test_admin_agent_no_private_config(
        self,
        test_db_session: Session,
        admin_user: User,
        user_a: User,
        agent_a: Agent,
    ) -> None:
        """Admin can read agent metadata but not private_config value."""
        from src.modules.agents.service import get_agent_by_id

        agent_a.private_config_encrypted = "encrypted-admin-secret"
        test_db_session.flush()

        result = get_agent_by_id(admin_user, agent_a.id, test_db_session)
        assert result["has_private_config"] is True
        assert "encrypted-admin-secret" not in str(result)
        assert "private_config_encrypted" not in result


class TestRevokeImmediateEffect:
    """Consent revoke takes effect immediately."""

    def test_revoke_blocks_subsequent_access(
        self,
        test_db_session: Session,
        user_a: User,
        user_b: User,
        agent_a: Agent,
    ) -> None:
        """After revoke, agent cannot access memory."""
        created = create_memory(
            user_a,
            {"content": "A's secret", "category": "PREFERENCE"},
            test_db_session,
        )
        result = grant_consent(user_a.id, agent_a.id, "chat_reply", test_db_session)
        revoke_consent(user_a.id, UUID(result["id"]), test_db_session)

        with pytest.raises(ConsentDeniedError):
            get_memory(
                user_b,
                UUID(created["id"]),
                test_db_session,
                agent_id=agent_a.id,
                purpose="chat_reply",
            )


class TestEncryptionFailClosed:
    """Encryption failure rejects requests."""

    def test_missing_key_raises(self) -> None:
        """Missing encryption key raises AppError."""
        from src.utils.errors import AppError

        with pytest.raises(AppError) as exc_info:
            EncryptionService(key="")
        assert exc_info.value.code == "ENCRYPTION_KEY_MISSING"

    def test_decryption_failure_raises(
        self, test_db_session: Session, user_a: User
    ) -> None:
        """Decryption failure with wrong ciphertext raises AppError."""
        from src.utils.errors import AppError

        # Create a memory with valid encryption
        create_memory(
            user_a,
            {"content": "valid content", "category": "PREFERENCE"},
            test_db_session,
        )

        # Corrupt the content_encrypted field directly
        from src.modules.memories.repository import MemoryRepository

        repo = MemoryRepository(test_db_session)
        memories = repo.list_by_owner(user_a.id)
        memories[0].content_encrypted = "corrupted-ciphertext"

        # Trying to read should raise on decryption
        with pytest.raises(AppError):
            get_memory(user_a, memories[0].id, test_db_session)

    def test_wrong_key_cannot_decrypt(
        self, test_db_session: Session, user_a: User
    ) -> None:
        """Data encrypted with one key cannot be decrypted with another."""
        from src.utils.errors import AppError

        # Create memory with default key
        create_memory(
            user_a,
            {"content": "secret data", "category": "PREFERENCE"},
            test_db_session,
        )

        # Reset and inject a different key into the singleton
        reset_encryption_service()
        import src.modules.memories.encryption as enc_mod

        enc_mod._encryption_service = enc_mod.EncryptionService(
            key="different-test-key-1234567890"
        )

        from src.modules.memories.repository import MemoryRepository

        repo = MemoryRepository(test_db_session)
        memories = repo.list_by_owner(user_a.id)

        with pytest.raises(AppError):
            get_memory(user_a, memories[0].id, test_db_session)

        # Restore original service
        reset_encryption_service()


class TestAuditNoContent:
    """Audit logs never contain memory content."""

    def test_audit_no_plaintext(
        self, test_db_session: Session, user_a: User
    ) -> None:
        """Audit log for memory_read does not contain plaintext."""
        plaintext = "super-secret-plaintext-marker-xyz"
        create_memory(
            user_a,
            {"content": plaintext, "category": "PREFERENCE"},
            test_db_session,
        )

        # Check all audit logs for this user
        repo = AuditRepository(test_db_session)
        logs = repo.list_by_actor(user_a.id)

        for log in logs:
            assert plaintext not in repr(log)
            if log.metadata_json:
                assert plaintext not in log.metadata_json

    def test_audit_no_encrypted_content(
        self, test_db_session: Session, user_a: User
    ) -> None:
        """Audit log does not contain encrypted content either."""
        create_memory(
            user_a,
            {"content": "test content for audit", "category": "PREFERENCE"},
            test_db_session,
        )

        from src.modules.memories.repository import MemoryRepository

        mem_repo = MemoryRepository(test_db_session)
        memories = mem_repo.list_by_owner(user_a.id)
        encrypted_content = memories[0].content_encrypted

        repo = AuditRepository(test_db_session)
        logs = repo.list_by_actor(user_a.id)

        for log in logs:
            assert encrypted_content not in repr(log)
            if log.metadata_json:
                assert encrypted_content not in log.metadata_json


class TestLogsNoContent:
    """Logs and metrics do not contain memory content."""

    def test_log_no_plaintext(
        self,
        test_db_session: Session,
        user_a: User,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Service logs do not contain plaintext."""
        plaintext = "log-plaintext-marker-abc123"
        with caplog.at_level(logging.DEBUG):
            create_memory(
                user_a,
                {"content": plaintext, "category": "PREFERENCE"},
                test_db_session,
            )

        for record in caplog.records:
            assert plaintext not in record.getMessage()
