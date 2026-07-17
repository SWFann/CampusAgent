"""
Service layer for the organizations module.

Business logic for:
- Organization CRUD (create, list, get, update, soft-delete)
- Membership lifecycle (add, list, update role, remove, join, leave)
- Permission enforcement via OrganizationPermissionService
- Last OWNER protection
- Join policy enforcement (OPEN/APPROVAL/INVITE_ONLY/CLOSED)
- Capacity enforcement
- Domain event publishing after successful commits

Privacy principles:
- Never return email, student_no, password_hash, token, or session info.
- Member lists only return safe user fields.
- Events only contain IDs, roles, and status.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...db.time import utc_now
from ...events.bus import default_event_bus
from ..users.models import User, UserStatus
from ..users.repository import UserRepository
from .events import (
    OrganizationArchived,
    OrganizationCreated,
    OrganizationMemberJoined,
    OrganizationMemberLeft,
    OrganizationMemberRoleChanged,
)
from .exceptions import (
    OrganizationCapacityExceededError,
    OrganizationInvalidJoinPolicyError,
    OrganizationLastOwnerError,
    OrganizationMemberAlreadyExistsError,
    OrganizationNotFoundError,
    OrganizationPermissionDeniedError,
)
from .models import (
    MembershipStatus,
    Organization,
    OrganizationJoinPolicy,
    OrganizationMembership,
    OrganizationRole,
    OrganizationStatus,
    OrganizationType,
    OrganizationVisibility,
)
from .permissions import permission_service
from .repository import OrganizationMembershipRepository, OrganizationRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_event_id() -> str:
    """Generate a unique event ID."""
    return secrets.token_hex(16)


def _validate_org_type(org_type: str) -> None:
    """Validate that the organization type is a known enum value."""
    valid_types = {t.value for t in OrganizationType}
    if org_type not in valid_types:
        raise OrganizationInvalidJoinPolicyError(
            message=f"无效的组织类型: {org_type}",
            details={"field": "type", "value": org_type},
        )


def _validate_visibility(visibility: str) -> None:
    """Validate visibility value."""
    valid = {v.value for v in OrganizationVisibility}
    if visibility not in valid:
        raise OrganizationInvalidJoinPolicyError(
            message=f"无效的可见性: {visibility}",
            details={"field": "visibility", "value": visibility},
        )


def _validate_join_policy(join_policy: str) -> None:
    """Validate join policy value."""
    valid = {p.value for p in OrganizationJoinPolicy}
    if join_policy not in valid:
        raise OrganizationInvalidJoinPolicyError(
            message=f"无效的加入策略: {join_policy}",
            details={"field": "join_policy", "value": join_policy},
        )


def _validate_role(role: str) -> None:
    """Validate role value."""
    valid = {r.value for r in OrganizationRole}
    if role not in valid:
        raise OrganizationInvalidJoinPolicyError(
            message=f"无效的角色: {role}",
            details={"field": "role", "value": role},
        )


def _check_capacity(session: Session, org: Organization) -> None:
    """Raise if the organization is at capacity."""
    if org.capacity is None:
        return
    repo = OrganizationMembershipRepository(session)
    current = repo.count_active_members(org.id)
    if current >= org.capacity:
        raise OrganizationCapacityExceededError(
            details={"capacity": org.capacity, "current": current}
        )


def _get_user_by_id(session: Session, user_id: UUID) -> User:
    """Get a user by ID, raising NotFoundError if not found or deleted."""
    from ...utils.errors import NotFoundError

    user = UserRepository(session).get_by_id(user_id)
    if user is None or user.status == UserStatus.DELETED.value:
        raise NotFoundError("用户")
    return user


def _org_to_read(org: Organization) -> dict[str, Any]:
    """Convert an Organization to a safe read dict."""
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "type": org.type,
        "parent_id": str(org.parent_id) if org.parent_id else None,
        "description": org.description,
        "visibility": org.visibility,
        "join_policy": org.join_policy,
        "status": org.status,
        "capacity": org.capacity,
        "created_by": str(org.created_by),
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "updated_at": org.updated_at.isoformat() if org.updated_at else None,
    }


def _membership_to_read(
    membership: OrganizationMembership, user: User
) -> dict[str, Any]:
    """Convert a membership + user to a safe member read dict.

    Returns only: user_id, display_name, avatar_url, global_role, role,
    status, joined_at, created_at. NEVER email, student_no, password_hash.
    """
    return {
        "user_id": str(membership.user_id),
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "global_role": user.global_role,
        "role": membership.role,
        "status": membership.status,
        "joined_at": membership.joined_at.isoformat()
        if membership.joined_at
        else None,
        "created_at": membership.created_at.isoformat()
        if membership.created_at
        else None,
    }


# ---------------------------------------------------------------------------
# Organization CRUD
# ---------------------------------------------------------------------------


def create_organization(
    actor: User,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Create a new organization.

    The creator automatically becomes the OWNER with an ACTIVE membership.

    Raises:
        OrganizationInvalidJoinPolicyError: If type/visibility/join_policy invalid.
        OrganizationNotFoundError: If parent_id points to a non-existent org.
    """
    _validate_org_type(data["type"])
    _validate_visibility(data.get("visibility", OrganizationVisibility.PUBLIC.value))
    _validate_join_policy(
        data.get("join_policy", OrganizationJoinPolicy.INVITE_ONLY.value)
    )

    # Validate parent if provided
    parent_id = data.get("parent_id")
    if parent_id is not None:
        parent = OrganizationRepository(session).get_active_by_id(UUID(str(parent_id)))
        if parent is None:
            raise OrganizationNotFoundError(message="父组织不存在")

    # Check slug uniqueness
    slug = data.get("slug")
    if slug and OrganizationRepository(session).slug_exists(slug):
        from ...utils.errors import AppError

        raise AppError(
            code="ORG_SLUG_ALREADY_EXISTS",
            message="组织 slug 已被使用",
            status_code=409,
        )

    org = Organization(
        name=data["name"],
        type=data["type"],
        slug=slug,
        parent_id=UUID(str(parent_id)) if parent_id else None,
        description=data.get("description"),
        visibility=data.get("visibility", OrganizationVisibility.PUBLIC.value),
        join_policy=data.get(
            "join_policy", OrganizationJoinPolicy.INVITE_ONLY.value
        ),
        capacity=data.get("capacity"),
        created_by=actor.id,
    )
    session.add(org)
    session.flush()  # Get org.id

    # Creator becomes OWNER
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=actor.id,
        role=OrganizationRole.OWNER.value,
        status=MembershipStatus.ACTIVE.value,
        invited_by=actor.id,
        joined_at=utc_now(),
    )
    session.add(membership)
    session.commit()
    session.refresh(org)
    session.refresh(membership)

    # Publish event after commit
    default_event_bus.publish(
        OrganizationCreated(
            event_id=_generate_event_id(),
            organization_id=org.id,
            actor_id=actor.id,
            organization_type=org.type,
            occurred_at=utc_now(),
        )
    )

    return _org_to_read(org)


