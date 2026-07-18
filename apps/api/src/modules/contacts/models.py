"""Contact relationship models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid


class ContactStatus(StrEnum):
    """Lifecycle state for a contact relationship."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class ContactRelationship(Base):
    """A user-to-user contact request or accepted friendship."""

    __tablename__ = "contact_relationships"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_contacts_pair"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    requester_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    addressee_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ContactStatus.PENDING.value
    )
    requested_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ContactRelationship id={self.id} requester={self.requester_id} "
            f"addressee={self.addressee_id} status={self.status}>"
        )
