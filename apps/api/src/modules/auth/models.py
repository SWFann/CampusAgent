"""
AuthSession and RefreshToken ORM models for CampusAgent.

This module defines the session-security tables:
- ``AuthSession``: a login session with a token family for replay detection.
- ``RefreshToken``: individual refresh tokens within a session family.

Design principles:
- ``jti_hash`` is stored (SHA-256 of the JWT ``jti`` claim), never the raw token.
- ``family_id`` groups tokens from the same login chain for revocation on replay.
- ``session_version`` increments on each successful refresh for front-end detection.
- All timestamps are timezone-aware UTC.
- Status fields use string enums for cross-database compatibility.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SessionStatus(StrEnum):
    """Lifecycle status of an auth session."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    COMPROMISED = "COMPROMISED"


class RefreshTokenStatus(StrEnum):
    """Lifecycle status of an individual refresh token."""

    ACTIVE = "ACTIVE"
    USED = "USED"
    REVOKED = "REVOKED"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class AuthSession(Base):
    """Represents a user login session and its token family.

    A new ``AuthSession`` is created on each successful login or registration.
    All refresh tokens issued within this session share the same ``family_id``.
    If a replay is detected, the entire family is revoked.
    """

    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_version: Mapped[int] = mapped_column(default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SessionStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    user: Mapped[User] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", back_populates="auth_sessions"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AuthSession id={self.id} user_id={self.user_id} "
            f"family_id={self.family_id} status={self.status}>"
        )


class RefreshToken(Base):
    """An individual refresh token within an ``AuthSession`` family.

    Only the ``jti_hash`` (SHA-256 of the JWT ``jti`` claim) is stored —
    never the raw token string. This allows server-side revocation and
    replay detection without exposing token values.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("auth_sessions.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    jti_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RefreshTokenStatus.ACTIVE.value
    )
    issued_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    session: Mapped[AuthSession] = relationship(
        "AuthSession", back_populates="refresh_tokens"
    )

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} jti_hash=[REDACTED] status={self.status}>"
