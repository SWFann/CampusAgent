"""Scene schemas — Pydantic models for API and internal use.

Privacy:
- PrivateSubmissionCreate carries raw preferences but the response
  (PrivateSubmissionResponse) never echoes the raw payload.
- Only capsule-derived metadata and status are returned.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Scene Definition
# ---------------------------------------------------------------------------


class SceneDefinitionRead(BaseModel):
    id: UUID
    scene_key: str
    version: str
    name: str
    description: str | None = None
    enabled: bool
    capabilities: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Scene Instance
# ---------------------------------------------------------------------------


class SceneInstanceCreate(BaseModel):
    scene_key: str = Field(..., min_length=1, max_length=50)
    organization_id: UUID | None = None
    conversation_id: UUID | None = None
    public_context: dict[str, Any] | None = None
    participant_user_ids: list[UUID] = Field(..., min_length=1)
    idempotency_key: str | None = None
    expires_at: datetime | None = None

    model_config = {"extra": "forbid"}


class SceneInstanceRead(BaseModel):
    id: UUID
    scene_key: str
    status: str
    current_phase: str
    created_by: UUID
    conversation_id: UUID | None = None
    organization_id: UUID | None = None
    public_context: dict[str, Any] | None = None
    expires_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    failed_reason_code: str | None = None
    created_at: datetime
    updated_at: datetime
    participant_count: int = 0
    submitted_count: int = 0
    participant_status: str | None = None
    is_creator: bool = False

    model_config = {"from_attributes": True, "extra": "forbid"}


class SceneInstanceStatus(BaseModel):
    """Public status of a scene instance — no private data."""

    id: UUID
    status: str
    current_phase: str
    progress: dict[str, int] = Field(default_factory=dict)
    privacy: dict[str, bool] = Field(
        default_factory=lambda: {
            "raw_preferences_visible": False,
            "individual_scores_visible": False,
            "debate_visible": False,
        }
    )

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Participant
# ---------------------------------------------------------------------------


class ParticipantRead(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    is_creator: bool
    joined_at: datetime | None = None

    model_config = {"from_attributes": True, "extra": "forbid"}


# ---------------------------------------------------------------------------
# Private Submission
# ---------------------------------------------------------------------------


class PrivateSubmissionCreate(BaseModel):
    """Raw preferences from the user. Never echoed in response."""

    preferences: dict[str, Any] = Field(..., description="User's raw preferences")
    save_to_long_term_memory: bool = Field(default=False)

    model_config = {"extra": "forbid"}


class PrivateSubmissionResponse(BaseModel):
    """Response — never contains the raw payload."""

    submission_status: str = "ACCEPTED"
    capsule_generated: bool = True
    expires_at: datetime | None = None
    submission_id: UUID

    model_config = {"extra": "forbid"}


class PrivateSubmissionStatus(BaseModel):
    """Status of a user's submission — no raw content."""

    has_submitted: bool
    submitted_at: datetime | None = None
    expires_at: datetime | None = None
    capsule_generated: bool = False

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


class CandidateRead(BaseModel):
    id: UUID
    candidate_key: str
    display_name: str
    public_metadata: dict[str, Any] | None = None
    aggregate_score: float | None = None
    public_reason: str | None = None
    status: str
    rank: int | None = None

    model_config = {"from_attributes": True, "extra": "forbid"}


# ---------------------------------------------------------------------------
# Vote
# ---------------------------------------------------------------------------


class VoteCreate(BaseModel):
    candidate_id: UUID
    vote_value: str = Field(..., description="APPROVE / REJECT / ABSTAIN")
    idempotency_key: str | None = None

    model_config = {"extra": "forbid"}


class VoteRead(BaseModel):
    id: UUID
    candidate_id: UUID
    vote_value: str
    created_at: datetime

    model_config = {"from_attributes": True, "extra": "forbid"}


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


class SceneResultRead(BaseModel):
    id: UUID
    selected_candidate: CandidateRead | None = None
    public_summary: str | None = None
    participant_count: int
    submitted_count: int
    created_at: datetime

    model_config = {"from_attributes": True, "extra": "forbid"}


# ---------------------------------------------------------------------------
# State transition
# ---------------------------------------------------------------------------


class StateTransitionRequest(BaseModel):
    action: str = Field(..., description="publish, cancel, confirm, etc.")
    idempotency_key: str | None = None

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Scene Plugin Protocol data types
# ---------------------------------------------------------------------------


class PrivateCapsule(BaseModel):
    """Minimised, non-sensitive derivative of private preferences.

    Contains hard constraints, soft preferences, and weights — NOT raw
    free-text or identifiable data.
    """

    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    soft_preferences: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    allowed_reason_codes: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class CandidateInput(BaseModel):
    """Public candidate data for plugin evaluation."""

    candidate_key: str
    display_name: str
    public_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class EvaluationResult(BaseModel):
    """Private evaluation result — never exposed publicly."""

    candidate_key: str
    hard_pass: bool = True
    utility: float = 0.0
    objection: bool = False
    reason_codes: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class AggregateResult(BaseModel):
    """Aggregated result across all participants — public-safe."""

    candidate_key: str
    aggregate_score: float
    public_reason: str
    rank: int
    hard_gate_passed: bool = True

    model_config = {"extra": "forbid"}
