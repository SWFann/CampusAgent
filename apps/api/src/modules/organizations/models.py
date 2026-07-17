"""
Organization and OrganizationMembership ORM models for CampusAgent.

This module defines the P4 organization tables:
- ``Organization``: school/college/department/class/dorm/club/course/team entity.
- ``OrganizationMembership``: user-to-organization membership with role and status.

Design principles:
- UUID primary keys (UUID v4 via ``new_uuid``).
- All timestamps are timezone-aware UTC via ``utc_now()``.
- Enums are stored as strings for cross-database compatibility.
- Self-referential parent/children relationship for org tree.
- ``(organization_id, user_id)`` unique constraint on memberships.
- ``__repr__`` does NOT leak sensitive user fields (email, password_hash).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid

# ---------------------------------------------------------------------------
# Enums (stored as strings in the database)
# ---------------------------------------------------------------------------


class OrganizationType(StrEnum):
    """Types of campus organizations."""

    SCHOOL = "SCHOOL"
    COLLEGE = "COLLEGE"
    DEPARTMENT = "DEPARTMENT"
    CLASS = "CLASS"
    DORM = "DORM"
    CLUB = "CLUB"
    COURSE = "COURSE"
    TEAM = "TEAM"
    OTHER = "OTHER"


class OrganizationVisibility(StrEnum):
    """Visibility level for an organization."""

    PUBLIC = "PUBLIC"
    MEMBERS_ONLY = "MEMBERS_ONLY"
    PRIVATE = "PRIVATE"


class OrganizationJoinPolicy(StrEnum):
    """How users can join an organization."""

    OPEN = "OPEN"
    APPROVAL = "APPROVAL"
    INVITE_ONLY = "INVITE_ONLY"
    CLOSED = "CLOSED"


class OrganizationStatus(StrEnum):
    """Lifecycle status of an organization."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class OrganizationRole(StrEnum):
    """Roles a user can hold within an organization."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    GUEST = "GUEST"


class MembershipStatus(StrEnum):
    """Lifecycle status of a membership."""

    INVITED = "INVITED"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    LEFT = "LEFT"
    REMOVED = "REMOVED"


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class Organization(Base):
    """Core organization entity.

    Represents a school, college, department, class, dorm, club, course,
    team, or other campus grouping. Supports a parent/children tree
    structure, visibility controls, join policies, and soft-delete.
    """

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    visibility: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationVisibility.PUBLIC.value
    )
    join_policy: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationJoinPolicy.INVITE_ONLY.value
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationStatus.ACTIVE.value
    )
    capacity: Mapped[int | None] = mapped_column(nullable=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Self-referential parent/children relationship
    parent: Mapped[Organization | None] = relationship(
        "Organization",
        remote_side="Organization.id",
        back_populates="children",
    )
    children: Mapped[list[Organization]] = relationship(
        "Organization",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Memberships
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Organization id={self.id} name={self.name} "
            f"type={self.type} status={self.status}>"
        )


class OrganizationMembership(Base):
    """Membership linking a user to an organization with a role and status.

    The ``(organization_id, user_id)`` pair is unique — a user has at most
    one membership row per organization. State transitions (INVITED →
    ACTIVE → LEFT/REMOVED) reuse the same row.
    """

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_org_user",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(
        String(40), nullable=False, default=OrganizationRole.MEMBER.value
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=MembershipStatus.ACTIVE.value
    )
    invited_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="memberships"
    )

    def __repr__(self) -> str:
        return (
            f"<OrganizationMembership id={self.id} "
            f"org_id={self.organization_id} user_id={self.user_id} "
            f"role={self.role} status={self.status}>"
        )
