"""Memory cleanup task — expired memory soft-delete and revoked consent cleanup.

Reentrant: running twice is a no-op for already-processed items.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from .repository import ConsentRepository, MemoryRepository

logger = logging.getLogger("campus_agent.memories.cleanup")


def cleanup_expired_memories(session: Session) -> dict[str, int]:
    """Soft-delete expired memory items. Reentrant.

    Returns:
        Dict with count of cleaned-up items.
    """
    repo = MemoryRepository(session)
    expired = repo.get_expired(limit=100)
    count = 0
    for memory in expired:
        repo.soft_delete(memory)
        count += 1

    if count > 0:
        session.commit()

    logger.info("memory.cleanup.expired", extra={"count": count})
    return {"expired_memories_deleted": count}


def cleanup_revoked_consents(session: Session) -> dict[str, int]:
    """Clean up revoked consent records. Reentrant.

    Returns:
        Dict with count of cleaned-up items.
    """
    repo = ConsentRepository(session)
    revoked = repo.get_revoked_consent_cleanup_candidates(limit=50)
    # Revoked consents are kept for audit trail — we just log them
    count = len(revoked)
    logger.info("memory.cleanup.revoked_consents", extra={"count": count})
    return {"revoked_consents_found": count}


def run_cleanup(session: Session) -> dict[str, int]:
    """Run full cleanup cycle. Reentrant."""
    result1 = cleanup_expired_memories(session)
    result2 = cleanup_revoked_consents(session)
    return {**result1, **result2}
