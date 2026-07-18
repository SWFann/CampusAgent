"""Contact API routes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user
from ..users.models import User
from . import service
from .schemas import ContactRequestCreate

router = APIRouter(prefix="/api/v1/contacts", tags=["contacts"])


@router.get("", status_code=status.HTTP_200_OK)
def list_contacts(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    data = service.list_contacts(current_user, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.get("/requests", status_code=status.HTTP_200_OK)
def list_requests(
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    data = service.list_contact_requests(current_user, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_request(
    body: ContactRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    data = service.create_contact_request(current_user, body.target_user_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/requests/{request_id}/accept", status_code=status.HTTP_200_OK)
def accept_request(
    request_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    data = service.accept_contact_request(current_user, request_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.post("/requests/{request_id}/reject", status_code=status.HTTP_200_OK)
def reject_request(
    request_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    data = service.reject_contact_request(current_user, request_id, db_session)
    return success(data=data, request_id=getattr(request.state, "correlation_id", None))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> None:
    service.delete_contact(current_user, user_id, db_session)
