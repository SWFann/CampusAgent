"""
Domain events for the organizations module.

These events use the P2 ``DomainEvent`` base class and the shared
``default_event_bus``. They are published AFTER a successful commit.

Privacy requirements:
- Events do NOT contain email, student_no, password_hash, token, or session info.
- Events only store IDs, roles, and status — no private content.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...events.bus import DomainEvent


@dataclass(frozen=True)
class OrganizationCreated(DomainEvent):
    """Published when a new organization is created."""

    event_id: str
    organization_id: UUID
    actor_id: UUID
    organization_type: str
    occurred_at: datetime


@dataclass(frozen=True)
class OrganizationArchived(DomainEvent):
    """Published when an organization is archived or deleted."""

    event_id: str
    organization_id: UUID
    actor_id: UUID
    action: str  # "archived" or "deleted"
    occurred_at: datetime


@dataclass(frozen=True)
class OrganizationMemberJoined(DomainEvent):
    """Published when a user joins or is added to an organization."""

    event_id: str
    organization_id: UUID
    user_id: UUID
    actor_id: UUID
    role: str
    status: str
    occurred_at: datetime


@dataclass(frozen=True)
class OrganizationMemberLeft(DomainEvent):
    """Published when a user leaves or is removed from an organization."""

    event_id: str
    organization_id: UUID
    user_id: UUID
    actor_id: UUID
    action: str  # "left" or "removed"
    occurred_at: datetime


@dataclass(frozen=True)
class OrganizationMemberRoleChanged(DomainEvent):
    """Published when a member's role is changed."""

    event_id: str
    organization_id: UUID
    user_id: UUID
    actor_id: UUID
    old_role: str
    new_role: str
    occurred_at: datetime
