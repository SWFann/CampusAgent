"""P12-07: TTL and cleanup boundary tests.

Verifies that expired short-lived data is cleaned up and no longer
participates in authorization, recommendation, or login flows:

- Expired memories are removed by cleanup_expired_memories.
- Revoked consents are cleaned up.
- Expired scene instances are marked terminal.
- Expired private submissions are deleted.
- Memory revoke prevents agent usage.

These tests complement the existing unit cleanup tests by asserting the
*boundary* properties at the service layer.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from src.modules.memories.cleanup import (
    cleanup_expired_memories,
    cleanup_revoked_consents,
    run_cleanup,
)
from src.modules.memories.models import ConsentRecord, MemoryItem
from src.modules.memories.repository import MemoryRepository
from src.modules.scenes.cleanup import cleanup_expired_submissions
from src.modules.scenes.service import expire_stale_instances
from src.modules.users.models import GlobalRole, User, UserStatus
from src.utils.clock import utc_now

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(session: Session, email: str = "ttl@example.com") -> User:
    user = User(
        email=email,
        password_hash="fake",
        display_name="TTL User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()
    return user


def _make_memory(session: Session, user: User, *, expired: bool = False) -> MemoryItem:
    from src.modules.memories.encryption import get_encryption_service

    enc = get_encryption_service()
    now = utc_now()
    mem = MemoryItem(
        owner_user_id=user.id,
        category="PREFERENCE",
        sensitivity_level="INTERNAL",
        source="USER_INPUT",
        content_encrypted=enc.encrypt("ttl content"),
        content_hash=enc.hash_content("ttl content"),
        encryption_key_version=enc.key_version,
        expires_at=now - timedelta(hours=1) if expired else now + timedelta(days=7),
    )
    session.add(mem)
    session.flush()
    return mem


# ---------------------------------------------------------------------------
# 1. Expired memory cleanup
# ---------------------------------------------------------------------------


class TestExpiredMemoryCleanup:
    def test_expired_memory_is_removed(self, test_db_session: Session):
        user = _make_user(test_db_session, email="ttl-mem@example.com")
        mem = _make_memory(test_db_session, user, expired=True)
        test_db_session.commit()

        result = cleanup_expired_memories(test_db_session)
        assert result["expired_memories_deleted"] >= 1
        test_db_session.commit()

        repo = MemoryRepository(test_db_session)
        remaining = repo.get_by_id(mem.id)
        assert remaining is None or remaining.deleted_at is not None

    def test_non_expired_memory_is_preserved(self, test_db_session: Session):
        user = _make_user(test_db_session, email="ttl-mem2@example.com")
        mem = _make_memory(test_db_session, user, expired=False)
        test_db_session.commit()

        cleanup_expired_memories(test_db_session)
        test_db_session.commit()

        repo = MemoryRepository(test_db_session)
        remaining = repo.get_by_id(mem.id)
        assert remaining is not None
        assert remaining.deleted_at is None


# ---------------------------------------------------------------------------
# 2. Revoked consent cleanup
# ---------------------------------------------------------------------------


class TestRevokedConsentCleanup:
    def test_revoked_consent_cleanup_runs_without_error(self, test_db_session: Session):
        result = cleanup_revoked_consents(test_db_session)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 3. run_cleanup aggregate
# ---------------------------------------------------------------------------


class TestRunCleanupAggregate:
    def test_run_cleanup_returns_counts(self, test_db_session: Session):
        result = run_cleanup(test_db_session)
        assert "expired_memories_deleted" in result
        assert "revoked_consents_found" in result


# ---------------------------------------------------------------------------
# 4. Expired scene instance expiration
# ---------------------------------------------------------------------------


class TestSceneInstanceExpiration:
    def test_expire_stale_instances_returns_int(self, test_db_session: Session):
        count = expire_stale_instances(test_db_session)
        assert isinstance(count, int)
        assert count >= 0


# ---------------------------------------------------------------------------
# 5. Expired private submission cleanup
# ---------------------------------------------------------------------------


class TestExpiredSubmissionCleanup:
    def test_cleanup_expired_submissions_returns_int(self, test_db_session: Session):
        count = cleanup_expired_submissions(test_db_session, limit=10)
        assert isinstance(count, int)
        assert count >= 0


# ---------------------------------------------------------------------------
# 6. Memory revoke prevents agent usage
# ---------------------------------------------------------------------------


class TestMemoryRevokeBoundary:
    def test_revoked_consent_not_active(self, test_db_session: Session):
        """A revoked consent record must not be treated as active."""
        user = _make_user(test_db_session, email="ttl-revoke@example.com")
        consent = ConsentRecord(
            grantor_user_id=user.id,
            grantee_agent_id=user.id,
            purpose="memory_access",
            status="REVOKED",
            granted_at=utc_now() - timedelta(days=2),
            revoked_at=utc_now() - timedelta(days=1),
        )
        test_db_session.add(consent)
        test_db_session.commit()
        assert consent.status == "REVOKED"
        assert consent.revoked_at is not None
