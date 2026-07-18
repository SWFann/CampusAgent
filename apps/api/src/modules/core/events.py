"""
Domain event types and event bus

Events are used for inter-module communication.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class DomainEvent:
    """Base domain event"""

    event_id: UUID
    event_type: str
    aggregate_id: UUID
    occurred_at: datetime
    payload: dict[str, Any]


# Event types
class EventTypes:
    """Domain event types"""

    # User events
    USER_REGISTERED = "user.registered"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"

    # Organization events
    ORG_CREATED = "org.created"
    MEMBER_ADDED = "member.added"
    MEMBER_REMOVED = "member.removed"

    # Conversation events
    CONVERSATION_CREATED = "conversation.created"
    MESSAGE_SENT = "message.sent"

    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_AUTONOMY_CHANGED = "agent.autonomy_changed"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_DELETED = "memory.deleted"

    # Scene events
    SCENE_CREATED = "scene.created"
    SCENE_STATE_CHANGED = "scene.state_changed"
    SCENE_COMPLETED = "scene.completed"
    SCENE_CANCELLED = "scene.cancelled"

    # Consent events
    CONSENT_GRANTED = "consent.granted"
    CONSENT_REVOKED = "consent.revoked"


# Event bus interface (implementation in P2)
class EventBus:
    """Domain event bus"""

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event"""
        raise NotImplementedError

    async def subscribe(
        self,
        event_type: str,
        handler: Any,
    ) -> None:
        """Subscribe to an event type"""
        raise NotImplementedError
