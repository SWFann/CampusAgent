"""
Auth dependencies for CampusAgent.

Provides:
- ``get_current_user(request, db_session, settings) -> User``: FastAPI
  dependency that extracts and validates the access token from the Cookie,
  returning the authenticated user.

Design principles:
- Access token is read from the ``access_token`` HttpOnly Cookie.
- Expired, invalid, or missing tokens raise ``InvalidTokenError`` (401).
- Disabled or deleted users are rejected with ``InvalidTokenError`` to
  avoid leaking account status.
- ``request.state.actor_id`` is set for request-context logging.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ...config import Settings
from ...dependencies import get_db_session, get_settings
from ..users.models import User, UserStatus
from ..users.repository import UserRepository
from .exceptions import InvalidTokenError
from .tokens import TokenType, decode_token


def get_current_user(
    request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Extract and validate the access token from the Cookie.

    This is the primary authentication dependency for all authenticated
    endpoints (GET /auth/me, PATCH /users/{id}, etc.).

    Returns:
        The authenticated ``User`` instance.

    Raises:
        InvalidTokenError: If the token is missing, invalid, expired,
            or the user is disabled/deleted.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise InvalidTokenError()

    try:
        payload = decode_token(access_token, settings)
    except Exception:
        raise InvalidTokenError() from None

    if payload.get("typ") != TokenType.ACCESS.value:
        raise InvalidTokenError()

    user_id_str = str(payload.get("sub", ""))
    if not user_id_str:
        raise InvalidTokenError()

    try:
        user_uuid = UUID(user_id_str)
    except (ValueError, TypeError):
        raise InvalidTokenError() from None

    user = UserRepository(db_session).get_by_id(user_uuid)
    if user is None:
        raise InvalidTokenError()

    # Reject disabled/deleted users
    if user.status in (UserStatus.DISABLED.value, UserStatus.DELETED.value):
        raise InvalidTokenError()

    # Set actor_id for request-context logging
    request.state.actor_id = str(user.id)

    return user


def get_optional_current_user(
    request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """Extract and validate the access token from the Cookie, returning None
    if the user is not authenticated.

    This is the optional-authentication dependency for public read endpoints
    that need to trim results based on whether the caller is authenticated
    and/or a member of an organization.

    Returns:
        The authenticated ``User`` instance, or ``None`` if no valid token
        is present.

    Unlike ``get_current_user``, this NEVER raises — it silently returns
    ``None`` for any auth failure (missing, invalid, expired, disabled).
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        return None

    try:
        payload = decode_token(access_token, settings)
    except Exception:
        return None

    if payload.get("typ") != TokenType.ACCESS.value:
        return None

    user_id_str = str(payload.get("sub", ""))
    if not user_id_str:
        return None

    try:
        user_uuid = UUID(user_id_str)
    except (ValueError, TypeError):
        return None

    user = UserRepository(db_session).get_by_id(user_uuid)
    if user is None:
        return None

    # Reject disabled/deleted users silently
    if user.status in (UserStatus.DISABLED.value, UserStatus.DELETED.value):
        return None

    # Set actor_id for request-context logging
    request.state.actor_id = str(user.id)

    return user
