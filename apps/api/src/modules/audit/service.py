"""Audit service — log and query audit records.

Privacy: audit records never contain content, prompt, or memory plaintext.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ..users.models import User
from .models import AuditLog
from .repository import AuditRepository


def log_audit(
    *,
    actor_id: UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    purpose: str | None = None,
    result: str = "SUCCESS",
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    session: Session,
) -> None:
    """Write an audit log entry. Never stores content/plaintext."""
    log_entry = AuditLog(
        actor_user_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        purpose=purpose,
        result=result,
        request_id=request_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    repo = AuditRepository(session)
    repo.create(log_entry)
    session.flush()  # Don't commit — caller controls transaction


def list_my_audit_logs(
    user: User,
    session: Session,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """List audit logs for the current user only."""
    repo = AuditRepository(session)
    logs = repo.list_by_actor(user.id, limit=limit)
    return {
        "audit_logs": [_audit_to_read(log) for log in logs],
        "total": len(logs),
    }


def _audit_to_read(log: AuditLog) -> dict[str, Any]:
    """Convert AuditLog to a safe read dict. No content/plaintext."""
    return {
        "id": str(log.id),
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "purpose": log.purpose,
        "result": log.result,
        "request_id": log.request_id,
        "metadata": json.loads(log.metadata_json) if log.metadata_json else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
