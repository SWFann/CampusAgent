"""
Organizations API routes for CampusAgent.

Provides:
- POST /api/v1/organizations — create org (auth + CSRF)
- GET /api/v1/organizations — list orgs (optional auth)
- GET /api/v1/organizations/{organization_id} — get org (optional auth)
- PATCH /api/v1/organizations/{organization_id} — update org (auth + CSRF)
- DELETE /api/v1/organizations/{organization_id} — delete org (auth + CSRF)
- POST /api/v1/organizations/{organization_id}/members — add member (auth + CSRF)
- GET /api/v1/organizations/{organization_id}/members — list members (auth)
- PATCH /api/v1/organizations/{organization_id}/members/{user_id} — update role (auth + CSRF)
- DELETE /api/v1/organizations/{organization_id}/members/{user_id} — remove member (auth + CSRF)
- POST /api/v1/organizations/{organization_id}/join — join org (auth + CSRF)
- POST /api/v1/organizations/{organization_id}/leave — leave org (auth + CSRF)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user, get_optional_current_user
from ..users.models import User
from . import service
from .schemas import (
    OrganizationCreateRequest,
    OrganizationInvitationDecisionRequest,
    OrganizationInvitationRequest,
    OrganizationMemberAddRequest,
    OrganizationMemberReviewRequest,
    OrganizationMemberUpdateRequest,
    OrganizationOwnershipTransferRequest,
    OrganizationUpdateRequest,
)

router = APIRouter(prefix="/api/v1/organizations", tags=["organizations"])


# ---------------------------------------------------------------------------
# POST /api/v1/organizations
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
def create_organization(
    body: OrganizationCreateRequest,
    http_request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Create a new organization. Auth + CSRF required."""
    data = body.model_dump(exclude_unset=True)
    result = service.create_organization(
        actor=current_user,
        data=data,
        session=db_session,
    )
    # Set Location header
    response.headers["Location"] = f"/api/v1/organizations/{result['id']}"
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/organizations
# ---------------------------------------------------------------------------


@router.get("", status_code=status.HTTP_200_OK)
def list_organizations(
    http_request: Request,
    org_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    actor: User | None = Depends(get_optional_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List organizations visible to the caller. Optional auth."""
    result = service.list_organizations(
        actor=actor,
        org_type=org_type,
        page=page,
        page_size=page_size,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/organizations/{organization_id}
# ---------------------------------------------------------------------------


@router.get("/{organization_id}", status_code=status.HTTP_200_OK)
def get_organization(
    organization_id: UUID,
    http_request: Request,
    actor: User | None = Depends(get_optional_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a single organization. Optional auth (visibility-gated)."""
    result = service.get_organization(
        actor=actor,
        organization_id=organization_id,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/organizations/{organization_id}
# ---------------------------------------------------------------------------


@router.patch("/{organization_id}", status_code=status.HTTP_200_OK)
def update_organization(
    organization_id: UUID,
    body: OrganizationUpdateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Update an organization. Auth + CSRF required."""
    data = body.model_dump(exclude_unset=True)
    result = service.update_organization(
        actor=current_user,
        organization_id=organization_id,
        data=data,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/organizations/{organization_id}
# ---------------------------------------------------------------------------


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    organization_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Soft-delete an organization. Auth + CSRF required."""
    service.delete_organization(
        actor=current_user,
        organization_id=organization_id,
        session=db_session,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /api/v1/organizations/{organization_id}/members
# ---------------------------------------------------------------------------


@router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    organization_id: UUID,
    body: OrganizationMemberAddRequest,
    http_request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Add a member to an organization. Auth + CSRF required."""
    result = service.add_member(
        actor=current_user,
        organization_id=organization_id,
        target_user_id=body.user_id,
        target_role=body.role,
        session=db_session,
    )
    response.headers["Location"] = f"/api/v1/organizations/{organization_id}/members/{body.user_id}"
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


@router.post("/{organization_id}/invitations", status_code=status.HTTP_201_CREATED)
def invite_member(
    organization_id: UUID,
    body: OrganizationInvitationRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Invite a campus user to join an organization."""
    result = service.invite_member(
        actor=current_user,
        organization_id=organization_id,
        target_user_id=body.user_id,
        target_role=body.role,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


@router.post("/{organization_id}/invitation", status_code=status.HTTP_200_OK)
def decide_invitation(
    organization_id: UUID,
    body: OrganizationInvitationDecisionRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Accept or decline the current user's organization invitation."""
    result = service.decide_invitation(
        actor=current_user,
        organization_id=organization_id,
        decision=body.decision,
        session=db_session,
    )
    return success(
        data={"decision": body.decision, "member": result},
        request_id=getattr(http_request.state, "request_id", None),
    )


@router.post("/{organization_id}/ownership-transfer", status_code=status.HTTP_200_OK)
def transfer_ownership(
    organization_id: UUID,
    body: OrganizationOwnershipTransferRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Transfer ownership to another active member."""
    result = service.transfer_ownership(
        actor=current_user,
        organization_id=organization_id,
        target_user_id=body.user_id,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/organizations/{organization_id}/members
# ---------------------------------------------------------------------------


@router.get("/{organization_id}/members", status_code=status.HTTP_200_OK)
def list_members(
    organization_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    status_filter: str = "ACTIVE",
) -> dict[str, Any]:
    """List members of an organization. Auth required."""
    result = service.list_members(
        actor=current_user,
        organization_id=organization_id,
        session=db_session,
        status_filter=status_filter,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


@router.post(
    "/{organization_id}/members/{user_id}/review",
    status_code=status.HTTP_200_OK,
)
def review_member_request(
    organization_id: UUID,
    user_id: UUID,
    body: OrganizationMemberReviewRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Approve or reject a pending membership request."""
    result = service.review_member_request(
        actor=current_user,
        organization_id=organization_id,
        target_user_id=user_id,
        decision=body.decision,
        target_role=body.role,
        session=db_session,
    )
    return success(
        data={"decision": body.decision, "member": result},
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/organizations/{organization_id}/members/{user_id}
# ---------------------------------------------------------------------------


@router.patch("/{organization_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def update_member_role(
    organization_id: UUID,
    user_id: UUID,
    body: OrganizationMemberUpdateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Update a member's role. Auth + CSRF required."""
    result = service.update_member_role(
        actor=current_user,
        organization_id=organization_id,
        target_user_id=user_id,
        new_role=body.role,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/organizations/{organization_id}/members/{user_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    organization_id: UUID,
    user_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Remove a member from an organization. Auth + CSRF required."""
    service.remove_member(
        actor=current_user,
        organization_id=organization_id,
        target_user_id=user_id,
        session=db_session,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /api/v1/organizations/{organization_id}/join
# ---------------------------------------------------------------------------


@router.post("/{organization_id}/join", status_code=status.HTTP_201_CREATED)
def join_organization(
    organization_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Join an organization via self-service. Auth + CSRF required."""
    result = service.join_organization(
        actor=current_user,
        organization_id=organization_id,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/organizations/{organization_id}/leave
# ---------------------------------------------------------------------------


@router.post("/{organization_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_organization(
    organization_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Leave an organization. Auth + CSRF required."""
    service.leave_organization(
        actor=current_user,
        organization_id=organization_id,
        session=db_session,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
