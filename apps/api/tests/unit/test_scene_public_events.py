"""P8-09: Scene public events tests.

Tests:
- Events only contain public fields (no private payload, capsule, individual score).
- SceneInstanceCreated event has correct fields.
- ScenePhaseChanged event has counts but no private data.
- SceneCompleted event has public_result_id but no private content.
- SceneCancelled event has no private data.
- ScenePrivateDataCleaned event only has count.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from src.modules.scenes.events import (
    SceneCancelled,
    SceneCandidateReady,
    SceneCompleted,
    SceneExpired,
    SceneFailed,
    SceneInstanceCreated,
    ScenePhaseChanged,
    ScenePrivateDataCleaned,
    SceneVotingComplete,
)


class TestPublicEvents:
    """Verify that all scene events contain only public fields."""

    def test_scene_instance_created_fields(self) -> None:
        event = SceneInstanceCreated(
            event_id="abc",
            scene_instance_id=uuid4(),
            scene_key="test",
            created_by=uuid4(),
            occurred_at=datetime.utcnow(),
        )
        # Check fields
        assert hasattr(event, "scene_instance_id")
        assert hasattr(event, "scene_key")
        assert hasattr(event, "created_by")
        # Must NOT have private fields
        assert not hasattr(event, "preferences")
        assert not hasattr(event, "capsule")
        assert not hasattr(event, "encrypted_payload")

    def test_scene_phase_changed_fields(self) -> None:
        event = ScenePhaseChanged(
            event_id="abc",
            scene_instance_id=uuid4(),
            old_phase="DRAFT",
            new_phase="INVITING",
            submitted_count=0,
            participant_count=1,
            occurred_at=datetime.utcnow(),
        )
        assert event.submitted_count == 0
        assert event.participant_count == 1
        # Must NOT have private fields
        assert not hasattr(event, "preferences")
        assert not hasattr(event, "individual_scores")
        assert not hasattr(event, "capsule")

    def test_scene_candidate_ready_fields(self) -> None:
        event = SceneCandidateReady(
            event_id="abc",
            scene_instance_id=uuid4(),
            candidate_count=3,
            occurred_at=datetime.utcnow(),
        )
        assert event.candidate_count == 3
        # Must NOT have private fields
        assert not hasattr(event, "evaluations")
        assert not hasattr(event, "individual_scores")

    def test_scene_voting_complete_fields(self) -> None:
        event = SceneVotingComplete(
            event_id="abc",
            scene_instance_id=uuid4(),
            vote_count=5,
            participant_count=5,
            occurred_at=datetime.utcnow(),
        )
        assert event.vote_count == 5
        # Must NOT have who voted for what
        assert not hasattr(event, "votes")
        assert not hasattr(event, "vote_details")

    def test_scene_completed_fields(self) -> None:
        result_id = uuid4()
        event = SceneCompleted(
            event_id="abc",
            scene_instance_id=uuid4(),
            public_result_id=result_id,
            participant_count=5,
            submitted_count=4,
            occurred_at=datetime.utcnow(),
        )
        assert event.public_result_id == result_id
        # Must NOT have private fields
        assert not hasattr(event, "summary_text")
        assert not hasattr(event, "preferences")

    def test_scene_cancelled_fields(self) -> None:
        event = SceneCancelled(
            event_id="abc",
            scene_instance_id=uuid4(),
            cancelled_by=uuid4(),
            occurred_at=datetime.utcnow(),
        )
        assert hasattr(event, "cancelled_by")
        assert not hasattr(event, "reason_text")
        assert not hasattr(event, "preferences")

    def test_scene_expired_fields(self) -> None:
        event = SceneExpired(
            event_id="abc",
            scene_instance_id=uuid4(),
            occurred_at=datetime.utcnow(),
        )
        assert not hasattr(event, "preferences")
        assert not hasattr(event, "capsule")

    def test_scene_failed_fields(self) -> None:
        event = SceneFailed(
            event_id="abc",
            scene_instance_id=uuid4(),
            reason_code="processing_failed",
            occurred_at=datetime.utcnow(),
        )
        assert event.reason_code == "processing_failed"
        # Must NOT have raw error message
        assert not hasattr(event, "error_message")
        assert not hasattr(event, "stack_trace")

    def test_scene_private_data_cleaned_fields(self) -> None:
        event = ScenePrivateDataCleaned(
            event_id="abc",
            scene_instance_id=uuid4(),
            submission_count=3,
            occurred_at=datetime.utcnow(),
        )
        assert event.submission_count == 3
        # Must NOT have any private data
        assert not hasattr(event, "payloads")
        assert not hasattr(event, "capsules")
        assert not hasattr(event, "preferences")

    def test_all_events_are_frozen(self) -> None:
        """All events should be frozen (immutable)."""
        events = [
            SceneInstanceCreated("a", uuid4(), "test", uuid4(), datetime.utcnow()),
            ScenePhaseChanged("a", uuid4(), "DRAFT", "INVITING", 0, 1, datetime.utcnow()),
            SceneCandidateReady("a", uuid4(), 3, datetime.utcnow()),
            SceneVotingComplete("a", uuid4(), 5, 5, datetime.utcnow()),
            SceneCompleted("a", uuid4(), None, 5, 4, datetime.utcnow()),
            SceneCancelled("a", uuid4(), uuid4(), datetime.utcnow()),
            SceneExpired("a", uuid4(), datetime.utcnow()),
            SceneFailed("a", uuid4(), "failed", datetime.utcnow()),
            ScenePrivateDataCleaned("a", uuid4(), 3, datetime.utcnow()),
        ]
        for event in events:
            # Frozen dataclasses should raise on attribute assignment.
            with pytest.raises(AttributeError):
                event.event_id = "modified"  # type: ignore[attr-defined]
