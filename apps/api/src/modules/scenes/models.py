"""Scene ORM models.

Privacy:
- PrivateSubmission.encrypted_payload is Fernet-encrypted; plaintext never
  appears in repr, logs, or API responses.
- SceneCandidate and SceneResult only store public data.
- No private payload, capsule, or individual score is ever stored in
  plaintext or returned via repr.
"""
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

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ParticipantStatus(StrEnum):
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    LEFT = "LEFT"


class CandidateStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    ELIMINATED = "ELIMINATED"
    SELECTED = "SELECTED"


class VoteValue(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"


# ---------------------------------------------------------------------------
# SceneDefinition — registered scene type (e.g. "meal_planning")
# ---------------------------------------------------------------------------


class SceneDefinition(Base):
    """A registered scene plugin definition.

    scene_key + version must be unique (enforced by the registry, not the DB
    — the DB is populated by the registry at startup or via admin API).
    """

    __tablename__ = "scene_definitions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scene_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(
        default=True, nullable=False
    )
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    instances: Mapped[list[SceneInstance]] = relationship(
        back_populates="definition", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<SceneDefinition id={self.id} scene_key={self.scene_key} "
            f"version={self.version} enabled={self.enabled}>"
        )


# ---------------------------------------------------------------------------
# SceneInstance — a running scene (e.g. a specific meal planning session)
# ---------------------------------------------------------------------------


class SceneInstance(Base):
    """A running scene instance.

    Privacy: no private payload is stored on this model. The status and
    current_phase are public metadata.
    """

    __tablename__ = "scene_instances"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    definition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_definitions.id"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=True, index=True
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    current_phase: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    public_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    definition: Mapped[SceneDefinition] = relationship(back_populates="instances")
    participants: Mapped[list[SceneParticipant]] = relationship(
        back_populates="instance", cascade="all, delete-orphan"
    )
    submissions: Mapped[list[PrivateSubmission]] = relationship(
        back_populates="instance", cascade="all, delete-orphan"
    )
    candidates: Mapped[list[SceneCandidate]] = relationship(
        back_populates="instance", cascade="all, delete-orphan"
    )
    votes: Mapped[list[SceneVote]] = relationship(
        back_populates="instance", cascade="all, delete-orphan"
    )
    result: Mapped[SceneResult | None] = relationship(
        back_populates="instance", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<SceneInstance id={self.id} status={self.status} "
            f"phase={self.current_phase} version={self.version}>"
        )


# ---------------------------------------------------------------------------
# SceneParticipant — who is in the scene
# ---------------------------------------------------------------------------


class SceneParticipant(Base):
    """A participant in a scene instance."""

    __tablename__ = "scene_participants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scene_instance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_instances.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ParticipantStatus.INVITED.value
    )
    consent_record_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    is_creator: Mapped[bool] = mapped_column(default=False, nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    instance: Mapped[SceneInstance] = relationship(back_populates="participants")

    def __repr__(self) -> str:
        return (
            f"<SceneParticipant id={self.id} user_id={self.user_id} "
            f"status={self.status} is_creator={self.is_creator}>"
        )


# ---------------------------------------------------------------------------
# PrivateSubmission — encrypted private preference submission
# ---------------------------------------------------------------------------


class PrivateSubmission(Base):
    """Encrypted private submission for a scene.

    Privacy:
    - encrypted_payload: Fernet ciphertext of the user's raw preferences.
    - capsule_json: a minimised, non-sensitive derivative (hard constraints,
      soft preferences, weights) — NOT the raw input.
    - plaintext is never stored, logged, or returned.
    - deleted_at soft-deletes; cleanup hard-purges after expiry.
    """

    __tablename__ = "scene_private_submissions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scene_instance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_instances.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    capsule_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, nullable=False
    )

    instance: Mapped[SceneInstance] = relationship(back_populates="submissions")

    def __repr__(self) -> str:
        return (
            f"<PrivateSubmission id={self.id} user_id={self.user_id} "
            f"has_payload={self.encrypted_payload is not None} "
            f"deleted={self.deleted_at is not None}>"
        )


# ---------------------------------------------------------------------------
# SceneCandidate — public candidate (e.g. a restaurant)
# ---------------------------------------------------------------------------


class SceneCandidate(Base):
    """A public candidate generated by the scene plugin.

    Only public data is stored — no private scores or individual preferences.
    """

    __tablename__ = "scene_candidates"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scene_instance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_instances.id"), nullable=False, index=True
    )
    candidate_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    public_metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    aggregate_score: Mapped[float | None] = mapped_column(nullable=True)
    public_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CandidateStatus.PENDING.value
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    instance: Mapped[SceneInstance] = relationship(back_populates="candidates")

    def __repr__(self) -> str:
        return (
            f"<SceneCandidate id={self.id} key={self.candidate_key} "
            f"score={self.aggregate_score} status={self.status}>"
        )


# ---------------------------------------------------------------------------
# SceneVote — a participant's vote on candidates
# ---------------------------------------------------------------------------


class SceneVote(Base):
    """A vote by a participant on a candidate."""

    __tablename__ = "scene_votes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scene_instance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_instances.id"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    candidate_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_candidates.id"), nullable=False, index=True
    )
    vote_value: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    instance: Mapped[SceneInstance] = relationship(back_populates="votes")

    def __repr__(self) -> str:
        return (
            f"<SceneVote id={self.id} user_id={self.user_id} "
            f"vote={self.vote_value}>"
        )


# ---------------------------------------------------------------------------
# SceneResult — the final confirmed result
# ---------------------------------------------------------------------------


class SceneResult(Base):
    """The public final result of a scene.

    Only stores public data: selected candidate, aggregate reason, and
    participant count. Never stores individual scores or preferences.
    """

    __tablename__ = "scene_results"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    scene_instance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("scene_instances.id"), nullable=False, unique=True, index=True
    )
    selected_candidate_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("scene_candidates.id"), nullable=True
    )
    public_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    instance: Mapped[SceneInstance] = relationship(back_populates="result")

    def __repr__(self) -> str:
        return (
            f"<SceneResult id={self.id} "
            f"selected={self.selected_candidate_id} "
            f"participants={self.participant_count}>"
        )
