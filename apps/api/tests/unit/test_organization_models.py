"""
Unit tests for Organization and OrganizationMembership models (P4-01).

Tests verify:
- Creating an Organization succeeds with correct defaults.
- parent/children self-referential relationship works.
- Creating an OrganizationMembership succeeds with correct defaults.
- ``(organization_id, user_id)`` unique constraint is enforced.
- ``__repr__`` does not leak sensitive user fields.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationJoinPolicy,
    OrganizationMembership,
    OrganizationRole,
    OrganizationStatus,
    OrganizationType,
    OrganizationVisibility,
)

# ---------------------------------------------------------------------------
# Organization model tests
# ---------------------------------------------------------------------------


class TestOrganizationModel:
    def test_create_organization_success(self, test_db_session: Session) -> None:
        """Creating an Organization succeeds."""
        user_id = uuid4()
        org = Organization(
            name="测试组织",
            type=OrganizationType.CLUB.value,
            created_by=user_id,
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        assert org.id is not None
        assert org.name == "测试组织"
        assert org.type == OrganizationType.CLUB.value

    def test_organization_defaults(self, test_db_session: Session) -> None:
        """Default visibility/join_policy/status are correct."""
        org = Organization(
            name="默认组织",
            type=OrganizationType.DORM.value,
            created_by=uuid4(),
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        assert org.visibility == OrganizationVisibility.PUBLIC.value
        assert org.join_policy == OrganizationJoinPolicy.INVITE_ONLY.value
        assert org.status == OrganizationStatus.ACTIVE.value
        assert org.slug is None
        assert org.description is None
        assert org.capacity is None
        assert org.parent_id is None
        assert org.archived_at is None
        assert org.deleted_at is None
        assert org.created_at is not None
        assert org.updated_at is not None

    def test_parent_child_relationship(self, test_db_session: Session) -> None:
        """parent/children self-referential relationship works."""
        parent = Organization(
            name="父组织",
            type=OrganizationType.COLLEGE.value,
            created_by=uuid4(),
        )
        test_db_session.add(parent)
        test_db_session.commit()
        test_db_session.refresh(parent)

        child = Organization(
            name="子组织",
            type=OrganizationType.CLASS.value,
            parent_id=parent.id,
            created_by=uuid4(),
        )
        test_db_session.add(child)
        test_db_session.commit()
        test_db_session.refresh(child)
        test_db_session.refresh(parent)

        assert child.parent_id == parent.id
        assert child.parent is not None
        assert child.parent.name == "父组织"
        assert len(parent.children) == 1
        assert parent.children[0].name == "子组织"

    def test_organization_repr_does_not_leak_sensitive_fields(
        self, test_db_session: Session
    ) -> None:
        """__repr__ does not output email, password_hash, or member info."""
        org = Organization(
            name="安全测试",
            type=OrganizationType.TEAM.value,
            created_by=uuid4(),
        )
        repr_str = repr(org)
        assert "安全测试" in repr_str
        assert "email" not in repr_str.lower()
        assert "password" not in repr_str.lower()
        assert "member" not in repr_str.lower()


# ---------------------------------------------------------------------------
# OrganizationMembership model tests
# ---------------------------------------------------------------------------


class TestOrganizationMembershipModel:
    def test_create_membership_success(self, test_db_session: Session) -> None:
        """Creating an OrganizationMembership succeeds."""
        user_id = uuid4()
        org = Organization(
            name="成员测试组织",
            type=OrganizationType.COURSE.value,
            created_by=user_id,
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user_id,
        )
        test_db_session.add(membership)
        test_db_session.commit()
        test_db_session.refresh(membership)

        assert membership.id is not None
        assert membership.organization_id == org.id
        assert membership.user_id == user_id

    def test_membership_defaults(self, test_db_session: Session) -> None:
        """Default role/status are correct."""
        user_id = uuid4()
        org = Organization(
            name="默认成员组织",
            type=OrganizationType.DORM.value,
            created_by=uuid4(),
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user_id,
        )
        test_db_session.add(membership)
        test_db_session.commit()
        test_db_session.refresh(membership)

        assert membership.role == OrganizationRole.MEMBER.value
        assert membership.status == MembershipStatus.ACTIVE.value
        assert membership.invited_by is None
        assert membership.joined_at is None
        assert membership.left_at is None

    def test_unique_org_user_constraint(self, test_db_session: Session) -> None:
        """``(organization_id, user_id)`` unique constraint is enforced."""
        user_id = uuid4()
        org = Organization(
            name="唯一约束测试",
            type=OrganizationType.CLUB.value,
            created_by=uuid4(),
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        m1 = OrganizationMembership(organization_id=org.id, user_id=user_id)
        test_db_session.add(m1)
        test_db_session.commit()

        m2 = OrganizationMembership(organization_id=org.id, user_id=user_id)
        test_db_session.add(m2)
        with pytest.raises(IntegrityError):
            test_db_session.commit()
        test_db_session.rollback()

    def test_membership_repr_does_not_leak_sensitive_fields(
        self, test_db_session: Session
    ) -> None:
        """__repr__ does not output email, password_hash."""
        user_id = uuid4()
        org = Organization(
            name="repr安全测试",
            type=OrganizationType.TEAM.value,
            created_by=uuid4(),
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user_id,
        )
        repr_str = repr(membership)
        assert "email" not in repr_str.lower()
        assert "password" not in repr_str.lower()

    def test_membership_organization_relationship(
        self, test_db_session: Session
    ) -> None:
        """Membership.organization back-reference works."""
        user_id = uuid4()
        org = Organization(
            name="关系测试",
            type=OrganizationType.CLASS.value,
            created_by=uuid4(),
        )
        test_db_session.add(org)
        test_db_session.commit()
        test_db_session.refresh(org)

        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user_id,
        )
        test_db_session.add(membership)
        test_db_session.commit()
        test_db_session.refresh(membership)
        test_db_session.refresh(org)

        assert membership.organization is not None
        assert membership.organization.id == org.id
        assert len(org.memberships) == 1
        assert org.memberships[0].user_id == user_id
