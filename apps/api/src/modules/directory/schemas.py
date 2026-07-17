"""
Pydantic schemas for the directory module.

Design principles:
- User search results do NOT include email, student_no, password_hash, or bio.
- Organization results are filtered by visibility and permissions.
- Tree nodes only return safe organization projections.
- Recommended results include a reason field for explainability.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DirectorySearchType(StrEnum):
    """Type of directory search."""

    ALL = "all"
    USERS = "users"
    ORGANIZATIONS = "organizations"


class DirectoryUserResult(BaseModel):
    """Safe user search result — no email, student_no, password_hash, or bio."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    avatar_url: str | None = None
    profile_visibility: str = "PUBLIC"


class DirectoryOrganizationResult(BaseModel):
    """Safe organization search result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    visibility: str
    status: str
    member_count: int = 0


class DirectorySearchResponse(BaseModel):
    """Response for GET /api/v1/directory/search."""

    users: list[DirectoryUserResult] = []
    organizations: list[DirectoryOrganizationResult] = []
    total: int
    query: str
    search_type: str


class DirectoryTreeNode(BaseModel):
    """A node in the organization tree."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    visibility: str
    status: str
    parent_id: UUID | None = None
    children: list[DirectoryTreeNode] = []


class DirectoryTreeResponse(BaseModel):
    """Response for GET /api/v1/directory/tree."""

    nodes: list[DirectoryTreeNode]
    max_depth: int


class DirectoryRecommendedItem(BaseModel):
    """A recommended organization."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    visibility: str
    reason: str


class DirectoryRecommendedResponse(BaseModel):
    """Response for GET /api/v1/directory/recommended."""

    recommendations: list[DirectoryRecommendedItem]
    total: int
