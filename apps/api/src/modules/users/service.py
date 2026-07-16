"""
Users service for CampusAgent.

Provides:
- ``get_user_public_profile(user_id, session) -> dict``: get public profile.
- ``update_user_profile(user_id, data, actor_id, session) -> User``: update profile.
- ``deactivate_user(user_id, session) -> None``: soft-delete + revoke sessions (P3-09).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.time import utc_now
from ..auth.models import AuthSession, SessionStatus
from ..auth.service import _revoke_family
from .models import StudentProfile, User, UserStatus
from .repository import UserRepository


def get_user_public_profile(user_id: UUID, session: Session) -> dict[str, Any]:
    """Get a user's public profile.

    Returns only safe fields: id, display_name, avatar_url, profile_visibility.
    Does NOT include email, student_no, password_hash, or session info.

    Raises:
        NotFoundError: If user not found or deleted.
    """
    from ...utils.errors import NotFoundError

    user = UserRepository(session).get_by_id(user_id)
    if user is None or user.status == UserStatus.DELETED.value:
        raise NotFoundError("用户")

    # Get profile visibility
    stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
    profile = session.execute(stmt).scalar_one_or_none()

    visibility = profile.profile_visibility if profile else "PUBLIC"

    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "profile_visibility": visibility,
    }


def update_user_profile(
    user_id: UUID,
    data: dict[str, Any],
    actor_id: UUID,
    session: Session,
) -> User:
    """Update a user's profile.

    Only the user themselves can update. Only display_name, bio,
    avatar_url, and profile_visibility are updatable.

    Raises:
        NotFoundError: If user not found.
        AuthorizationError: If actor is not the user.
    """
    from ...utils.errors import AuthorizationError, NotFoundError

    user = UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("用户")

    if actor_id != user_id:
        raise AuthorizationError("无权限修改此用户")

    # Update allowed fields
    if "display_name" in data and data["display_name"] is not None:
        user.display_name = data["display_name"]
    if "avatar_url" in data:
        user.avatar_url = data["avatar_url"]

    # Update student profile fields
    stmt = select(StudentProfile).where(StudentProfile.user_id == user_id)
    profile = session.execute(stmt).scalar_one_or_none()
    if profile is not None:
        if "bio" in data:
            profile.bio = data["bio"]
        if "profile_visibility" in data and data["profile_visibility"] is not None:
            profile.profile_visibility = data["profile_visibility"]

    session.commit()
    session.refresh(user)
    return user


def deactivate_user(user_id: UUID, session: Session) -> None:
    """Soft-delete a user: set status to DELETED, set deleted_at, revoke all sessions.

    This is the P3-09 account deletion flow. Does NOT hard-delete the User
    record (to preserve audit foreign keys).

    Raises:
        NotFoundError: If user not found.
    """
    from ...utils.errors import NotFoundError

    user = UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError("用户")

    # Soft delete
    user.status = UserStatus.DELETED.value
    user.deleted_at = utc_now()

    # Revoke all active sessions
    stmt = select(AuthSession).where(
        AuthSession.user_id == user_id,
        AuthSession.status == SessionStatus.ACTIVE.value,
    )
    active_sessions = session.execute(stmt).scalars().all()
    for s in active_sessions:
        s.status = SessionStatus.REVOKED.value
        s.revoked_at = utc_now()
        _revoke_family(session, s.family_id, mark_compromised=False)

    session.commit()
