"""Consent service for memory access control.

Implements grant/check/revoke/expire logic.
Consent revoke takes effect immediately.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ..audit.service import log_audit
from .exceptions import ConsentNotFoundError
from .models import ConsentRecord, ConsentStatus
from .repository import ConsentRepository


def grant_consent(
    grantor_id: UUID,
    agent_id: UUID,
    purpose: str,
    session: Session,
    *,
    scope: dict[str, Any] | None = None,
    expires_at: datetime | None = None,
    memory_id: UUID | None = None,
) -> dict[str, Any]:
    """Grant consent for an agent to access memories for a purpose."""
    repo = ConsentRepository(session)

    # Check if already has active consent
    existing = repo.get_active(grantor_id, agent_id, purpose)
    if existing is not None:
        return _consent_to_read(existing)

    consent = ConsentRecord(
        grantor_user_id=grantor_id,
        grantee_agent_id=agent_id,
        purpose=purpose,
        scope_json=json.dumps(scope) if scope else None,
        status=ConsentStatus.GRANTED.value,
        granted_at=utc_now(),
        expires_at=expires_at,
        memory_id=memory_id,
    )
    repo.create(consent)
    session.commit()
    session.refresh(consent)

    log_audit(
        actor_id=grantor_id,
        action="consent_grant",
        resource_type="consent",
        resource_id=str(consent.id),
        purpose=purpose,
        result="SUCCESS",
        session=session,
    )
    return _consent_to_read(consent)


def check_consent(
    grantor_id: UUID,
    agent_id: UUID,
    purpose: str,
    session: Session,
    *,
    category: str | None = None,
) -> bool:
    """Check if consent is active. Returns True if granted, False otherwise."""
    repo = ConsentRepository(session)
    consent = repo.get_active(grantor_id, agent_id, purpose)
    if consent is None:
        return False

    # Check scope if category is specified
    if category and consent.scope_json:
        scope = json.loads(consent.scope_json)
        allowed_categories = scope.get("category")
        if allowed_categories and isinstance(allowed_categories, list) and category not in allowed_categories:
            return False

    return True


def revoke_consent(
    grantor_id: UUID,
    consent_id: UUID,
    session: Session,
) -> None:
    """Revoke consent. Takes effect immediately."""
    repo = ConsentRepository(session)
    consent = repo.get_by_id(consent_id)
    if consent is None:
        raise ConsentNotFoundError()
    if consent.grantor_user_id != grantor_id:
        raise ConsentNotFoundError(message="授权记录不存在")
    repo.revoke(consent)
    session.commit()

    log_audit(
        actor_id=grantor_id,
        action="consent_revoke",
        resource_type="consent",
        resource_id=str(consent.id),
        purpose=consent.purpose,
        result="SUCCESS",
        session=session,
    )


def list_consents(
    grantor_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """List all consent records for a user."""
    repo = ConsentRepository(session)
    consents = repo.list_by_grantor(grantor_id)
    return {
        "consents": [_consent_to_read(c) for c in consents],
        "total": len(consents),
    }


def _consent_to_read(consent: ConsentRecord) -> dict[str, Any]:
    return {
        "id": str(consent.id),
        "grantor_user_id": str(consent.grantor_user_id),
        "grantee_agent_id": str(consent.grantee_agent_id),
        "purpose": consent.purpose,
        "scope": json.loads(consent.scope_json) if consent.scope_json else None,
        "status": consent.status,
        "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
        "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
        "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
    }
