"""
Directory API routes for CampusAgent.

Provides:
- GET /api/v1/directory/search — search users and organizations
- GET /api/v1/directory/tree — get organization tree
- GET /api/v1/directory/recommended — get recommended organizations

All endpoints use optional authentication to trim results based on
whether the caller is authenticated and/or a member of an organization.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.dependencies import get_optional_current_user
from ..users.models import User
from . import service

router = APIRouter(prefix="/api/v1/directory", tags=["directory"])


# ---------------------------------------------------------------------------
# GET /api/v1/directory/search
# ---------------------------------------------------------------------------


@router.get("/search", status_code=200)
def search_directory(
    http_request: Request,
    q: str = Query(..., description="Search query (min 2 characters)"),
    type: str = Query("all", description="Search type: all/users/organizations"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: User | None = Depends(get_optional_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Search the directory for users and organizations.

    Optional auth — results are trimmed based on the caller's identity.
    User results do NOT include email, student_no, or password_hash.
    Organization results respect visibility rules.
    """
    result = service.search_directory(
        actor=actor,
        q=q,
        search_type=type,
        limit=limit,
        offset=offset,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/directory/tree
# ---------------------------------------------------------------------------


@router.get("/tree", status_code=200)
def get_directory_tree(
    http_request: Request,
    root_organization_id: UUID | None = Query(
        None, description="Root org ID for subtree (None = all roots)"
    ),
    max_depth: int = Query(3, ge=1),
    actor: User | None = Depends(get_optional_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get the organization tree, filtered by the caller's permissions.

    Optional auth — PRIVATE/MEMBERS_ONLY nodes are hidden from non-members.
    """
    result = service.get_organization_tree(
        actor=actor,
        root_organization_id=root_organization_id,
        max_depth=max_depth,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/directory/recommended
# ---------------------------------------------------------------------------


@router.get("/recommended", status_code=200)
def get_recommended(
    http_request: Request,
    limit: int = Query(10, ge=1, le=50),
    actor: User | None = Depends(get_optional_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get recommended organizations for the current user.

    Uses only non-sensitive org relationships — no implicit profiling.
    Each recommendation includes a reason field for explainability.
    """
    result = service.get_recommended_organizations(
        actor=actor,
        limit=limit,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )
