"""
Pydantic schemas for the organizations module.

Design principles:
- Input schemas use frozen-contract field names.
- Output schemas do NOT include email, student_no, password_hash, token, or session info.
- Member user fields only return id, display_name, avatar_url, global_role (optional).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Organization schemas
# ---------------------------------------------------------------------------


class OrganizationCreateRequest(BaseModel):
    """POST /api/v1/organizations request body."""

    name: str = Field(..., min_length=1, max_length=120)
    type: str = Field(..., max_length=40)
    slug: str | None = Field(default=None, max_length=160)
    parent_id: UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    visibility: str = Field(default="PUBLIC", max_length=40)
    join_policy: str = Field(default="INVITE_ONLY", max_length=40)
    capacity: int | None = Field(default=None, ge=1)


class OrganizationUpdateRequest(BaseModel):
    """PATCH /api/v1/organizations/{id} request body.

    Only name, description, visibility, join_policy, and capacity are
    updatable. id, type, created_by, status are NOT updatable here.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    visibility: str | None = Field(default=None, max_length=40)
    join_policy: str | None = Field(default=None, max_length=40)
    capacity: int | None = Field(default=None, ge=1)


class OrganizationRead(BaseModel):
    """Safe organization output — no member or sensitive user data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str | None = None
    type: str
    parent_id: UUID | None = None
    description: str | None = None
    visibility: str
    join_policy: str
    status: str
    capacity: int | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class OrganizationListItem(BaseModel):
    """Organization list item — minimal safe projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    visibility: str
    status: str
    member_count: int = 0


class OrganizationListResponse(BaseModel):
    """Response for GET /api/v1/organizations."""

    organizations: list[OrganizationListItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Membership schemas
# ---------------------------------------------------------------------------


class OrganizationMemberAddRequest(BaseModel):
    """POST /api/v1/organizations/{id}/members request body."""

    user_id: UUID
    role: str = Field(default="MEMBER", max_length=40)


class OrganizationMemberUpdateRequest(BaseModel):
    """PATCH /api/v1/organizations/{id}/members/{user_id} request body."""

    role: str = Field(..., max_length=40)


class OrganizationMemberRead(BaseModel):
    """Safe member output — no email, student_no, password_hash.

    Only returns id, display_name, avatar_url, and role/status info.
    """

    user_id: UUID
    display_name: str
    avatar_url: str | None = None
    global_role: str | None = None
    role: str
    status: str
    joined_at: datetime | None = None
    created_at: datetime


class OrganizationMembersResponse(BaseModel):
    """Response for GET /api/v1/organizations/{id}/members."""

    members: list[OrganizationMemberRead]
    total: int


class OrganizationJoinResponse(BaseModel):
    """Response for POST /api/v1/organizations/{id}/join."""

    organization_id: UUID
    user_id: UUID
    role: str
    status: str
