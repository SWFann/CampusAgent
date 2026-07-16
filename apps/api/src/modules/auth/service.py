"""
Auth service for CampusAgent.

This module contains the business logic for:
- User registration (P3-03)
- User login (P3-04)
- Token refresh with replay detection (P3-05)
- Logout (P3-05)

The service receives a SQLAlchemy ``Session`` from the dependency injection
layer and is responsible for committing transactions and publishing events
after successful commit.
"""

from __future__ import annotations

import secrets
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import Settings
from ...db.time import utc_now
from ..users.models import GlobalRole, StudentProfile, User, UserStatus
from ..users.repository import StudentProfileRepository, UserRepository
from .cookies import generate_csrf_token
from .exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenExpiredError,
    RefreshTokenRevokedError,
    UserAlreadyExistsError,
)
from .models import AuthSession, RefreshToken, RefreshTokenStatus, SessionStatus
from .passwords import hash_password, validate_password_strength, verify_password
from .tokens import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_jti,
)


class RegistrationResult:
    """Result of a successful registration.

    Contains the created user and the tokens to set as cookies.
    The tokens are NOT included in the JSON response body — they are
    only used to set HttpOnly cookies.
    """

    def __init__(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        csrf_token: str,
    ) -> None:
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.csrf_token = csrf_token


