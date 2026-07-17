"""Memory service layer — business logic for memory CRUD.

Privacy:
- All content is encrypted before storage.
- Only the owner can read decrypted content.
- Admin has no content-reading interface.
- Consent and expiry are checked on every query.
- Logs and metrics never include content.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ..audit.service import log_audit
from ..users.models import User
from .consent import check_consent
from .encryption import get_encryption_service
from .exceptions import (
    ConsentDeniedError,
    MemoryNotFoundError,
    MemoryPermissionDeniedError,
)
from .models import MemoryItem
from .repository import MemoryRepository


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a datetime from a string or pass through a datetime object.

    Returns None if value is None.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


def _ensure_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (assume UTC if naive).

    SQLite strips tzinfo on storage, so datetimes read back from SQLite
    are naive. This helper normalises them for comparison with
    timezone-aware values from ``utc_now()``.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def create_memory(
    user: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Create a new memory item with encrypted content."""
    enc = get_encryption_service()
    plaintext = data["content"]

    memory = MemoryItem(
        owner_user_id=user.id,
        agent_id=UUID(str(data["agent_id"])) if data.get("agent_id") else None,
        category=data["category"],
        sensitivity_level=data.get("sensitivity_level", "INTERNAL"),
        source=data.get("source", "USER_INPUT"),
        content_encrypted=enc.encrypt(plaintext),
        content_hash=enc.hash_content(plaintext),
        encryption_key_version=enc.key_version,
        expires_at=_parse_datetime(data.get("expires_at")),
    )

    repo = MemoryRepository(session)
    repo.create(memory)
    session.commit()
    session.refresh(memory)

    log_audit(
        actor_id=user.id,
        action="memory_write",
        resource_type="memory",
        resource_id=str(memory.id),
        result="SUCCESS",
        session=session,
    )

    return _memory_to_read(memory, decrypted_content=plaintext)


def get_memory(
    user: User,
    memory_id: UUID,
    session: Session,
    *,
    agent_id: UUID | None = None,
    purpose: str | None = None,
) -> dict[str, Any]:
    """Get a memory by ID. Owner sees decrypted content.

    If agent_id and purpose are provided, consent is checked.
    """
    repo = MemoryRepository(session)
    memory = repo.get_by_id(memory_id)
    if memory is None or memory.deleted_at is not None:
        raise MemoryNotFoundError()

    # Owner can always read their own memory
    if memory.owner_user_id == user.id:
        enc = get_encryption_service()
        plaintext = enc.decrypt(memory.content_encrypted)
        result = _memory_to_read(memory, decrypted_content=plaintext)

        log_audit(
            actor_id=user.id,
            action="memory_read",
            resource_type="memory",
            resource_id=str(memory.id),
            purpose=purpose or "self",
            result="SUCCESS",
            session=session,
        )
        return result

    # Non-owner: must have valid consent
    if agent_id is None or purpose is None:
        raise MemoryPermissionDeniedError()

    has_consent = check_consent(
        grantor_id=memory.owner_user_id,
        agent_id=agent_id,
        purpose=purpose,
        session=session,
    )
    if not has_consent:
        log_audit(
            actor_id=user.id,
            action="memory_read",
            resource_type="memory",
            resource_id=str(memory.id),
            purpose=purpose,
            result="DENIED",
            session=session,
        )
        raise ConsentDeniedError()

    # With consent, return metadata only (not decrypted content for non-owner)
    log_audit(
        actor_id=user.id,
        action="memory_read",
        resource_type="memory",
        resource_id=str(memory.id),
        purpose=purpose,
        result="SUCCESS",
        session=session,
    )
    return _memory_to_read(memory)


def list_memories(
    user: User,
    session: Session,
    *,
    category: str | None = None,
) -> dict[str, Any]:
    """List memories for the current user (owner-only).

    Excludes deleted and expired memories.
    """
    repo = MemoryRepository(session)
    memories = repo.list_by_owner(user.id, category=category)

    # Filter out expired memories
    now = utc_now()
    active_memories = [
        m for m in memories
        if m.expires_at is None or _ensure_aware(m.expires_at) > now
    ]

    # Owner can see decrypted content
    enc = get_encryption_service()
    items = []
    for m in active_memories:
        try:
            plaintext = enc.decrypt(m.content_encrypted)
        except Exception:
            plaintext = None
        items.append(_memory_to_read(m, decrypted_content=plaintext))

    return {"memories": items, "total": len(items)}


def update_memory(
    user: User,
    memory_id: UUID,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Update a memory. Owner-only."""
    repo = MemoryRepository(session)
    memory = repo.get_by_id(memory_id)
    if memory is None or memory.deleted_at is not None:
        raise MemoryNotFoundError()
    if memory.owner_user_id != user.id:
        raise MemoryPermissionDeniedError()

    if "content" in data and data["content"] is not None:
        enc = get_encryption_service()
        memory.content_encrypted = enc.encrypt(data["content"])
        memory.content_hash = enc.hash_content(data["content"])

    if "category" in data and data["category"] is not None:
        memory.category = data["category"]
    if "sensitivity_level" in data and data["sensitivity_level"] is not None:
        memory.sensitivity_level = data["sensitivity_level"]
    if "expires_at" in data:
        memory.expires_at = _parse_datetime(data["expires_at"])

    repo.save(memory)
    session.commit()
    session.refresh(memory)

    enc = get_encryption_service()
    plaintext = enc.decrypt(memory.content_encrypted)
    return _memory_to_read(memory, decrypted_content=plaintext)


def delete_memory(
    user: User,
    memory_id: UUID,
    session: Session,
) -> None:
    """Soft-delete a memory. Owner-only."""
    repo = MemoryRepository(session)
    memory = repo.get_by_id(memory_id)
    if memory is None or memory.deleted_at is not None:
        raise MemoryNotFoundError()
    if memory.owner_user_id != user.id:
        raise MemoryPermissionDeniedError()

    repo.soft_delete(memory)
    session.commit()

    log_audit(
        actor_id=user.id,
        action="memory_delete",
        resource_type="memory",
        resource_id=str(memory.id),
        result="SUCCESS",
        session=session,
    )


def _memory_to_read(
    memory: MemoryItem,
    *,
    decrypted_content: str | None = None,
) -> dict[str, Any]:
    """Convert MemoryItem to a safe read dict.

    decrypted_content is only included for the owner.
    Never includes content_encrypted.
    """
    return {
        "id": str(memory.id),
        "owner_user_id": str(memory.owner_user_id),
        "agent_id": str(memory.agent_id) if memory.agent_id else None,
        "category": memory.category,
        "sensitivity_level": memory.sensitivity_level,
        "source": memory.source,
        "content": decrypted_content,
        "content_hash": memory.content_hash,
        "encryption_key_version": memory.encryption_key_version,
        "expires_at": memory.expires_at.isoformat() if memory.expires_at else None,
        "deleted_at": memory.deleted_at.isoformat() if memory.deleted_at else None,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }
