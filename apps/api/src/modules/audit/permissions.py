"""Authorization policy boundary for the audit module."""

from __future__ import annotations

from typing import Protocol


class PermissionPolicy(Protocol):
    """Contract implemented by module-specific authorization policies."""

    def can(
        self,
        *,
        actor_id: str,
        action: str,
        resource_id: str | None = None,
    ) -> bool:
        """Return whether an actor may perform an action on a resource."""
        ...
