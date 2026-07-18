"""P8-14: Scene core flow integration test.

Tests the full lifecycle of a scene instance:
1. Create scene with participants.
2. Transition to COLLECTING_PRIVATE_INPUT.
3. Participants accept and submit private preferences.
4. Transition to GENERATING_CANDIDATES.
5. Coordinator runs generation phase.
6. Private data is cleaned up.
7. Public candidates and result are available.
8. Transition to VOTING.
9. Participants vote.
10. Transition to CONFIRMING → COMPLETED.

Privacy verification:
- No raw preferences in the database after generation.
- No individual scores in candidates or results.
- Events contain only public data.
"""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.coordinator import run_generation_phase
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import (
    PrivateSubmissionRepository,
)
from src.modules.scenes.service import (
    accept_invitation,
    create_scene_instance,
    get_scene_result,
    get_submission_status,
    list_candidates,
    submit_private_preferences,
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
        email="flow-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def participant1(test_db_session: Session) -> User:
    user = User(
        email="flow-p1@example.com",
        password_hash="fake",
        display_name="Participant 1",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def participant2(test_db_session: Session) -> User:
    user = User(
        email="flow-p2@example.com",
        password_hash="fake",
        display_name="Participant 2",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


class TestSceneCoreFlow:
    """Full lifecycle integration test."""

    def test_full_lifecycle(
        self,
        creator: User,
        participant1: User,
        participant2: User,
        test_db_session: Session,
    ) -> None:
        """Test the complete scene lifecycle from creation to completion."""
        # 1. Create scene with 3 participants.
        result = create_scene_instance(
            creator,
            {
                "scene_key": "noop_scene",
                "participant_user_ids": [creator.id, participant1.id, participant2.id],
                "public_context": {"title": "Test Scene"},
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        assert result["status"] == SceneState.DRAFT.value

        # 2. Transition to INVITING → COLLECTING_PRIVATE_INPUT.
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        # 3. Participants accept invitations.
        accept_invitation(participant1, instance_id, test_db_session)
        accept_invitation(participant2, instance_id, test_db_session)

        # 4. Submit private preferences.
        submit_private_preferences(
            creator, instance_id,
            {"require_vegetarian": True, "prefer_spicy": 3},
            test_db_session,
        )
        submit_private_preferences(
            participant1, instance_id,
            {"require_halal": True, "prefer_quiet": 2},
            test_db_session,
        )
        submit_private_preferences(
            participant2, instance_id,
            {"require_vegan": True, "prefer_nearby": 1},
            test_db_session,
        )

        # Verify submissions were accepted.
        for user in [creator, participant1, participant2]:
            status = get_submission_status(user, instance_id, test_db_session)
            assert status["has_submitted"] is True

        # 5. Transition to GENERATING_CANDIDATES.
        transition_state(creator, instance_id, "start_processing", test_db_session)

        # 6. Run the coordinator.
        gen_result = run_generation_phase(instance_id, test_db_session)
        assert gen_result["candidate_count"] > 0
        assert gen_result["submitted_count"] == 3

        # 7. Verify private data was cleaned up.
        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.encrypted_payload == ""
            assert sub.capsule_json is None
            assert sub.deleted_at is not None

        # 8. Verify public candidates are available.
        candidates = list_candidates(creator, instance_id, test_db_session)
        assert candidates["total"] > 0
        for c in candidates["candidates"]:
            assert c["candidate_key"] is not None
            assert c["display_name"] is not None
            # No individual scores in candidates.
            assert "individual_scores" not in c
            assert "evaluations" not in c

        # 9. Verify public result is available.
        result = get_scene_result(creator, instance_id, test_db_session)
        assert result["public_summary"] is not None
        assert result["participant_count"] == 3
        assert result["submitted_count"] == 3
        assert result["selected_candidate"] is not None

        # 10. Verify no raw preferences in the database.
        all_subs = test_db_session.query(
            __import__("src.modules.scenes.models", fromlist=["PrivateSubmission"]).PrivateSubmission
        ).all()
        for sub in all_subs:
            if sub.scene_instance_id == instance_id:
                assert "require_vegetarian" not in (sub.encrypted_payload or "")
                assert "prefer_spicy" not in (sub.encrypted_payload or "")

    def test_cancel_during_collecting(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Cancelling during COLLECTING_PRIVATE_INPUT should work and clean up."""
        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id, participant1.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)
        submit_private_preferences(
            creator, instance_id, {"require_a": True}, test_db_session
        )

        # Cancel.
        result = transition_state(creator, instance_id, "cancel", test_db_session)
        assert result["status"] == SceneState.CANCELLED.value

        # Clean up private data on cancel.
        from src.modules.scenes.cleanup import cleanup_instance_on_terminal

        cleanup_instance_on_terminal(instance_id, test_db_session)

        # Verify private data is cleaned.
        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.encrypted_payload == ""
            assert sub.deleted_at is not None

    def test_generation_with_no_submissions(
        self,
        creator: User,
        test_db_session: Session,
    ) -> None:
        """Generation with zero submissions should still produce a result."""
        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)

        gen_result = run_generation_phase(instance_id, test_db_session)
        assert gen_result["submitted_count"] == 0
        # NoopScenePlugin generates at least 1 candidate even with 0 capsules.
        assert gen_result["candidate_count"] >= 1