def list_organizations(
    actor: User | None,
    *,
    org_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: Session,
) -> dict[str, Any]:
    """List organizations visible to the actor.

    Non-members can only see PUBLIC orgs. Members can see their orgs
    plus PUBLIC orgs. System/School admins can see everything.
    """
    repo = OrganizationRepository(session)
    offset = (page - 1) * page_size
    orgs = repo.list_active(
        org_type=org_type, limit=page_size, offset=offset
    )

    # Filter by visibility
    visible_orgs: list[Organization] = []
    for org in orgs:
        if permission_service.can_view_organization(
            actor, org, _get_membership(session, org.id, actor) if actor else None
        ):
            visible_orgs.append(org)

    items = []
    for org in visible_orgs:
        member_count = repo.count_active_members(org.id)
        items.append(
            {
                "id": str(org.id),
                "name": org.name,
                "type": org.type,
                "visibility": org.visibility,
                "status": org.status,
                "member_count": member_count,
            }
        )

    return {
        "organizations": items,
        "total": len(items),
        "page": page,
        "page_size": page_size,
    }


def get_organization(
    actor: User | None,
    organization_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Get a single organization by ID.

    Raises:
        OrganizationNotFoundError: If org not found or deleted.
        OrganizationPermissionDeniedError: If actor cannot view the org.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    membership = _get_membership(session, org.id, actor) if actor else None
    if not permission_service.can_view_organization(actor, org, membership):
        raise OrganizationPermissionDeniedError(message="无权查看此组织")

    return _org_to_read(org)


def update_organization(
    actor: User,
    organization_id: UUID,
    data: dict[str, Any],
    session: Session,
) -> dict[str, Any]:
    """Update an organization.

    Only OWNER, ADMIN, SYSTEM_ADMIN, SCHOOL_ADMIN can update.
    Updatable: name, description, visibility, join_policy, capacity.
    NOT updatable: id, type, created_by, status.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor lacks permission.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    membership = _get_membership(session, org.id, actor)
    if not permission_service.can_update_organization(actor, membership):
        raise OrganizationPermissionDeniedError(message="无权修改此组织")

    # Validate and apply updates
    if "name" in data and data["name"] is not None:
        org.name = data["name"]
    if "description" in data:
        org.description = data["description"]
    if "visibility" in data and data["visibility"] is not None:
        _validate_visibility(data["visibility"])
        org.visibility = data["visibility"]
    if "join_policy" in data and data["join_policy"] is not None:
        _validate_join_policy(data["join_policy"])
        org.join_policy = data["join_policy"]
    if "capacity" in data and data["capacity"] is not None:
        if data["capacity"] < 1:
            raise OrganizationInvalidJoinPolicyError(
                message="容量必须大于等于 1"
            )
        org.capacity = data["capacity"]

    session.commit()
    session.refresh(org)
    return _org_to_read(org)


def delete_organization(
    actor: User,
    organization_id: UUID,
    session: Session,
) -> None:
    """Soft-delete an organization (status=DELETED, deleted_at set).

    Only OWNER or SYSTEM_ADMIN can delete.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor lacks permission.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    membership = _get_membership(session, org.id, actor)
    if not permission_service.can_delete_organization(actor, membership):
        raise OrganizationPermissionDeniedError(message="无权删除此组织")

    org.status = OrganizationStatus.DELETED.value
    org.deleted_at = utc_now()
    session.commit()

    # Publish event after commit
    default_event_bus.publish(
        OrganizationArchived(
            event_id=_generate_event_id(),
            organization_id=org.id,
            actor_id=actor.id,
            action="deleted",
            occurred_at=utc_now(),
        )
    )


# ---------------------------------------------------------------------------
# Membership lifecycle
# ---------------------------------------------------------------------------


def add_member(
    actor: User,
    organization_id: UUID,
    target_user_id: UUID,
    target_role: str,
    session: Session,
) -> dict[str, Any]:
    """Add a member to an organization.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor lacks permission.
        OrganizationMemberAlreadyExistsError: If user is already a member.
        OrganizationCapacityExceededError: If org is at capacity.
    """
    _validate_role(target_role)

    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    actor_membership = _get_membership(session, org.id, actor)
    if not permission_service.can_add_member(actor, actor_membership, target_role):
        raise OrganizationPermissionDeniedError(message="无权添加成员")

    # ADMIN cannot add OWNER
    if target_role == OrganizationRole.OWNER.value and not permission_service.can_transfer_ownership(
        actor, actor_membership
    ):
        raise OrganizationPermissionDeniedError(
            message="无权添加 OWNER，只有 OWNER 或 SYSTEM_ADMIN 可以转让所有权"
        )

    target_user = _get_user_by_id(session, target_user_id)

    # Check capacity
    _check_capacity(session, org)

    mem_repo = OrganizationMembershipRepository(session)
    existing = mem_repo.get_by_org_user(org.id, target_user_id)

    if existing is not None:
        if existing.status in (
            MembershipStatus.ACTIVE.value,
            MembershipStatus.PENDING.value,
            MembershipStatus.INVITED.value,
        ):
            raise OrganizationMemberAlreadyExistsError()
        # Reuse the row for LEFT/REMOVED
        existing.status = MembershipStatus.ACTIVE.value
        existing.role = target_role
        existing.invited_by = actor.id
        existing.joined_at = utc_now()
        existing.left_at = None
        membership = existing
    else:
        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=target_user_id,
            role=target_role,
            status=MembershipStatus.ACTIVE.value,
            invited_by=actor.id,
            joined_at=utc_now(),
        )
        session.add(membership)

    session.commit()
    session.refresh(membership)

    # Publish event after commit
    default_event_bus.publish(
        OrganizationMemberJoined(
            event_id=_generate_event_id(),
            organization_id=org.id,
            user_id=target_user_id,
            actor_id=actor.id,
            role=membership.role,
            status=membership.status,
            occurred_at=utc_now(),
        )
    )

    return _membership_to_read(membership, target_user)


