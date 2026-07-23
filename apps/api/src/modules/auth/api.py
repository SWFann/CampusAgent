"""
Auth API routes for CampusAgent.

Provides:
- POST /api/v1/auth/register (P3-03)
- POST /api/v1/auth/login (P3-04)
- POST /api/v1/auth/refresh (P3-05)
- POST /api/v1/auth/logout (P3-05)
- GET /api/v1/auth/me (P3-06)

Register and login are CSRF-exempt (unauthenticated bootstrap endpoints).
Refresh, logout, and PATCH endpoints require CSRF validation.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from ...config import Settings
from ...dependencies import get_db_session, get_settings
from ...schemas.envelope import success
from ..users.models import User
from .cookies import clear_auth_cookies, generate_csrf_token, set_auth_cookies
from .csrf import require_csrf
from .dependencies import get_current_user
from .exceptions import InvalidTokenError
from .schemas import LoginRequest, RefreshResponse, RegisterRequest, UserRead
from .service import login_user, logout_user, refresh_token_rotation, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    http_request: Request,
    response: Response,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Register a new user.

    Creates User + StudentProfile + AuthSession + RefreshToken.
    Sets access_token, refresh_token, csrf_token as HttpOnly cookies.
    The response body does NOT contain any token strings.

    CSRF: exempt (bootstrap endpoint — client has no csrf_token yet).
    """
    result = register_user(
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        student_no=body.student_no,
        phone_number=body.phone_number,
        session=db_session,
        settings=settings,
    )

    # Set auth cookies (tokens are NOT in the response body)
    set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        csrf_token=result.csrf_token,
        settings=settings,
    )

    user_data = UserRead(
        id=result.user.id,
        email=result.user.email,
        display_name=result.user.display_name,
        global_role=result.user.global_role,
    )

    return success(
        data=user_data.model_dump(mode="json"),
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    body: LoginRequest,
    http_request: Request,
    response: Response,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Login a user.

    Validates credentials, creates a new session, sets cookies.
    The response body does NOT contain any token strings.

    CSRF: exempt (bootstrap endpoint).
    """
    result = login_user(
        email=body.email,
        password=body.password,
        session=db_session,
        settings=settings,
    )

    set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        csrf_token=result.csrf_token,
        settings=settings,
    )

    user_data = UserRead(
        id=result.user.id,
        email=result.user.email,
        display_name=result.user.display_name,
        global_role=result.user.global_role,
    )

    return success(
        data=user_data.model_dump(mode="json"),
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh(
    request: Request,
    response: Response,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Refresh access token (rotate refresh token).

    Reads refresh_token from Cookie. Requires CSRF validation.
    Implements replay detection: if the same refresh token is used twice,
    the entire token family is revoked.

    CSRF: required.
    """
    refresh_token_str = request.cookies.get("refresh_token")
    if not refresh_token_str:
        raise InvalidTokenError()

    result = refresh_token_rotation(
        refresh_token_str=refresh_token_str,
        session=db_session,
        settings=settings,
    )

    set_auth_cookies(
        response,
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        csrf_token=generate_csrf_token(),
        settings=settings,
    )

    response_data = RefreshResponse(
        id=result.user.id,
        email=result.user.email,
        display_name=result.user.display_name,
        global_role=result.user.global_role,
        session_version=result.session_version,
    )

    return success(
        data=response_data.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Logout: revoke session and clear cookies.

    Requires CSRF validation. Reads access_token from Cookie.
    Returns 204 No Content.

    CSRF: required.
    """
    access_token_str = request.cookies.get("access_token")
    if not access_token_str:
        raise InvalidTokenError()

    logout_user(
        access_token_str=access_token_str,
        session=db_session,
        settings=settings,
    )

    clear_auth_cookies(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@router.get("/me", status_code=status.HTTP_200_OK)
def me(
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get current authenticated user info.

    Reads access_token from Cookie. No CSRF required (GET request).

    Returns the current user's public fields.
    """
    user_data = UserRead(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        global_role=current_user.global_role,
    )

    return success(
        data=user_data.model_dump(mode="json"),
        request_id=getattr(http_request.state, "request_id", None),
    )
