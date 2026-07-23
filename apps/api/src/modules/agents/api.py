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
from .schemas import AgentModelRouteUpdate, WorkspaceChatRequest, WorkspaceThreadCreate

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


@router.post("/me/chat")
def chat_with_my_agent(
    body: WorkspaceChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Chat with the current user's personal Agent via the model gateway."""
    content = body.message or (body.messages[-1].content if body.messages else "")
    data = service.chat_with_personal_agent(current_user, body.thread_id, content, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/me/workspace/threads")
def list_my_workspace_threads(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List only the current student's personal task conversations."""
    data = service.list_workspace_threads(current_user, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/me/workspace/threads")
def create_my_workspace_thread(
    body: WorkspaceThreadCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Create a new empty personal task conversation."""
    data = service.create_workspace_thread(current_user, db_session, title=body.title)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/me/workspace/threads/{thread_id}")
def get_my_workspace_thread(
    thread_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Read and decrypt one task conversation for its owner only."""
    data = service.get_workspace_thread(current_user, thread_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/me/model-route")
def get_my_model_route(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Return the current user's route without ever returning an API key."""
    data = service.get_agent_model_route(current_user, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.patch("/me/model-route")
def update_my_model_route(
    body: AgentModelRouteUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Encrypt and save the current user's personal model route."""
    data = service.update_agent_model_route(
        current_user,
        db_session,
        mode=body.mode,
        profile_id=body.profile_id,
        name=body.name,
        provider=body.provider,
        base_url=body.base_url,
        model=body.model,
        api_key=body.api_key,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.delete("/me/model-route/profiles/{profile_id}")
def delete_my_model_route_profile(
    profile_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Delete one saved personal model configuration."""
    data = service.delete_agent_model_route_profile(current_user, db_session, profile_id)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/me/model-route/test")
def test_my_model_route(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Probe the saved route without sending conversation content."""
    data = service.test_agent_model_route(current_user, db_session)
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
