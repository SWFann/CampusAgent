"""
User and StudentProfile ORM models for CampusAgent.

This module defines the core identity tables:
- ``User``: account-level entity (email, password_hash, role, status).
- ``StudentProfile``: student-specific profile (student_no, major, bio).

Design principles:
- UUID primary keys (UUID v4 via ``new_uuid``).
- All timestamps are timezone-aware UTC via ``utc_now()``.
- Enums are stored as strings for cross-database compatibility (SQLite tests + PostgreSQL prod).
- Email is normalised to lowercase at the service layer; the column has a unique constraint.
- ``deleted_at`` enables soft-delete without breaking foreign-key integrity.
- One-to-one relationship between User and StudentProfile.
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
# Enums (stored as strings in the database)
# ---------------------------------------------------------------------------


class GlobalRole(StrEnum):
    """Global roles assigned to a user across the entire platform."""

    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    COUNSELOR = "COUNSELOR"
    ORG_ADMIN = "ORG_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class UserStatus(StrEnum):
    """Account lifecycle status."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETED = "DELETED"


class ProfileVisibility(StrEnum):
    """Visibility level for a student profile."""

    PUBLIC = "PUBLIC"
    STUDENTS_ONLY = "STUDENTS_ONLY"
    PRIVATE = "PRIVATE"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class User(Base):
    """Core user account entity.

    Stores authentication credentials (``password_hash``), display
    information, and account status. Sensitive fields (``password_hash``)
    must never appear in API responses or logs.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    global_role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GlobalRole.STUDENT.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # One-to-one relationship with StudentProfile
    student_profile: Mapped[StudentProfile | None] = relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # One-to-many relationship with AuthSession (defined in auth module)
    auth_sessions: Mapped[list[AuthSession]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} status={self.status}>"


class StudentProfile(Base):
    """Student-specific profile linked to a User account.

    One-to-one with ``User``. Contains fields that are specific to
    students (student number, major, bio) and visibility controls.
    """

    __tablename__ = "student_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), unique=True, nullable=False
    )
    student_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    enrollment_year: Mapped[int | None] = mapped_column(nullable=True)
    major_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProfileVisibility.PUBLIC.value
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    # Back-reference to User
    user: Mapped[User] = relationship("User", back_populates="student_profile")

    def __repr__(self) -> str:
        return f"<StudentProfile id={self.id} student_no={self.student_no}>"
