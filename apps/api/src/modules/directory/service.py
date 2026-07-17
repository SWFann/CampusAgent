"""
Service layer for the directory module.

Provides:
- ``search_directory``: search users and organizations with privacy-safe projections.
- ``get_organization_tree``: get a visibility-filtered organization tree.
- ``get_recommended_organizations``: get non-sensitive recommendations.

Privacy principles:
- User search does NOT search or return email, student_no, password_hash, or bio.
- Organization search respects visibility (PUBLIC/MEMBERS_ONLY/PRIVATE).
- Tree nodes are filtered by the actor's permissions.
- Recommendations use only non-sensitive org relationships — no implicit profiling.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..organizations.models import (
    Organization,
    OrganizationStatus,
    OrganizationVisibility,
)
from ..organizations.permissions import permission_service
from ..organizations.repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
)
from ..users.models import User, UserStatus
from .exceptions import (
    DirectoryInvalidTypeError,
    DirectoryOrgNotFoundError,
    DirectoryQueryTooShortError,
    DirectoryTreeTooDeepError,
)
from .schemas import DirectorySearchType

# Maximum allowed tree depth for safety
MAX_TREE_DEPTH = 5
# Minimum search query length
MIN_QUERY_LENGTH = 2


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search_directory(
    actor: User | None,
    *,
    q: str,
    search_type: str = DirectorySearchType.ALL.value,
    limit: int = 20,
    offset: int = 0,
    session: Session,
) -> dict[str, Any]:
    """Search the directory for users and/or organizations.

    Args:
        actor: The current user (or None for anonymous).
        q: The search query string.
        search_type: One of "all", "users", "organizations".
        limit: Maximum results per category.
        offset: Pagination offset.
        session: SQLAlchemy session.

    Returns:
        A dict with "users", "organizations", "total", "query", "search_type".

    Raises:
        DirectoryQueryTooShortError: If q is too short.
        DirectoryInvalidTypeError: If search_type is invalid.
    """
    query = q.strip()
    if len(query) < MIN_QUERY_LENGTH:
        raise DirectoryQueryTooShortError(
            details={"min_length": MIN_QUERY_LENGTH, "actual_length": len(query)}
        )

    valid_types = {t.value for t in DirectorySearchType}
    if search_type not in valid_types:
        raise DirectoryInvalidTypeError(
            details={"valid_types": list(valid_types), "actual": search_type}
        )

    users: list[dict[str, Any]] = []
    organizations: list[dict[str, Any]] = []

    if search_type in (DirectorySearchType.ALL.value, DirectorySearchType.USERS.value):
        users = _search_users(query, limit, offset, session)

    if search_type in (
        DirectorySearchType.ALL.value,
        DirectorySearchType.ORGANIZATIONS.value,
    ):
        organizations = _search_organizations(query, actor, limit, offset, session)

    total = len(users) + len(organizations)

    return {
        "users": users,
        "organizations": organizations,
        "total": total,
        "query": q,
        "search_type": search_type,
    }


def _search_users(
    query: str, limit: int, offset: int, session: Session
) -> list[dict[str, Any]]:
    """Search users by display_name only.

    Privacy: Does NOT search email, student_no, or bio.
    Does NOT return email, student_no, password_hash, or bio.
    Excludes DELETED and DISABLED users.
    """
    pattern = f"%{query}%"
    stmt = select(User).where(
        User.display_name.ilike(pattern),
        User.status == UserStatus.ACTIVE.value,
    )
    stmt = stmt.order_by(User.display_name.asc()).limit(limit).offset(offset)
    results = session.execute(stmt).scalars().all()

    # Get profile visibility for each user
    from ..users.models import StudentProfile

    users: list[dict[str, Any]] = []
    for user in results:
        profile_stmt = select(StudentProfile).where(
            StudentProfile.user_id == user.id
        )
        profile = session.execute(profile_stmt).scalar_one_or_none()
        visibility = profile.profile_visibility if profile else "PUBLIC"

        users.append(
            {
                "id": str(user.id),
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "profile_visibility": visibility,
            }
        )

    return users


def _search_organizations(
    query: str,
    actor: User | None,
    limit: int,
    offset: int,
    session: Session,
) -> list[dict[str, Any]]:
    """Search organizations by name or slug.

    Privacy: PUBLIC orgs visible to all.
    MEMBERS_ONLY/PRIVATE only visible to members or system/school admins.
    DELETED/ARCHIVED excluded.
    """
    repo = OrganizationRepository(session)
    orgs = repo.search(query, limit=limit, offset=offset)

    mem_repo = OrganizationMembershipRepository(session)
    visible_orgs: list[dict[str, Any]] = []

    for org in orgs:
        membership = None
        if actor is not None:
            membership = mem_repo.get_active_by_org_user(org.id, actor.id)

        if permission_service.can_view_organization(actor, org, membership):
            member_count = repo.count_active_members(org.id)
            visible_orgs.append(
                {
                    "id": str(org.id),
                    "name": org.name,
                    "type": org.type,
                    "visibility": org.visibility,
                    "status": org.status,
                    "member_count": member_count,
                }
            )

    return visible_orgs


# ---------------------------------------------------------------------------
# Organization Tree
# ---------------------------------------------------------------------------


def get_organization_tree(
    actor: User | None,
    *,
    root_organization_id: UUID | None = None,
    max_depth: int = 3,
    session: Session,
) -> dict[str, Any]:
    """Get a visibility-filtered organization tree.

    Args:
        actor: The current user (or None for anonymous).
        root_organization_id: If provided, return the subtree rooted at this org.
            If None, return all root-level (parentless) organizations.
        max_depth: Maximum depth of the tree (default 3, max 5).
        session: SQLAlchemy session.

    Returns:
        A dict with "nodes" (list of tree nodes) and "max_depth".

    Raises:
        DirectoryTreeTooDeepError: If max_depth exceeds MAX_TREE_DEPTH.
        DirectoryOrgNotFoundError: If root org not found or not visible.
    """
    if max_depth > MAX_TREE_DEPTH:
        raise DirectoryTreeTooDeepError(
            details={"max_allowed": MAX_TREE_DEPTH, "requested": max_depth}
        )

    repo = OrganizationRepository(session)
    mem_repo = OrganizationMembershipRepository(session)

    def _can_view(org: Organization) -> bool:
        membership = None
        if actor is not None:
            membership = mem_repo.get_active_by_org_user(org.id, actor.id)
        return permission_service.can_view_organization(actor, org, membership)

    def _build_node(org: Organization, depth: int) -> dict[str, Any] | None:
        """Recursively build a tree node, returning None if not visible."""
        if not _can_view(org):
            return None

        children: list[dict[str, Any]] = []
        if depth < max_depth:
            child_orgs = repo.get_children(org.id)
            for child in child_orgs:
                child_node = _build_node(child, depth + 1)
                if child_node is not None:
                    children.append(child_node)

        return {
            "id": str(org.id),
            "name": org.name,
            "type": org.type,
            "visibility": org.visibility,
            "status": org.status,
            "parent_id": str(org.parent_id) if org.parent_id else None,
            "children": children,
        }

    nodes: list[dict[str, Any]] = []

    if root_organization_id is not None:
        root = repo.get_active_by_id(root_organization_id)
        if root is None:
            raise DirectoryOrgNotFoundError()
        if not _can_view(root):
            raise DirectoryOrgNotFoundError()
        node = _build_node(root, 0)
        if node is not None:
            nodes.append(node)
    else:
        # Return all root-level (parentless) active organizations
        stmt = select(Organization).where(
            Organization.parent_id.is_(None),
            Organization.status != OrganizationStatus.DELETED.value,
        )
        stmt = stmt.order_by(Organization.name.asc())
        root_orgs = session.execute(stmt).scalars().all()

        for org in root_orgs:
            node = _build_node(org, 0)
            if node is not None:
                nodes.append(node)

    return {"nodes": nodes, "max_depth": max_depth}


# ---------------------------------------------------------------------------
# Recommended Organizations
# ---------------------------------------------------------------------------


def get_recommended_organizations(
    actor: User | None,
    *,
    limit: int = 10,
    session: Session,
) -> dict[str, Any]:
    """Get recommended organizations for the current user.

    MVP recommendation rules:
    - No implicit profiling.
    - No reading private preferences, chat, messages, or memories.
    - Based on the user's existing org relationships:
      - Same parent PUBLIC organizations.
      - PUBLIC CLUB/COURSE/TEAM the user hasn't joined.
    - If no safe recommendations, return empty array.
    - Each recommendation includes a reason field.

    Args:
        actor: The current user (or None for anonymous).
        limit: Maximum recommendations.
        session: SQLAlchemy session.

    Returns:
        A dict with "recommendations" (list) and "total".
    """
    recommendations: list[dict[str, Any]] = []

    if actor is None:
        # Anonymous: return some PUBLIC orgs as general recommendations
        repo = OrganizationRepository(session)
        orgs = repo.list_active(limit=limit)
        for org in orgs:
            if org.visibility == OrganizationVisibility.PUBLIC.value:
                recommendations.append(
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "type": org.type,
                        "visibility": org.visibility,
                        "reason": "public_organization",
                    }
                )
                if len(recommendations) >= limit:
                    break
        return {"recommendations": recommendations, "total": len(recommendations)}

    repo = OrganizationRepository(session)
    mem_repo = OrganizationMembershipRepository(session)

    # Get user's current org memberships
    user_memberships = mem_repo.list_active_by_user(actor.id)
    user_org_ids = {m.organization_id for m in user_memberships}

    # Strategy 1: Same parent PUBLIC organizations
    # For each org the user is a member of, find sibling PUBLIC orgs
    seen: set[UUID] = set()
    for membership in user_memberships:
        member_org = repo.get_active_by_id(membership.organization_id)
        if member_org is None or member_org.parent_id is None:
            continue

        siblings = repo.get_children(member_org.parent_id)
        for sibling in siblings:
            if (
                sibling.id not in user_org_ids
                and sibling.id not in seen
                and sibling.visibility == OrganizationVisibility.PUBLIC.value
            ):
                seen.add(sibling.id)
                recommendations.append(
                    {
                        "id": str(sibling.id),
                        "name": sibling.name,
                        "type": sibling.type,
                        "visibility": sibling.visibility,
                        "reason": "same_parent_public_organization",
                    }
                )
                if len(recommendations) >= limit:
                    return {
                        "recommendations": recommendations,
                        "total": len(recommendations),
                    }

    # Strategy 2: PUBLIC CLUB/COURSE/TEAM the user hasn't joined
    if len(recommendations) < limit:
        stmt = select(Organization).where(
            Organization.status == OrganizationStatus.ACTIVE.value,
            Organization.visibility == OrganizationVisibility.PUBLIC.value,
            Organization.type.in_(["CLUB", "COURSE", "TEAM"]),
        )
        stmt = stmt.order_by(Organization.created_at.desc()).limit(limit * 2)
        candidate_orgs = session.execute(stmt).scalars().all()

        for org in candidate_orgs:
            if org.id not in user_org_ids and org.id not in seen:
                seen.add(org.id)
                recommendations.append(
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "type": org.type,
                        "visibility": org.visibility,
                        "reason": "public_club_course_team",
                    }
                )
                if len(recommendations) >= limit:
                    break

    return {"recommendations": recommendations, "total": len(recommendations)}
