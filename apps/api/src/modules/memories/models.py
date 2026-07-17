"""Memory ORM models. Privacy: content_encrypted never in repr/logs."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid


class MemoryCategory(StrEnum):
    PREFERENCE = "PREFERENCE"
    FACT = "FACT"
    CONTEXT = "CONTEXT"
    FEEDBACK = "FEEDBACK"


class SensitivityLevel(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"


class MemorySource(StrEnum):
    USER_INPUT = "USER_INPUT"
    AGENT_INFERRED = "AGENT_INFERRED"
    SYSTEM = "SYSTEM"


class ConsentPurpose(StrEnum):
    CHAT_REPLY = "chat_reply"
    SCENE_EXECUTION = "scene_execution"
    MEMORY_REVIEW = "memory_review"
    RECOMMENDATION = "recommendation"


class ConsentStatus(StrEnum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"


class MemoryItem(Base):
    """Memory item with encrypted content. Never expose content_encrypted."""
    __tablename__ = "memory_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    sensitivity_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SensitivityLevel.INTERNAL.value
    )
    source: Mapped[str] = mapped_column(
        String(40), nullable=False, default=MemorySource.USER_INPUT.value
    )
    content_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    encryption_key_version: Mapped[int] = mapped_column(default=1, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    consents: Mapped[list[ConsentRecord]] = relationship(
        "ConsentRecord", back_populates="memory", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MemoryItem id={self.id} owner={self.owner_user_id} category={self.category}>"


class ConsentRecord(Base):
    """Consent record for memory access control."""
    __tablename__ = "consent_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    grantor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    grantee_agent_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ConsentStatus.GRANTED.value
    )
    granted_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    memory_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("memory_items.id"), nullable=True
    )
    memory: Mapped[MemoryItem | None] = relationship("MemoryItem", back_populates="consents")

    def __repr__(self) -> str:
        return f"<ConsentRecord id={self.id} grantor={self.grantor_user_id} purpose={self.purpose} status={self.status}>"
