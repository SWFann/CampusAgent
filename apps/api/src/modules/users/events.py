"""Domain event boundary for the users module."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...events.bus import DomainEvent


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Domain event published when a user successfully registers.

    This event is published AFTER the transaction commits.
    Handlers (e.g., P6-02 auto-create personal Agent) subscribe to it.

    Attributes:
        event_id: Unique event identifier (UUID v4 string).
        user_id: The newly registered user's UUID.
        email_hash: SHA-256 hash of the normalised email (privacy-preserving).
        occurred_at: When the registration was committed (UTC).
    """

    event_id: str
    user_id: UUID
    email_hash: str
    occurred_at: datetime


def create_user_registered_event(
    user_id: UUID,
    email: str,
    occurred_at: datetime,
) -> UserRegistered:
    """Create a UserRegistered event.

    The email is hashed (SHA-256) to avoid leaking PII in event logs.
    A fresh event_id (UUID v4) is generated.

    Args:
        user_id: The registered user's UUID.
        email: The normalised email (will be hashed).
        occurred_at: The commit timestamp (UTC).

    Returns:
        A ``UserRegistered`` event instance.
    """
    from uuid import uuid4

    email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()
    return UserRegistered(
        event_id=str(uuid4()),
        user_id=user_id,
        email_hash=email_hash,
        occurred_at=occurred_at,
    )
