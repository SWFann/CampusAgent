"""Audit API endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.dependencies import get_current_user
from ..users.models import User
from . import service

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("/me")
async def list_my_audit_logs(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    limit: int = 50,
) -> dict[str, Any]:
    """List audit logs for the current user only. No content/plaintext."""
    data = service.list_my_audit_logs(current_user, db_session, limit=limit)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))
