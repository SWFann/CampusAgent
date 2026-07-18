"""ModelDefinition ORM model — registered model configurations.

Privacy:
- No API key, credential, or prompt content is stored here.
- Credentials live on ModelNode (encrypted); ModelDefinition only holds
  non-sensitive model metadata.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid


class ModelProviderType(StrEnum):
    """Provider type for a model definition."""

    LOCAL = "local"
    EXTERNAL = "external"
    MOCK = "mock"
    RULE = "rule"


class ModelType(StrEnum):
    """Model capability type."""

    CHAT = "chat"
    EMBEDDING = "embedding"


class ModelDefinition(Base):
    """Registered model configuration.

    Stores non-sensitive metadata about a model: name, version, provider
    type, capabilities, and defaults. Sensitive credentials are stored on
    the associated ModelNode (encrypted).
    """

    __tablename__ = "model_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model_type: Mapped[str] = mapped_column(String(20), nullable=False)
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ModelDefinition id={self.id} name={self.name} "
            f"provider={self.provider} enabled={self.enabled}>"
        )
