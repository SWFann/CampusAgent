"""Authorization policy boundary for the users module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class PermissionPolicy(Protocol):
    """Contract implemented by module-specific authorization policies."""

    def can(
        self,
        *,
        actor_id: UUID,
        action: str,
        resource_id: UUID | None = None,
    ) -> bool:
        """Return whether an actor may perform an action on a resource."""
        ...


def is_self(actor_id: UUID, user_id: UUID) -> bool:
    """Check if the actor is the user themselves."""
    return actor_id == user_id
