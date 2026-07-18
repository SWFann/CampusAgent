"""Admin API endpoints for nodes, models, and deployments.

RBAC (P7 guide §14):
- POST/PATCH/DELETE nodes, POST models, POST deployments → SYSTEM_ADMIN only.
- GET endpoints, health-check, metrics → SCHOOL_ADMIN or SYSTEM_ADMIN.
- ORG_ADMIN does NOT have model management permissions.
- Cookie write requests require CSRF validation.

All admin routers are registered under /api/v1/admin/*.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user
from ..users.models import User
from . import service

# ---------------------------------------------------------------------------
# Nodes router
# ---------------------------------------------------------------------------

nodes_router = APIRouter(prefix="/api/v1/admin/nodes", tags=["admin-nodes"])


@nodes_router.post("", status_code=201)
async def create_node(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Register a new edge node. SYSTEM_ADMIN only."""
    body = await request.json()
    data = service.create_node(current_user, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@nodes_router.get("")
async def list_nodes(
    request: Request,
    status: str | None = Query(default=None),
    capability: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List all nodes. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    data = service.list_nodes(
        current_user,
        db_session,
        status=status,
        capability=capability,
        page=page,
        limit=limit,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@nodes_router.get("/{node_id}")
async def get_node(
    node_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a single node detail. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    data = service.get_node(current_user, node_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@nodes_router.patch("/{node_id}")
async def update_node(
    node_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Update node config. SYSTEM_ADMIN only."""
    body = await request.json()
    data = service.update_node(current_user, node_id, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@nodes_router.delete("/{node_id}")
async def delete_node(
    node_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Soft-delete a node. SYSTEM_ADMIN only."""
    service.delete_node(current_user, node_id, db_session)
    return success(data=None, request_id=getattr(request.state, "correlation_id", None))


@nodes_router.post("/{node_id}/health-check")
async def health_check(
    node_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Manually trigger a node health check. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    data = service.trigger_health_check(current_user, node_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@nodes_router.get("/{node_id}/metrics")
async def node_metrics(
    node_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get node resource metrics. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    data = service.get_node_metrics(current_user, node_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


# ---------------------------------------------------------------------------
# Models router
# ---------------------------------------------------------------------------

models_router = APIRouter(prefix="/api/v1/admin/models", tags=["admin-models"])


@models_router.post("", status_code=201)
async def create_model(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Register a new model configuration. SYSTEM_ADMIN only."""
    body = await request.json()
    data = service.create_model(current_user, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@models_router.get("")
async def list_models(
    request: Request,
    provider: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List model configurations. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    data = service.list_models(
        current_user,
        db_session,
        provider=provider,
        enabled=enabled,
        page=page,
        limit=limit,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


# ---------------------------------------------------------------------------
# Deployments router
# ---------------------------------------------------------------------------

deployments_router = APIRouter(prefix="/api/v1/admin/deployments", tags=["admin-deployments"])


@deployments_router.post("", status_code=201)
async def create_deployment(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Create a deployment record. SYSTEM_ADMIN only."""
    body = await request.json()
    data = service.create_deployment(current_user, body, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@deployments_router.get("")
async def list_deployments(
    request: Request,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List deployments. SCHOOL_ADMIN or SYSTEM_ADMIN."""
    data = service.list_deployments(
        current_user,
        db_session,
        status=status,
        page=page,
        limit=limit,
    )
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


# Backwards-compatible single router (includes all admin sub-routers).
router = APIRouter()
router.include_router(nodes_router)
router.include_router(models_router)
router.include_router(deployments_router)
