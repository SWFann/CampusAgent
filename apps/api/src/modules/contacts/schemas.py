"""Contact API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ContactRequestCreate(BaseModel):
    """POST /api/v1/contacts/requests body."""

    target_user_id: UUID


class ContactUserRead(BaseModel):
    """Safe user projection for contact pages."""

    id: UUID
    display_name: str
    avatar_url: str | None = None


class ContactRead(BaseModel):
    """Accepted contact item."""

    user: ContactUserRead
    relationship_id: UUID
    status: str
    requested_at: datetime
    responded_at: datetime | None = None


class ContactRequestRead(BaseModel):
    """Pending incoming/outgoing contact request."""

    id: UUID
    requester: ContactUserRead
    addressee: ContactUserRead
    status: str
    requested_at: datetime


class ContactListResponse(BaseModel):
    """GET /api/v1/contacts response."""

    contacts: list[ContactRead]
    total: int


class ContactRequestsResponse(BaseModel):
    """GET /api/v1/contacts/requests response."""

    incoming: list[ContactRequestRead]
    outgoing: list[ContactRequestRead]
