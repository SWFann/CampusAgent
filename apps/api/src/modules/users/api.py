"""
Users API routes for CampusAgent.

Provides:
- GET /api/v1/users/{user_id} — public profile (P3-07)
- PATCH /api/v1/users/{user_id} — update profile (P3-07, CSRF required)
- GET /api/v1/users/{user_id}/organizations — placeholder (P3-07)
- GET /api/v1/users/{user_id}/agent — placeholder (P3-07)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from ...config import Settings
from ...dependencies import get_db_session, get_settings
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user
from .models import User
from .schemas import UserProfileUpdate, UserPublicRead
from .service import get_user_public_profile, update_user_profile

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ---------------------------------------------------------------------------
# GET /api/v1/users/{user_id}
# ---------------------------------------------------------------------------


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
def get_user(
    user_id: UUID,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get a user's public profile.

    Returns only safe fields. Does NOT include email, student_no,
    password_hash, or session info.
    """
    profile = get_user_public_profile(user_id, db_session)
    return success(
        data=profile,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# PATCH /api/v1/users/{user_id}
# ---------------------------------------------------------------------------


@router.patch("/{user_id}", status_code=status.HTTP_200_OK)
def update_user(
    user_id: UUID,
    body: UserProfileUpdate,
    http_request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Update a user's profile.

    Only the user themselves can update. CSRF required.
    Updatable: display_name, bio, avatar_url, profile_visibility.
    NOT updatable: email, student_no, global_role, status.
    """
    data = body.model_dump(exclude_unset=True)
    updated_user = update_user_profile(
        user_id=user_id,
        data=data,
        actor_id=current_user.id,
        session=db_session,
    )

    result = UserPublicRead(
        id=updated_user.id,
        display_name=updated_user.display_name,
        avatar_url=updated_user.avatar_url,
    )

    return success(
        data=result.model_dump(mode="json"),
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/users/{user_id}/organizations
# ---------------------------------------------------------------------------


@router.get("/{user_id}/organizations", status_code=status.HTTP_200_OK)
def get_user_organizations(
    user_id: UUID,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get a user's organizations.

    P3: Returns an empty list (organizations are P4).
    """
    # Verify user exists
    get_user_public_profile(user_id, db_session)
    return success(
        data={"organizations": []},
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/users/{user_id}/agent
# ---------------------------------------------------------------------------


@router.get("/{user_id}/agent", status_code=status.HTTP_200_OK)
def get_user_agent(
    user_id: UUID,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Get a user's agent.

    P3: Returns AGENT_NOT_FOUND (agents are P6).
    """
    from ...utils.errors import NotFoundError

    # Verify user exists
    get_user_public_profile(user_id, db_session)
    raise NotFoundError("智能体")
