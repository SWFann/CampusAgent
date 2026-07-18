"""Memory API endpoints."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user
from ..users.models import User
from . import service
from .consent import grant_consent, list_consents, revoke_consent

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


@router.post("")
async def create_memory(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Create a new memory item."""
    body = await request.json()
    data = service.create_memory(current_user, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("")
async def list_memories(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    category: str | None = None,
) -> dict[str, Any]:
    """List memories for the current user."""
    data = service.list_memories(current_user, db_session, category=category)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


# --- Consent endpoints ---

@router.post("/consents")
async def grant_consent_api(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Grant consent for an agent to access memories."""
    body = await request.json()
    data = grant_consent(
        grantor_id=current_user.id,
        agent_id=UUID(str(body["agent_id"])),
        purpose=body["purpose"],
        session=db_session,
        scope=body.get("scope"),
        expires_at=body.get("expires_at"),
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/consents")
async def list_consents_api(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List consent records for the current user."""
    data = list_consents(current_user.id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.delete("/consents/{consent_id}")
async def revoke_consent_api(
    consent_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Revoke consent. Takes effect immediately."""
    revoke_consent(current_user.id, consent_id, db_session)
    return success(data=None, request_id=getattr(request.state, "correlation_id", None))


@router.get("/{memory_id}")
async def get_memory(
    memory_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    agent_id: UUID | None = None,
    purpose: str | None = None,
) -> dict[str, Any]:
    """Get a memory by ID."""
    data = service.get_memory(
        current_user, memory_id, db_session,
        agent_id=agent_id, purpose=purpose,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.patch("/{memory_id}")
async def update_memory(
    memory_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Update a memory."""
    body = await request.json()
    data = service.update_memory(current_user, memory_id, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Soft-delete a memory."""
    service.delete_memory(current_user, memory_id, db_session)
    return success(data=None, request_id=getattr(request.state, "correlation_id", None))
