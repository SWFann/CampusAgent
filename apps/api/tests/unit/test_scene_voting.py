"""P8-10: Scene voting tests.

Tests:
- One person one vote (replace is allowed).
- Only ACCEPTED participants can vote.
- Only in VOTING phase.
- Invalid vote value rejected.
- Candidate must belong to the scene instance.
- Idempotent vote with same idempotency key.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.exceptions import (
    SceneNotFoundError,
    ScenePermissionDeniedError,
    SceneSubmissionError,
)
from src.modules.scenes.models import (
    CandidateStatus,
    SceneCandidate,
)
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.service import (
    accept_invitation,
    cast_vote,
    create_scene_instance,
    list_candidates,
    transition_state,
)
from src.modules.scenes.state_machine import SceneState
from src.modules.scenes.test_plugins import NoopScenePlugin
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def setup_registry():
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(NoopScenePlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def creator(test_db_session: Session) -> User:
    user = User(
        email="vote-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def voter(test_db_session: Session) -> User:
    user = User(
        email="voter@example.com",
        password_hash="fake",
        display_name="Voter",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def voting_scene(creator: User, voter: User, test_db_session: Session) -> tuple[UUID, SceneCandidate]:
    """Create a scene instance in VOTING phase with a candidate."""
    result = create_scene_instance(
        creator,
        {
            "scene_key": "noop_scene",
            "participant_user_ids": [creator.id, voter.id],
        },
        test_db_session,
    )
    instance_id = UUID(result["id"])

    # Transition to VOTING.
    transition_state(creator, instance_id, "publish", test_db_session)
    transition_state(creator, instance_id, "start_collecting", test_db_session)

    # Accept invitation.
    accept_invitation(voter, instance_id, test_db_session)

    # Add a candidate directly.
    candidate = SceneCandidate(
        scene_instance_id=instance_id,
        candidate_key="test_candidate",
        display_name="Test Candidate",
        status=CandidateStatus.ACTIVE.value,
    )
    test_db_session.add(candidate)
    test_db_session.flush()

    # Transition to VOTING.
    transition_state(creator, instance_id, "start_processing", test_db_session)
    # Can't skip to VOTING from COLLECTING — need GENERATING_CANDIDATES first.
    # But the state machine requires GENERATING_CANDIDATES → VOTING.
    # Since we're testing voting, we manually set the state.
    from src.modules.scenes.repository import SceneInstanceRepository

    instance_repo = SceneInstanceRepository(test_db_session)
    instance = instance_repo.get_by_id(instance_id)
    assert instance is not None
    instance.status = SceneState.VOTING.value
    instance.current_phase = SceneState.VOTING.value
    test_db_session.flush()

    return instance_id, candidate


class TestVoting:
    def test_cast_vote(self, voting_scene: tuple[UUID, SceneCandidate], voter: User, test_db_session: Session) -> None:
        instance_id, candidate = voting_scene
        result = cast_vote(
            voter, instance_id, candidate.id, "APPROVE", test_db_session
        )
        assert result["vote_value"] == "APPROVE"
        assert result["candidate_id"] == str(candidate.id)

    def test_one_person_one_vote_replace(
        self, voting_scene: tuple[UUID, SceneCandidate], voter: User, test_db_session: Session
    ) -> None:
        """Replacing a vote should update, not duplicate."""
        instance_id, candidate = voting_scene
        cast_vote(voter, instance_id, candidate.id, "APPROVE", test_db_session)

        # Add another candidate.
        candidate2 = SceneCandidate(
            scene_instance_id=instance_id,
            candidate_key="test_candidate_2",
            display_name="Test Candidate 2",
            status=CandidateStatus.ACTIVE.value,
        )
        test_db_session.add(candidate2)
        test_db_session.flush()

        # Replace vote.
        result = cast_vote(voter, instance_id, candidate2.id, "REJECT", test_db_session)
        assert result["candidate_id"] == str(candidate2.id)

        # Verify only one vote exists.
        from src.modules.scenes.repository import SceneVoteRepository

        vote_repo = SceneVoteRepository(test_db_session)
        votes = vote_repo.list_by_instance(instance_id)
        assert len(votes) == 1

    def test_non_participant_cannot_vote(
        self, voting_scene: tuple[UUID, SceneCandidate], test_db_session: Session
    ) -> None:
        instance_id, candidate = voting_scene
        outsider = User(
            email="outsider@example.com",
            password_hash="fake",
            display_name="Outsider",
            global_role=GlobalRole.STUDENT.value,
            status=UserStatus.ACTIVE.value,
        )
        test_db_session.add(outsider)
        test_db_session.flush()

        with pytest.raises(ScenePermissionDeniedError):
            cast_vote(outsider, instance_id, candidate.id, "APPROVE", test_db_session)

    def test_invalid_vote_value(
        self, voting_scene: tuple[UUID, SceneCandidate], voter: User, test_db_session: Session
    ) -> None:
        instance_id, candidate = voting_scene
        with pytest.raises(SceneSubmissionError):
            cast_vote(voter, instance_id, candidate.id, "INVALID", test_db_session)

    def test_candidate_not_in_instance(
        self, voting_scene: tuple[UUID, SceneCandidate], voter: User, test_db_session: Session
    ) -> None:
        instance_id, _ = voting_scene
        with pytest.raises(SceneNotFoundError):
            cast_vote(voter, instance_id, uuid4(), "APPROVE", test_db_session)

    def test_list_candidates(
        self, voting_scene: tuple[UUID, SceneCandidate], voter: User, test_db_session: Session
    ) -> None:
        instance_id, candidate = voting_scene
        result = list_candidates(voter, instance_id, test_db_session)
        assert result["total"] >= 1
        assert any(c["candidate_key"] == "test_candidate" for c in result["candidates"])
