"""Agent API endpoints."""
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

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/me")
async def get_my_agent(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get the current user's personal agent."""
    data = service.get_my_agent(current_user, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/{agent_id}")
async def get_agent(
    agent_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get an agent by ID. Owner sees full info; admin sees metadata only."""
    data = service.get_agent_by_id(current_user, agent_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Update an agent. Only the owner can update."""
    body = await request.json()
    data = service.update_agent(current_user, agent_id, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("")
async def list_my_agents(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List all agents owned by the current user."""
    data = service.list_my_agents(current_user, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))