def list_members(
    actor: User,
    organization_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """List active members of an organization.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor cannot view members.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    membership = _get_membership(session, org.id, actor)
    if not permission_service.can_view_members(actor, org, membership):
        raise OrganizationPermissionDeniedError(message="无权查看成员列表")

    mem_repo = OrganizationMembershipRepository(session)
    memberships = mem_repo.list_active_by_org(org.id)

    members = []
    for m in memberships:
        user = UserRepository(session).get_by_id(m.user_id)
        if user is not None:
            members.append(_membership_to_read(m, user))

    return {"members": members, "total": len(members)}


def update_member_role(
    actor: User,
    organization_id: UUID,
    target_user_id: UUID,
    new_role: str,
    session: Session,
) -> dict[str, Any]:
    """Update a member's role.

    Protects the last OWNER: if the target is the last OWNER and
    new_role is not OWNER, raises OrganizationLastOwnerError.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor lacks permission.
        OrganizationLastOwnerError: If demoting the last OWNER.
    """
    _validate_role(new_role)

    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    actor_membership = _get_membership(session, org.id, actor)
    target_membership = OrganizationMembershipRepository(
        session
    ).get_active_by_org_user(org.id, target_user_id)
    if target_membership is None:
        from ...utils.errors import NotFoundError

        raise NotFoundError("用户")

    if not permission_service.can_change_member_role(
        actor, actor_membership, target_membership, new_role
    ):
        raise OrganizationPermissionDeniedError(message="无权修改成员角色")

    # If promoting to OWNER, need transfer permission
    if new_role == OrganizationRole.OWNER.value and not permission_service.can_transfer_ownership(
        actor, actor_membership
    ):
        raise OrganizationPermissionDeniedError(
            message="无权转让所有权，只有 OWNER 或 SYSTEM_ADMIN 可以"
        )

    old_role = target_membership.role

    # Last OWNER protection: cannot demote the last OWNER
    mem_repo = OrganizationMembershipRepository(session)
    if (
        old_role == OrganizationRole.OWNER.value
        and new_role != OrganizationRole.OWNER.value
    ):
        owner_count = mem_repo.count_active_owners(org.id)
        if owner_count <= 1:
            raise OrganizationLastOwnerError(
                message="最后一个所有者不能降级"
            )

    target_membership.role = new_role
    session.commit()
    session.refresh(target_membership)

    # Publish event after commit
    default_event_bus.publish(
        OrganizationMemberRoleChanged(
            event_id=_generate_event_id(),
            organization_id=org.id,
            user_id=target_user_id,
            actor_id=actor.id,
            old_role=old_role,
            new_role=new_role,
            occurred_at=utc_now(),
        )
    )

    target_user = _get_user_by_id(session, target_user_id)
    return _membership_to_read(target_membership, target_user)


def remove_member(
    actor: User,
    organization_id: UUID,
    target_user_id: UUID,
    session: Session,
) -> None:
    """Remove a member from an organization (status=REMOVED).

    Protects the last OWNER.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor lacks permission.
        OrganizationLastOwnerError: If removing the last OWNER.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    actor_membership = _get_membership(session, org.id, actor)
    target_membership = OrganizationMembershipRepository(
        session
    ).get_active_by_org_user(org.id, target_user_id)
    if target_membership is None:
        from ...utils.errors import NotFoundError

        raise NotFoundError("用户")

    if not permission_service.can_remove_member(
        actor, actor_membership, target_membership
    ):
        raise OrganizationPermissionDeniedError(message="无权移除成员")

    # Last OWNER protection
    mem_repo = OrganizationMembershipRepository(session)
    if target_membership.role == OrganizationRole.OWNER.value:
        owner_count = mem_repo.count_active_owners(org.id)
        if owner_count <= 1:
            raise OrganizationLastOwnerError(
                message="最后一个所有者不能被移除"
            )

    target_membership.status = MembershipStatus.REMOVED.value
    target_membership.left_at = utc_now()
    session.commit()

    # Publish event after commit
    default_event_bus.publish(
        OrganizationMemberLeft(
            event_id=_generate_event_id(),
            organization_id=org.id,
            user_id=target_user_id,
            actor_id=actor.id,
            action="removed",
            occurred_at=utc_now(),
        )
    )


def join_organization(
    actor: User,
    organization_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """Join an organization via self-service.

    - OPEN: membership ACTIVE, role MEMBER
    - APPROVAL: membership PENDING, role MEMBER
    - INVITE_ONLY/CLOSED: raises OrganizationInvalidJoinPolicyError

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationMemberAlreadyExistsError: If already a member.
        OrganizationInvalidJoinPolicyError: If join policy forbids self-join.
        OrganizationCapacityExceededError: If org is at capacity.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    mem_repo = OrganizationMembershipRepository(session)

    # Check if already an active member
    existing = mem_repo.get_by_org_user(org.id, actor.id)
    if existing is not None and existing.status in (
        MembershipStatus.ACTIVE.value,
        MembershipStatus.PENDING.value,
        MembershipStatus.INVITED.value,
    ):
        raise OrganizationMemberAlreadyExistsError()

    # Check join policy
    policy = org.join_policy
    if policy in (
        OrganizationJoinPolicy.INVITE_ONLY.value,
        OrganizationJoinPolicy.CLOSED.value,
    ):
        raise OrganizationInvalidJoinPolicyError()

    # Check capacity (for OPEN and APPROVAL)
    if policy == OrganizationJoinPolicy.OPEN.value:
        _check_capacity(session, org)

    # Determine status based on policy
    if policy == OrganizationJoinPolicy.OPEN.value:
        status = MembershipStatus.ACTIVE.value
        joined_at: datetime | None = utc_now()
    elif policy == OrganizationJoinPolicy.APPROVAL.value:
        status = MembershipStatus.PENDING.value
        joined_at = None
    else:
        raise OrganizationInvalidJoinPolicyError()

    if existing is not None:
        # Reuse the row for LEFT/REMOVED
        existing.status = status
        existing.role = OrganizationRole.MEMBER.value
        existing.joined_at = joined_at
        existing.left_at = None
        membership = existing
    else:
        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=actor.id,
            role=OrganizationRole.MEMBER.value,
            status=status,
            joined_at=joined_at,
        )
        session.add(membership)

    session.commit()
    session.refresh(membership)

    # Publish event after commit
    default_event_bus.publish(
        OrganizationMemberJoined(
            event_id=_generate_event_id(),
            organization_id=org.id,
            user_id=actor.id,
            actor_id=actor.id,
            role=membership.role,
            status=membership.status,
            occurred_at=utc_now(),
        )
    )

    return {
        "organization_id": str(org.id),
        "user_id": str(actor.id),
        "role": membership.role,
        "status": membership.status,
    }


def leave_organization(
    actor: User,
    organization_id: UUID,
    session: Session,
) -> None:
    """Leave an organization (status=LEFT).

    Only the current user can leave their own membership.
    Protects the last OWNER.

    Raises:
        OrganizationNotFoundError: If org not found.
        OrganizationPermissionDeniedError: If actor is not a member.
        OrganizationLastOwnerError: If the last OWNER tries to leave.
    """
    org = OrganizationRepository(session).get_active_by_id(organization_id)
    if org is None:
        raise OrganizationNotFoundError()

    mem_repo = OrganizationMembershipRepository(session)
    membership = mem_repo.get_active_by_org_user(org.id, actor.id)
    if membership is None:
        raise OrganizationPermissionDeniedError(
            message="你不是该组织的成员"
        )

    # Last OWNER protection
    if membership.role == OrganizationRole.OWNER.value:
        owner_count = mem_repo.count_active_owners(org.id)
        if owner_count <= 1:
            raise OrganizationLastOwnerError(
                message="最后一个所有者不能退出"
            )

    membership.status = MembershipStatus.LEFT.value
    membership.left_at = utc_now()
    session.commit()

    # Publish event after commit
    default_event_bus.publish(
        OrganizationMemberLeft(
            event_id=_generate_event_id(),
            organization_id=org.id,
            user_id=actor.id,
            actor_id=actor.id,
            action="left",
            occurred_at=utc_now(),
        )
    )


def list_user_organizations(
    actor: User | None,
    target_user_id: UUID,
    session: Session,
) -> dict[str, Any]:
    """List organizations for a user.

    If actor queries themselves, return all ACTIVE memberships.
    If actor queries someone else, return only PUBLIC orgs (and
    MEMBERS_ONLY/PRIVATE only if actor shares the org or has admin rights).

    Does NOT return email, student_no, password_hash.

    Raises:
        NotFoundError: If target user not found or deleted.
    """
    # Verify the target user exists (raises NotFoundError if not)
    _get_user_by_id(session, target_user_id)

    mem_repo = OrganizationMembershipRepository(session)
    org_repo = OrganizationRepository(session)
    memberships = mem_repo.list_active_by_user(target_user_id)

    orgs: list[dict[str, Any]] = []
    is_self = actor is not None and actor.id == target_user_id
    is_admin = actor is not None and permission_service._is_admin_level(actor)

    for m in memberships:
        org = org_repo.get_active_by_id(m.organization_id)
        if org is None:
            continue

        # Visibility filtering for non-self queries
        if not is_self and not is_admin:
            # Check if actor is a member of this org
            actor_membership = None
            if actor is not None:
                actor_membership = mem_repo.get_active_by_org_user(org.id, actor.id)

            # Only return PUBLIC orgs, or orgs the actor is also a member of
            if (
                org.visibility
                in (
                    OrganizationVisibility.PRIVATE.value,
                    OrganizationVisibility.MEMBERS_ONLY.value,
                )
                and actor_membership is None
            ):
                continue
            # PUBLIC: always visible

        member_count = org_repo.count_active_members(org.id)
        orgs.append(
            {
                "id": str(org.id),
                "name": org.name,
                "type": org.type,
                "visibility": org.visibility,
                "status": org.status,
                "role": m.role,
                "member_count": member_count,
            }
        )

    return {"organizations": orgs}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_membership(
    session: Session, organization_id: UUID, actor: User | None
) -> OrganizationMembership | None:
    """Get the actor's membership in an organization, or None."""
    if actor is None:
        return None
    return OrganizationMembershipRepository(session).get_active_by_org_user(
        organization_id, actor.id
    )
