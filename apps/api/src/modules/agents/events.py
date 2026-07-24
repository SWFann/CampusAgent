"""Agent events for domain event bus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...events.bus import DomainEvent


@dataclass(frozen=True)
class PersonalAgentCreated(DomainEvent):
    """Published when a personal agent is auto-created after user registration."""

    event_id: str
    agent_id: UUID
    owner_user_id: UUID
    occurred_at: datetime
