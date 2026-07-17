"""Memory repository for database access."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from .models import ConsentRecord, ConsentStatus, MemoryItem


class MemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, memory: MemoryItem) -> MemoryItem:
        self._session.add(memory)
        self._session.flush()
        return memory

    def get_by_id(self, memory_id: UUID) -> MemoryItem | None:
        return self._session.get(MemoryItem, memory_id)

    def list_by_owner(
        self, owner_id: UUID, *, category: str | None = None, limit: int = 50
    ) -> list[MemoryItem]:
        query = self._session.query(MemoryItem).filter(
            MemoryItem.owner_user_id == owner_id,
            MemoryItem.deleted_at.is_(None),
        )
        if category:
            query = query.filter(MemoryItem.category == category)
        return query.order_by(MemoryItem.created_at.desc()).limit(limit).all()

    def soft_delete(self, memory: MemoryItem) -> None:
        memory.deleted_at = utc_now()

    def get_expired(self, limit: int = 100) -> list[MemoryItem]:
        now = utc_now()
        return (
            self._session.query(MemoryItem)
            .filter(
                MemoryItem.expires_at.is_not(None),
                MemoryItem.expires_at < now,
                MemoryItem.deleted_at.is_(None),
            )
            .limit(limit)
            .all()
        )

    def save(self, memory: MemoryItem) -> MemoryItem:
        self._session.flush()
        return memory


class ConsentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, consent: ConsentRecord) -> ConsentRecord:
        self._session.add(consent)
        self._session.flush()
        return consent

    def get_by_id(self, consent_id: UUID) -> ConsentRecord | None:
        return self._session.get(ConsentRecord, consent_id)

    def get_active(
        self,
        grantor_id: UUID,
        agent_id: UUID,
        purpose: str,
    ) -> ConsentRecord | None:
        now = utc_now()
        return (
            self._session.query(ConsentRecord)
            .filter(
                ConsentRecord.grantor_user_id == grantor_id,
                ConsentRecord.grantee_agent_id == agent_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.status == ConsentStatus.GRANTED.value,
                ConsentRecord.revoked_at.is_(None),
            )
            .filter(
                (ConsentRecord.expires_at.is_(None))
                | (ConsentRecord.expires_at > now)
            )
            .first()
        )

    def list_by_grantor(self, grantor_id: UUID) -> list[ConsentRecord]:
        return (
            self._session.query(ConsentRecord)
            .filter(ConsentRecord.grantor_user_id == grantor_id)
            .order_by(ConsentRecord.created_at.desc())
            .all()
        )

    def revoke(self, consent: ConsentRecord) -> None:
        consent.status = ConsentStatus.REVOKED.value
        consent.revoked_at = utc_now()

    def get_revoked_consent_cleanup_candidates(self, limit: int = 50) -> list[ConsentRecord]:
        return (
            self._session.query(ConsentRecord)
            .filter(
                ConsentRecord.status == ConsentStatus.REVOKED.value,
                ConsentRecord.revoked_at.is_not(None),
            )
            .limit(limit)
            .all()
        )
