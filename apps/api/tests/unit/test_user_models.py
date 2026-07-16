"""
Unit tests for User and StudentProfile ORM models (P3-01).

These tests verify:
- Creating User and StudentProfile succeeds.
- Email uniqueness constraint is enforced.
- Student number uniqueness constraint is enforced.
- Soft-delete field (``deleted_at``) exists.
- One-to-one relationship between User and StudentProfile.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from src.db.time import utc_now
from src.modules.users.models import (
    GlobalRole,
    ProfileVisibility,
    StudentProfile,
    User,
    UserStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(
    *,
    email: str = "student@example.edu",
    password_hash: str = "$2b$12$dummyhash",
    display_name: str = "张三",
    student_no: str = "20260001",
    session,
) -> User:
    """Create and add a User + StudentProfile to the session."""
    user = User(
        email=email,
        password_hash=password_hash,
        display_name=display_name,
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()  # get the id

    profile = StudentProfile(
        user_id=user.id,
        student_no=student_no,
        profile_visibility=ProfileVisibility.PUBLIC.value,
    )
    session.add(profile)
    session.flush()
    return user


# ---------------------------------------------------------------------------
# 1. User creation and defaults
# ---------------------------------------------------------------------------


class TestUserCreation:
    def test_create_user_success(self, test_db_session):
        """Creating a User with valid fields succeeds."""
        user = _make_user(session=test_db_session)
        test_db_session.commit()

        assert user.id is not None
        assert user.email == "student@example.edu"
        assert user.display_name == "张三"
        assert user.global_role == GlobalRole.STUDENT.value
        assert user.status == UserStatus.ACTIVE.value
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.deleted_at is None
        assert user.avatar_url is None

    def test_user_defaults(self, test_db_session):
        """Default values for global_role and status are correct."""
        user = User(
            email="defaults@example.edu",
            password_hash="hash",
            display_name="Default",
        )
        test_db_session.add(user)
        test_db_session.flush()

        assert user.global_role == GlobalRole.STUDENT.value
        assert user.status == UserStatus.ACTIVE.value

    def test_user_repr_does_not_leak_password(self, test_db_session):
        """__repr__ must not include password_hash."""
        user = User(
            email="repr@example.edu",
            password_hash="$2b$12$secret",
            display_name="Repr",
        )
        repr_str = repr(user)
        assert "password_hash" not in repr_str.lower()
        assert "$2b" not in repr_str


# ---------------------------------------------------------------------------
# 2. Email uniqueness
# ---------------------------------------------------------------------------


class TestEmailUniqueness:
    def test_duplicate_email_fails(self, test_db_session):
        """Two users with the same email must raise IntegrityError."""
        _make_user(email="dup@example.edu", session=test_db_session)
        test_db_session.flush()

        user2 = User(
            email="dup@example.edu",
            password_hash="hash2",
            display_name="Dup",
        )
        test_db_session.add(user2)
        with pytest.raises(IntegrityError):
            test_db_session.flush()


# ---------------------------------------------------------------------------
# 3. StudentProfile and student_no uniqueness
# ---------------------------------------------------------------------------


class TestStudentProfile:
    def test_create_student_profile_success(self, test_db_session):
        """Creating a StudentProfile linked to a User succeeds."""
        user = _make_user(session=test_db_session)
        test_db_session.flush()

        profile = user.student_profile
        assert profile is not None
        assert profile.student_no == "20260001"
        assert profile.profile_visibility == ProfileVisibility.PUBLIC.value
        assert profile.user_id == user.id

    def test_duplicate_student_no_fails(self, test_db_session):
        """Two profiles with the same student_no must raise IntegrityError."""
        _make_user(student_no="20260002", session=test_db_session)
        test_db_session.flush()

        user2 = User(
            email="second@example.edu",
            password_hash="hash",
            display_name="Second",
        )
        test_db_session.add(user2)
        test_db_session.flush()

        profile2 = StudentProfile(
            user_id=user2.id,
            student_no="20260002",  # same as first
        )
        test_db_session.add(profile2)
        with pytest.raises(IntegrityError):
            test_db_session.flush()

    def test_one_to_one_constraint(self, test_db_session):
        """A second StudentProfile for the same user must fail (unique FK)."""
        user = _make_user(session=test_db_session)
        test_db_session.flush()

        profile2 = StudentProfile(
            user_id=user.id,
            student_no="99999999",
        )
        test_db_session.add(profile2)
        with pytest.raises(IntegrityError):
            test_db_session.flush()


# ---------------------------------------------------------------------------
# 4. Soft-delete field
# ---------------------------------------------------------------------------


class TestSoftDelete:
    def test_deleted_at_field_exists(self, test_db_session):
        """The ``deleted_at`` field exists and is nullable."""
        user = _make_user(session=test_db_session)
        assert user.deleted_at is None

        now = utc_now()
        user.deleted_at = now
        test_db_session.flush()
        assert user.deleted_at == now

    def test_status_can_be_set_to_deleted(self, test_db_session):
        """User status can be set to DELETED."""
        user = _make_user(session=test_db_session)
        user.status = UserStatus.DELETED.value
        test_db_session.flush()
        assert user.status == UserStatus.DELETED.value
