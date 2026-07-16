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
