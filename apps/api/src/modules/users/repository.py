"""
Repository for User and StudentProfile entities.

Provides query helpers for common lookups:
- ``get_by_email``: find a user by normalised email.
- ``get_by_student_no``: find a student profile by student number.
- ``email_exists`` / ``student_no_exists``: existence checks for registration.

The repository is session-scoped — it receives a ``Session`` from the caller.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db.repositories import BaseRepository
from .models import StudentProfile, User


class UserRepository(BaseRepository[User]):
    """Repository for the ``User`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, User)

    def get_by_id(self, id_: Any) -> User | None:
        """Get a user by primary key, excluding soft-deleted users."""
        user = self._session.get(User, id_)
        if user is not None and user.deleted_at is not None:
            return None
        return user

    def get_by_email(self, email: str) -> User | None:
        """Find a user by email (case-insensitive, normalised to lowercase)."""
        stmt = select(User).where(User.email == email.lower())
        return self._session.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        """Check if a normalised email is already registered."""
        return self.get_by_email(email) is not None


class StudentProfileRepository(BaseRepository[StudentProfile]):
    """Repository for the ``StudentProfile`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, StudentProfile)

    def get_by_student_no(self, student_no: str) -> StudentProfile | None:
        """Find a student profile by student number."""
        stmt = select(StudentProfile).where(StudentProfile.student_no == student_no)
        return self._session.execute(stmt).scalar_one_or_none()

    def student_no_exists(self, student_no: str) -> bool:
        """Check if a student number is already registered."""
        return self.get_by_student_no(student_no) is not None

    def phone_number_exists(self, phone_number: str) -> bool:
        """Check whether a phone number is already bound to a student."""
        stmt = select(StudentProfile.id).where(
            StudentProfile.phone_number == phone_number
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None