def register_user(
    *,
    email: str,
    password: str,
    display_name: str,
    student_no: str,
    session: Session,
    settings: Settings,
) -> RegistrationResult:
    """Register a new user.

    Creates User + StudentProfile + AuthSession + RefreshToken, hashes the
    password, generates access/refresh/csrf tokens, and commits the
    transaction.

    Args:
        email: User email (will be normalised to lowercase).
        password: Plaintext password.
        display_name: Display name.
        student_no: Student number.
        session: SQLAlchemy session.
        settings: Application settings.

    Returns:
        A ``RegistrationResult`` with the user and tokens.

    Raises:
        WeakPasswordError: If the password fails strength validation.
        UserAlreadyExistsError: If email or student_no is already registered.
    """
    # Normalise email
    email_normalised = email.lower().strip()

    # Validate password strength
    validate_password_strength(
        password,
        email=email_normalised,
        student_no=student_no,
    )

    # Check uniqueness
    user_repo = UserRepository(session)
    if user_repo.email_exists(email_normalised):
        raise UserAlreadyExistsError(message="邮箱已被注册")

    profile_repo = StudentProfileRepository(session)
    if profile_repo.student_no_exists(student_no):
        raise UserAlreadyExistsError(message="学号已被注册")

    # Create User
    user = User(
        email=email_normalised,
        password_hash=hash_password(password),
        display_name=display_name,
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()  # get user.id

    # Create StudentProfile
    profile = StudentProfile(
        user_id=user.id,
        student_no=student_no,
    )
    session.add(profile)

    # Create AuthSession
    family_id = secrets.token_urlsafe(16)
    now = utc_now()
    auth_session = AuthSession(
        user_id=user.id,
        family_id=family_id,
        session_version=1,
        status=SessionStatus.ACTIVE.value,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(auth_session)
    session.flush()  # get session.id

    # Create refresh token
    refresh_token_str, jti, token_expires_at = create_refresh_token(
        user_id=user.id,
        family_id=family_id,
        session_id=auth_session.id,
        settings=settings,
    )

    refresh_token = RefreshToken(
        session_id=auth_session.id,
        user_id=user.id,
        family_id=family_id,
        jti_hash=hash_jti(jti),
        status=RefreshTokenStatus.ACTIVE.value,
        expires_at=token_expires_at,
    )
    session.add(refresh_token)

    # Commit transaction
    session.commit()
    session.refresh(user)
    session.refresh(auth_session)

    # Generate access token and CSRF token
    access_token_str, _ = create_access_token(
        user_id=user.id,
        role=user.global_role,
        settings=settings,
    )
    csrf_token = generate_csrf_token()

    # Publish UserRegistered domain event (P3-08)
    from ...events.bus import default_event_bus
    from ..users.events import create_user_registered_event

    event = create_user_registered_event(
        user_id=user.id,
        email=email_normalised,
        occurred_at=utc_now(),
    )
    default_event_bus.publish(event)

    return RegistrationResult(
        user=user,
        access_token=access_token_str,
        refresh_token=refresh_token_str,
        csrf_token=csrf_token,
    )


class LoginResult:
    """Result of a successful login."""

    def __init__(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        csrf_token: str,
    ) -> None:
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.csrf_token = csrf_token


def login_user(
    *,
    email: str,
    password: str,
    session: Session,
    settings: Settings,
) -> LoginResult:
    """Authenticate a user and create a new session.

    Args:
        email: User email.
        password: Plaintext password.
        session: SQLAlchemy session.
        settings: Application settings.

    Returns:
        A ``LoginResult`` with the user and tokens.

    Raises:
        InvalidCredentialsError: If credentials are invalid or account is disabled.
    """
    email_normalised = email.lower().strip()
    user_repo = UserRepository(session)
    user = user_repo.get_by_email(email_normalised)

    # Unified error: don't distinguish "user not found" from "wrong password"
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    # Check account status — still return AUTH_INVALID_CREDENTIALS
    # to avoid leaking account existence
    if user.status in (UserStatus.DISABLED.value, UserStatus.DELETED.value):
        raise InvalidCredentialsError()

    # Create new session
    family_id = secrets.token_urlsafe(16)
    now = utc_now()
    auth_session = AuthSession(
        user_id=user.id,
        family_id=family_id,
        session_version=1,
        status=SessionStatus.ACTIVE.value,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(auth_session)
    session.flush()

    # Create refresh token
    refresh_token_str, jti, token_expires_at = create_refresh_token(
        user_id=user.id,
        family_id=family_id,
        session_id=auth_session.id,
        settings=settings,
    )

    refresh_token = RefreshToken(
        session_id=auth_session.id,
        user_id=user.id,
        family_id=family_id,
        jti_hash=hash_jti(jti),
        status=RefreshTokenStatus.ACTIVE.value,
        expires_at=token_expires_at,
    )
    session.add(refresh_token)

    session.commit()
    session.refresh(user)

    # Generate access token and CSRF token
    access_token_str, _ = create_access_token(
        user_id=user.id,
        role=user.global_role,
        settings=settings,
    )
    csrf_token = generate_csrf_token()

    return LoginResult(
        user=user,
        access_token=access_token_str,
        refresh_token=refresh_token_str,
        csrf_token=csrf_token,
    )


class RefreshResult:
    """Result of a successful token refresh."""

    def __init__(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        session_version: int,
    ) -> None:
        self.user = user
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.session_version = session_version


def refresh_token_rotation(
    *,
    refresh_token_str: str,
    session: Session,
    settings: Settings,
) -> RefreshResult:
    """Rotate a refresh token: validate, mark old as USED, issue new.

    Implements replay detection: if the same refresh token is used twice,
    the entire token family is revoked.

    Args:
        refresh_token_str: The refresh token JWT string.
        session: SQLAlchemy session.
        settings: Application settings.

    Returns:
        A ``RefreshResult`` with the new tokens and session version.

    Raises:
        InvalidTokenError: If the token is missing or invalid.
        RefreshTokenExpiredError: If the token has expired.
        RefreshTokenRevokedError: If the token has been revoked or replayed.
    """
    # Decode and validate the token
    try:
        payload = decode_token(refresh_token_str, settings)
    except Exception:
        raise InvalidTokenError() from None

    # Verify token type
    if payload.get("typ") != TokenType.REFRESH.value:
        raise InvalidTokenError()

    jti = str(payload.get("jti", ""))
    family_id = str(payload.get("family_id", ""))
    session_id_str = str(payload.get("session_id", ""))
    user_id_str = str(payload.get("sub", ""))

    if not jti or not family_id or not session_id_str or not user_id_str:
        raise InvalidTokenError()

    # Look up the stored refresh token by jti_hash
    jti_hash = hash_jti(jti)
    stmt = select(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
    stored_token = session.execute(stmt).scalar_one_or_none()

    if stored_token is None:
        raise InvalidTokenError()

    # Check token status
    if stored_token.status == RefreshTokenStatus.USED.value:
        # REPLAY DETECTED — revoke entire family
        _revoke_family(session, family_id)
        session.commit()
        raise RefreshTokenRevokedError(message="检测到 Refresh Token 重放，已撤销整个会话")

    if stored_token.status == RefreshTokenStatus.REVOKED.value:
        raise RefreshTokenRevokedError()

    # Check expiry (SQLite may return naive datetimes — normalise to UTC)
    now = utc_now()
    stored_expiry = stored_token.expires_at
    if stored_expiry.tzinfo is None:
        from datetime import UTC

        stored_expiry = stored_expiry.replace(tzinfo=UTC)
    if stored_expiry < now:
        raise RefreshTokenExpiredError()

    # Mark old token as USED
    stored_token.status = RefreshTokenStatus.USED.value
    stored_token.used_at = now

    # Get the auth session
    session_uuid = UUID(session_id_str)
    auth_session = session.get(AuthSession, session_uuid)
    if auth_session is None or auth_session.status != SessionStatus.ACTIVE.value:
        raise RefreshTokenRevokedError()

    # Increment session version
    auth_session.session_version += 1

    # Get user
    user_uuid = UUID(user_id_str)
    user = UserRepository(session).get_by_id(user_uuid)
    if user is None or user.status in (UserStatus.DISABLED.value, UserStatus.DELETED.value):
        raise InvalidTokenError()

    # Create new refresh token
    new_refresh_token_str, new_jti, new_expires_at = create_refresh_token(
        user_id=user.id,
        family_id=family_id,
        session_id=auth_session.id,
        settings=settings,
    )

    new_token = RefreshToken(
        session_id=auth_session.id,
        user_id=user.id,
        family_id=family_id,
        jti_hash=hash_jti(new_jti),
        status=RefreshTokenStatus.ACTIVE.value,
        expires_at=new_expires_at,
    )
    session.add(new_token)

    session.commit()
    session.refresh(user)
    session.refresh(auth_session)

    # Generate new access token
    access_token_str, _ = create_access_token(
        user_id=user.id,
        role=user.global_role,
        settings=settings,
    )

    return RefreshResult(
        user=user,
        access_token=access_token_str,
        refresh_token=new_refresh_token_str,
        session_version=auth_session.session_version,
    )


def logout_user(
    *,
    access_token_str: str,
    session: Session,
    settings: Settings,
) -> None:
    """Logout: revoke the current session and token family.

    Args:
        access_token_str: The access token JWT string.
        session: SQLAlchemy session.
        settings: Application settings.

    Raises:
        InvalidTokenError: If the token is missing or invalid.
    """
    try:
        payload = decode_token(access_token_str, settings)
    except Exception:
        raise InvalidTokenError() from None

    if payload.get("typ") != TokenType.ACCESS.value:
        raise InvalidTokenError()

    user_id_str = str(payload.get("sub", ""))
    jti = str(payload.get("jti", ""))
    if not user_id_str or not jti:
        raise InvalidTokenError()

    user_uuid = UUID(user_id_str)
    user = UserRepository(session).get_by_id(user_uuid)
    if user is None:
        raise InvalidTokenError()

    # Revoke all active sessions for this user
    stmt = select(AuthSession).where(
        AuthSession.user_id == user_uuid,
        AuthSession.status == SessionStatus.ACTIVE.value,
    )
    active_sessions = session.execute(stmt).scalars().all()
    for s in active_sessions:
        s.status = SessionStatus.REVOKED.value
        s.revoked_at = utc_now()
        _revoke_family(session, s.family_id, mark_compromised=False)

    session.commit()


def _revoke_family(
    session: Session,
    family_id: str,
    *,
    mark_compromised: bool = True,
) -> None:
    """Revoke all refresh tokens in a family.

    Replay detection marks the session family as compromised. User-initiated
    logout and account deletion are normal revocations, not compromise events.
    """
    # Revoke all tokens in the family
    stmt = select(RefreshToken).where(RefreshToken.family_id == family_id)
    tokens = session.execute(stmt).scalars().all()
    for token in tokens:
        if token.status != RefreshTokenStatus.USED.value:
            token.status = RefreshTokenStatus.REVOKED.value
            token.revoked_at = utc_now()

    # Mark sessions as COMPROMISED for replay, or REVOKED for normal logout.
    session_stmt = select(AuthSession).where(AuthSession.family_id == family_id)
    sessions = session.execute(session_stmt).scalars().all()
    for s in sessions:
        s.status = (
            SessionStatus.COMPROMISED.value
            if mark_compromised
            else SessionStatus.REVOKED.value
        )
        s.revoked_at = utc_now()
