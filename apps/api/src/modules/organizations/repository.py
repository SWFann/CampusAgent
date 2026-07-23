"""
Repository for Organization and OrganizationMembership entities.

Provides query helpers for common lookups. The repository only does
queries and basic persistence — no permission decisions.

Permission, last-OWNER protection, and join-policy logic are handled
in the service / permissions layers.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...db.repositories import BaseRepository
from .models import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for the ``Organization`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, Organization)

    def get_by_id(self, id_: UUID) -> Organization | None:
        """Get an organization by primary key (including soft-deleted)."""
        return self._session.get(Organization, id_)

    def get_active_by_id(self, id_: UUID) -> Organization | None:
        """Get an organization by ID, excluding soft-deleted.

        Archived organizations are still returned (they are visible
        to members with appropriate permissions).
        """
        org = self._session.get(Organization, id_)
        if org is None or org.status == OrganizationStatus.DELETED.value:
            return None
        return org

    def list_active(
        self,
        *,
        org_type: str | None = None,
        parent_id: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Organization]:
        """List active (non-deleted) organizations with optional filters."""
        stmt = select(Organization).where(
            Organization.status != OrganizationStatus.DELETED.value
        )
        if org_type is not None:
            stmt = stmt.where(Organization.type == org_type)
        if parent_id is not None:
            stmt = stmt.where(Organization.parent_id == parent_id)
        stmt = stmt.order_by(Organization.created_at.desc()).limit(limit).offset(offset)
        return list(self._session.execute(stmt).scalars().all())

    def get_children(self, parent_id: UUID) -> list[Organization]:
        """Get active children of a parent organization."""
        stmt = select(Organization).where(
            Organization.parent_id == parent_id,
            Organization.status != OrganizationStatus.DELETED.value,
        )
        return list(self._session.execute(stmt).scalars().all())

    def slug_exists(self, slug: str, exclude_id: UUID | None = None) -> bool:
        """Check if a slug is already used by a non-deleted organization."""
        stmt = select(Organization).where(
            Organization.slug == slug,
            Organization.status != OrganizationStatus.DELETED.value,
        )
        if exclude_id is not None:
            stmt = stmt.where(Organization.id != exclude_id)
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def count_active_members(self, organization_id: UUID) -> int:
        """Count active memberships for an organization."""
        stmt = select(func.count()).select_from(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE.value,
        )
        result = self._session.execute(stmt).scalar()
        return int(result or 0)

    def search(
        self,
        query: str,
        *,
        org_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Organization]:
        """Search organizations by name or slug (ILIKE)."""
        pattern = f"%{query}%"
        stmt = select(Organization).where(
            Organization.status != OrganizationStatus.DELETED.value,
            Organization.status != OrganizationStatus.ARCHIVED.value,
        )
        stmt = stmt.where(
            (Organization.name.ilike(pattern))
            | (Organization.slug.ilike(pattern))
        )
        if org_type is not None:
            stmt = stmt.where(Organization.type == org_type)
        stmt = stmt.order_by(Organization.name.asc()).limit(limit).offset(offset)
        return list(self._session.execute(stmt).scalars().all())


class OrganizationMembershipRepository(BaseRepository[OrganizationMembership]):
    """Repository for the ``OrganizationMembership`` ORM model."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, OrganizationMembership)

    def get_by_org_user(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        """Get any membership row for a (org, user) pair, regardless of status."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_active_by_org_user(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        """Get an ACTIVE membership for a (org, user) pair."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE.value,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_active_by_org(self, organization_id: UUID) -> list[OrganizationMembership]:
        """List all ACTIVE memberships for an organization."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE.value,
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_by_org_status(
        self, organization_id: UUID, status: str
    ) -> list[OrganizationMembership]:
        """List memberships in an organization for one lifecycle status."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == status,
        )
        return list(self._session.execute(stmt).scalars().all())

    def list_active_by_user(self, user_id: UUID) -> list[OrganizationMembership]:
        """List all ACTIVE memberships for a user."""
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE.value,
        )
        return list(self._session.execute(stmt).scalars().all())

    def count_active_owners(self, organization_id: UUID) -> int:
        """Count active OWNER memberships for an organization."""
        from .models import OrganizationRole

        stmt = select(func.count()).select_from(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == OrganizationRole.OWNER.value,
            OrganizationMembership.status == MembershipStatus.ACTIVE.value,
        )
        result = self._session.execute(stmt).scalar()
        return int(result or 0)

    def count_active_members(self, organization_id: UUID) -> int:
        """Count active memberships for an organization."""
        stmt = select(func.count()).select_from(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.status == MembershipStatus.ACTIVE.value,
        )
        result = self._session.execute(stmt).scalar()
        return int(result or 0)

    def has_active_membership(
        self, organization_id: UUID, user_id: UUID
    ) -> bool:
        """Check if a user has an ACTIVE membership in an organization."""
        return self.get_active_by_org_user(organization_id, user_id) is not None
