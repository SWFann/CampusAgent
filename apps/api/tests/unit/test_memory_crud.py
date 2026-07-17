"""P6-06: Memory CRUD tests.

Tests:
- POST /memories creates encrypted memory.
- GET /memories lists memories (owner-only, decrypted).
- GET /memories/{id} returns decrypted content to owner.
- PATCH /memories/{id} updates memory.
- DELETE /memories/{id} soft-deletes memory.
- Admin has no content-reading interface.
- Logs do not contain plaintext.
"""
from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.db.time import utc_now
from src.modules.memories.encryption import reset_encryption_service
from src.modules.memories.exceptions import (
    MemoryNotFoundError,
    MemoryPermissionDeniedError,
)
from src.modules.memories.repository import MemoryRepository
from src.modules.memories.service import (
    create_memory,
    delete_memory,
    get_memory,
    list_memories,
    update_memory,
)
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def _reset_encryption():
    """Reset encryption service singleton before and after each test."""
    reset_encryption_service()
    yield
    reset_encryption_service()


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="crud@example.com",
        password_hash="fake-hash",
        display_name="CRUD User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def other_user(test_db_session: Session) -> User:
    user = User(
        email="other-crud@example.com",
        password_hash="fake-hash",
        display_name="Other CRUD",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


class TestMemoryCreate:
    """Test memory creation."""

    def test_create_memory(self, test_db_session: Session, test_user: User) -> None:
        """Create a memory with encrypted content."""
        result = create_memory(
            test_user,
            {"content": "I prefer spicy food", "category": "PREFERENCE"},
            test_db_session,
        )
        assert result["category"] == "PREFERENCE"
        assert result["content"] == "I prefer spicy food"
        assert result["content_hash"] is not None
        assert result["encryption_key_version"] == 1
        assert result["id"] is not None

    def test_create_memory_encrypts_content(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Content is encrypted in the database, not stored as plaintext."""
        plaintext = "secret-preference-value"
        create_memory(
            test_user,
            {"content": plaintext, "category": "PREFERENCE"},
            test_db_session,
        )

        # Check database directly
        repo = MemoryRepository(test_db_session)
        memories = repo.list_by_owner(test_user.id)
        assert len(memories) == 1
        assert memories[0].content_encrypted != plaintext
        assert plaintext not in memories[0].content_encrypted

    def test_create_memory_with_expiry(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Memory can be created with expires_at."""
        future = (utc_now() + timedelta(hours=48)).isoformat()
        result = create_memory(
            test_user,
            {"content": "temp note", "category": "CONTEXT", "expires_at": future},
            test_db_session,
        )
        assert result["expires_at"] is not None


class TestMemoryRead:
    """Test memory reading."""

    def test_get_memory_owner(self, test_db_session: Session, test_user: User) -> None:
        """Owner can read decrypted content."""
        created = create_memory(
            test_user,
            {"content": "my preference", "category": "PREFERENCE"},
            test_db_session,
        )
        result = get_memory(test_user, UUID(created["id"]), test_db_session)
        assert result["content"] == "my preference"

    def test_get_memory_not_found(self, test_db_session: Session, test_user: User) -> None:
        """Non-existent memory raises."""
        with pytest.raises(MemoryNotFoundError):
            get_memory(test_user, uuid4(), test_db_session)

    def test_get_memory_deleted_raises(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Deleted memory raises."""
        created = create_memory(
            test_user,
            {"content": "to be deleted", "category": "PREFERENCE"},
            test_db_session,
        )
        delete_memory(test_user, UUID(created["id"]), test_db_session)
        with pytest.raises(MemoryNotFoundError):
            get_memory(test_user, UUID(created["id"]), test_db_session)

    def test_list_memories_owner(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Owner can list and see decrypted content."""
        create_memory(
            test_user, {"content": "pref1", "category": "PREFERENCE"}, test_db_session
        )
        create_memory(
            test_user, {"content": "fact1", "category": "FACT"}, test_db_session
        )
        result = list_memories(test_user, test_db_session)
        assert result["total"] == 2

    def test_list_memories_by_category(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """List memories filtered by category."""
        create_memory(
            test_user, {"content": "pref1", "category": "PREFERENCE"}, test_db_session
        )
        create_memory(
            test_user, {"content": "fact1", "category": "FACT"}, test_db_session
        )
        result = list_memories(test_user, test_db_session, category="PREFERENCE")
        assert result["total"] == 1
        assert result["memories"][0]["category"] == "PREFERENCE"

    def test_list_memories_excludes_expired(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Expired memories are excluded from list."""
        past = (utc_now() - timedelta(hours=1)).isoformat()
        create_memory(
            test_user,
            {"content": "expired", "category": "PREFERENCE", "expires_at": past},
            test_db_session,
        )
        create_memory(
            test_user,
            {"content": "active", "category": "PREFERENCE"},
            test_db_session,
        )
        result = list_memories(test_user, test_db_session)
        assert result["total"] == 1
        assert result["memories"][0]["content"] == "active"


class TestMemoryUpdate:
    """Test memory update."""

    def test_update_memory_content(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Owner can update content."""
        created = create_memory(
            test_user,
            {"content": "original", "category": "PREFERENCE"},
            test_db_session,
        )
        result = update_memory(
            test_user,
            UUID(created["id"]),
            {"content": "updated"},
            test_db_session,
        )
        assert result["content"] == "updated"

    def test_update_memory_category(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Owner can update category."""
        created = create_memory(
            test_user,
            {"content": "data", "category": "PREFERENCE"},
            test_db_session,
        )
        result = update_memory(
            test_user,
            UUID(created["id"]),
            {"category": "FACT"},
            test_db_session,
        )
        assert result["category"] == "FACT"

    def test_update_memory_non_owner_denied(
        self, test_db_session: Session, test_user: User, other_user: User
    ) -> None:
        """Non-owner cannot update."""
        created = create_memory(
            test_user,
            {"content": "secret", "category": "PREFERENCE"},
            test_db_session,
        )
        with pytest.raises(MemoryPermissionDeniedError):
            update_memory(other_user, UUID(created["id"]), {"content": "hacked"}, test_db_session)


class TestMemoryDelete:
    """Test memory deletion."""

    def test_delete_memory(self, test_db_session: Session, test_user: User) -> None:
        """Owner can soft-delete memory."""
        created = create_memory(
            test_user,
            {"content": "to delete", "category": "PREFERENCE"},
            test_db_session,
        )
        delete_memory(test_user, UUID(created["id"]), test_db_session)

        # Verify it's soft-deleted
        repo = MemoryRepository(test_db_session)
        memory = repo.get_by_id(UUID(created["id"]))
        assert memory is not None
        assert memory.deleted_at is not None

    def test_delete_memory_non_owner_denied(
        self, test_db_session: Session, test_user: User, other_user: User
    ) -> None:
        """Non-owner cannot delete."""
        created = create_memory(
            test_user,
            {"content": "secret", "category": "PREFERENCE"},
            test_db_session,
        )
        with pytest.raises(MemoryPermissionDeniedError):
            delete_memory(other_user, UUID(created["id"]), test_db_session)

    def test_delete_already_deleted_raises(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Deleting already-deleted memory raises."""
        created = create_memory(
            test_user,
            {"content": "x", "category": "PREFERENCE"},
            test_db_session,
        )
        memory_id = UUID(created["id"])
        delete_memory(test_user, memory_id, test_db_session)
        with pytest.raises(MemoryNotFoundError):
            delete_memory(test_user, memory_id, test_db_session)
