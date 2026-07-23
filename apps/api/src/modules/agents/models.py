"""Agent ORM models. Privacy: private_config_encrypted never in repr."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from ...db.base import Base
from ...db.time import utc_now
from ...db.types import new_uuid


class AgentType(StrEnum):
    PERSONAL = "PERSONAL"
    GROUP = "GROUP"
    ORG = "ORG"


class DelegationLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class AgentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETED = "DELETED"


class AgentRunStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class WorkspaceThreadStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class WorkspaceMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Agent(Base):
    """Agent entity. private_config_encrypted never exposed in repr."""

    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_persona: Mapped[str | None] = mapped_column(Text, nullable=True)
    private_config_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_route_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    delegation_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default=DelegationLevel.L0.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AgentStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    runs: Mapped[list[AgentRun]] = relationship(
        "AgentRun", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} type={self.type} name={self.name} status={self.status}>"


class AgentRun(Base):
    """Agent run metadata. Only hashes — never prompt/response content."""

    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    agent_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    output_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AgentRunStatus.SUCCESS.value
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    agent: Mapped[Agent] = relationship("Agent", back_populates="runs")

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id} agent_id={self.agent_id} purpose={self.purpose} status={self.status}>"


class WorkspaceThread(Base):
    """An owner-only personal workspace task conversation."""

    __tablename__ = "workspace_threads"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    owner_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="新的个人任务")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkspaceThreadStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    messages: Mapped[list[WorkspaceMessage]] = relationship(
        "WorkspaceMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="WorkspaceMessage.created_at",
    )

    def __repr__(self) -> str:
        return f"<WorkspaceThread id={self.id} owner={self.owner_user_id} status={self.status}>"


class WorkspaceMessage(Base):
    """Encrypted message content for a personal workspace thread."""

    __tablename__ = "workspace_messages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    thread_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("workspace_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    thread: Mapped[WorkspaceThread] = relationship("WorkspaceThread", back_populates="messages")

    def __repr__(self) -> str:
        return f"<WorkspaceMessage id={self.id} thread={self.thread_id} role={self.role}>"
