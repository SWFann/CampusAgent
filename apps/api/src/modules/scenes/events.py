"""Domain events for the scenes module.

These events use the shared ``DomainEvent`` base class and the
``default_event_bus``. They are published AFTER a successful commit.

Privacy requirements (P8 guide §13):
- Events ONLY contain: scene_instance_id, phase, submitted_count,
  candidate_count, public_result_id.
- Events NEVER contain: private payload, capsule, individual score,
  memory content, or any P4 data.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...events.bus import DomainEvent


@dataclass(frozen=True)
class SceneInstanceCreated(DomainEvent):
    """Published when a new scene instance is created."""

    event_id: str
    scene_instance_id: UUID
    scene_key: str
    created_by: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class ScenePhaseChanged(DomainEvent):
    """Published when a scene instance transitions to a new phase.

    Privacy: only the phase name and counts are included — never
    private submissions, capsules, or individual scores.
    """

    event_id: str
    scene_instance_id: UUID
    old_phase: str
    new_phase: str
    submitted_count: int
    participant_count: int
    occurred_at: datetime


@dataclass(frozen=True)
class SceneCandidateReady(DomainEvent):
    """Published when candidates are generated and ready for voting.

    Privacy: only the candidate count is included — never individual
    scores or capsule data.
    """

    event_id: str
    scene_instance_id: UUID
    candidate_count: int
    occurred_at: datetime


@dataclass(frozen=True)
class SceneVotingComplete(DomainEvent):
    """Published when voting is complete.

    Privacy: only the vote count is included — never who voted for what.
    """

    event_id: str
    scene_instance_id: UUID
    vote_count: int
    participant_count: int
    occurred_at: datetime


@dataclass(frozen=True)
class SceneCompleted(DomainEvent):
    """Published when a scene instance reaches the COMPLETED state.

    Privacy: only the public_result_id is included — never the full
    result content (which is fetched via the API).
    """

    event_id: str
    scene_instance_id: UUID
    public_result_id: UUID | None
    participant_count: int
    submitted_count: int
    occurred_at: datetime


@dataclass(frozen=True)
class SceneCancelled(DomainEvent):
    """Published when a scene instance is cancelled."""

    event_id: str
    scene_instance_id: UUID
    cancelled_by: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class SceneExpired(DomainEvent):
    """Published when a scene instance expires."""

    event_id: str
    scene_instance_id: UUID
    occurred_at: datetime


@dataclass(frozen=True)
class SceneFailed(DomainEvent):
    """Published when a scene instance fails.

    Privacy: only the reason_code is included (a stable enum-like string),
    never the raw error message or stack trace.
    """

    event_id: str
    scene_instance_id: UUID
    reason_code: str
    occurred_at: datetime


@dataclass(frozen=True)
class ScenePrivateDataCleaned(DomainEvent):
    """Published after private data cleanup completes.

    Privacy: only the scene_instance_id and submission_count are included.
    """

    event_id: str
    scene_instance_id: UUID
    submission_count: int
    occurred_at: datetime
