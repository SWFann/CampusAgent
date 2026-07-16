"""
Pydantic schemas for the users module.

These schemas define the API contract shapes for user-related responses.
- ``UserPublicRead``: safe public profile (no email, no student_no).
- ``UserSelfRead``: full self info (includes email, student profile).
- ``StudentProfileRead``: student profile subset.

All schemas use ``from_attributes=True`` so they can be constructed directly
from ORM model instances.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StudentProfileRead(BaseModel):
    """Student profile fields visible to the profile owner."""

    model_config = ConfigDict(from_attributes=True)

    student_no: str
    enrollment_year: int | None = None
    major_name: str | None = None
    bio: str | None = None
    profile_visibility: str = "PUBLIC"


class UserPublicRead(BaseModel):
    """Public user profile — safe to expose to any caller.

    Does NOT include email, student_no, password_hash, or session info.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    avatar_url: str | None = None
    profile_visibility: str = "PUBLIC"


class UserSelfRead(BaseModel):
    """Self user info — only visible to the authenticated user themselves.

    Includes email and student profile but never password_hash.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    global_role: str
    student_profile: StudentProfileRead | None = None


class UserProfileUpdate(BaseModel):
    """PATCH /api/v1/users/{user_id} request body.

    Only the profile owner may update these fields.
    Email, student_no, global_role, and status are NOT updatable here.
    """

    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    profile_visibility: str | None = None
