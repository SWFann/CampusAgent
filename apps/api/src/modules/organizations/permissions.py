"""
Centralized permission service for organization actions.

This module implements the RBAC policy for organizations:
- Global roles: SYSTEM_ADMIN, SCHOOL_ADMIN, ORG_ADMIN
- Organization roles: OWNER, ADMIN, MEMBER, GUEST

Rules:
- SYSTEM_ADMIN can manage all organizations.
- SCHOOL_ADMIN can manage all organizations (P4 MVP; to be narrowed by school scope).
- ORG_ADMIN does NOT automatically equal any org OWNER.
- OWNER can do everything in their org.
- ADMIN can manage MEMBER/GUEST but not OWNER.
- MEMBER can view and leave.
- GUEST can view minimal info and leave.
- Non-members can only view PUBLIC orgs.
"""

from __future__ import annotations

from ..users.models import GlobalRole, User
from .models import (
    MembershipStatus,
    Organization,
    OrganizationMembership,
    OrganizationRole,
    OrganizationVisibility,
)


class OrganizationPermissionService:
    """Centralized permission checker for organization actions."""

    def _is_system_admin(self, actor: User) -> bool:
        return actor.global_role == GlobalRole.SYSTEM_ADMIN.value

    def _is_school_admin(self, actor: User) -> bool:
        return actor.global_role == GlobalRole.SCHOOL_ADMIN.value

    def _is_admin_level(self, actor: User) -> bool:
        """Check if the actor has a global admin role (SYSTEM_ADMIN or SCHOOL_ADMIN)."""
        return self._is_system_admin(actor) or self._is_school_admin(actor)

    def _get_role(self, membership: OrganizationMembership | None) -> str | None:
        """Extract the role from a membership, or None if no active membership."""
        if membership is None:
            return None
        if membership.status != MembershipStatus.ACTIVE.value:
            return None
        return membership.role

    # ------------------------------------------------------------------
    # View permissions
    # ------------------------------------------------------------------

    def can_view_organization(
        self,
        actor: User | None,
        organization: Organization,
        membership: OrganizationMembership | None,
    ) -> bool:
        """Check if the actor can view the organization details."""
        # System/School admins can view everything
        if actor is not None and self._is_admin_level(actor):
            return True

        # Active members can always view their org
        if self._get_role(membership) is not None:
            return True

        # Non-members: only PUBLIC orgs
        return organization.visibility == OrganizationVisibility.PUBLIC.value

    def can_view_members(
        self,
        actor: User,
        organization: Organization,
        membership: OrganizationMembership | None,
    ) -> bool:
        """Check if the actor can view the organization's member list."""
        # System/School admins can view members
        if self._is_admin_level(actor):
            return True

        role = self._get_role(membership)

        # OWNER, ADMIN, MEMBER can view members
        if role in (
            OrganizationRole.OWNER.value,
            OrganizationRole.ADMIN.value,
            OrganizationRole.MEMBER.value,
        ):
            return True

        # GUEST can view members only for PUBLIC orgs (limited)
        if role == OrganizationRole.GUEST.value:
            return organization.visibility == OrganizationVisibility.PUBLIC.value

        # Non-members cannot view member lists
        return False

    # ------------------------------------------------------------------
    # Management permissions
    # ------------------------------------------------------------------

    def can_update_organization(
        self, actor: User, membership: OrganizationMembership | None
    ) -> bool:
        """Check if the actor can update the organization."""
        if self._is_admin_level(actor):
            return True

        role = self._get_role(membership)
        return role in (OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value)

    def can_delete_organization(
        self, actor: User, membership: OrganizationMembership | None
    ) -> bool:
        """Check if the actor can delete the organization."""
        if self._is_system_admin(actor):
            return True

        role = self._get_role(membership)
        return role == OrganizationRole.OWNER.value

    def can_add_member(
        self,
        actor: User,
        actor_membership: OrganizationMembership | None,
        target_role: str,
    ) -> bool:
        """Check if the actor can add a member with the given target role."""
        if self._is_admin_level(actor):
            return True

        role = self._get_role(actor_membership)

        if role == OrganizationRole.OWNER.value:
            # OWNER can add any role
            return True

        if role == OrganizationRole.ADMIN.value:
            # ADMIN can only add MEMBER/GUEST
            return target_role in (
                OrganizationRole.MEMBER.value,
                OrganizationRole.GUEST.value,
            )

        return False

    def can_remove_member(
        self,
        actor: User,
        actor_membership: OrganizationMembership | None,
        target_membership: OrganizationMembership,
    ) -> bool:
        """Check if the actor can remove the target member."""
        if self._is_admin_level(actor):
            return True

        role = self._get_role(actor_membership)
        target_role = self._get_role(target_membership)

        if role == OrganizationRole.OWNER.value:
            # OWNER can remove anyone (subject to last-owner protection in service)
            return True

        if role == OrganizationRole.ADMIN.value:
            # ADMIN can only remove MEMBER/GUEST
            return target_role in (
                OrganizationRole.MEMBER.value,
                OrganizationRole.GUEST.value,
            )

        return False

    def can_change_member_role(
        self,
        actor: User,
        actor_membership: OrganizationMembership | None,
        target_membership: OrganizationMembership,
        new_role: str,
    ) -> bool:
        """Check if the actor can change the target member's role."""
        if self._is_admin_level(actor):
            return True

        role = self._get_role(actor_membership)
        target_role = self._get_role(target_membership)

        if role == OrganizationRole.OWNER.value:
            # OWNER can change anyone's role (subject to last-owner protection)
            return True

        if role == OrganizationRole.ADMIN.value:
            # ADMIN can only change MEMBER/GUEST roles
            # ADMIN cannot promote anyone to OWNER
            if new_role == OrganizationRole.OWNER.value:
                return False
            return target_role in (
                OrganizationRole.MEMBER.value,
                OrganizationRole.GUEST.value,
            )

        return False

    def can_transfer_ownership(
        self,
        actor: User,
        actor_membership: OrganizationMembership | None,
    ) -> bool:
        """Check if the actor can transfer ownership (promote to OWNER)."""
        if self._is_system_admin(actor):
            return True

        role = self._get_role(actor_membership)
        return role == OrganizationRole.OWNER.value


# Singleton instance for reuse
permission_service = OrganizationPermissionService()
