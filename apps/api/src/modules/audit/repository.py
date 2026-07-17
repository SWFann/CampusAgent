"""Audit repository for database access."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from .models import AuditLog


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, log: AuditLog) -> AuditLog:
        self._session.add(log)
        self._session.flush()
        return log

    def list_by_actor(self, actor_id: UUID, *, limit: int = 50) -> list[AuditLog]:
        return (
            self._session.query(AuditLog)
            .filter(AuditLog.actor_user_id == actor_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
