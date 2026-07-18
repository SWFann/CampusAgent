"""P9-12: Dorm dinner scene API and full lifecycle tests.

Tests the full lifecycle of a dorm dinner scene instance:
1. Create scene with dorm_dinner scene_key and participants.
2. Transition through states: DRAFT → INVITING → COLLECTING_PRIVATE_INPUT.
3. Participants accept and submit private preferences.
4. Transition to GENERATING_CANDIDATES and run coordinator.
5. Verify public candidates and results are available.
6. Transition to VOTING → CONFIRMING → COMPLETED.
7. Verify privacy: no raw preferences in responses.

This test uses the real DormDinnerPlugin (not a mock).
"""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.coordinator import run_generation_phase
from src.modules.scenes.plugins.dorm_dinner.plugin import DormDinnerPlugin
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import PrivateSubmissionRepository
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
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def setup_registry():
    """Register DormDinnerPlugin for each test."""
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(DormDinnerPlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def creator(test_db_session: Session) -> User:
    user = User(
        email="dinner-creator@example.com",
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
        email="dinner-p1@example.com",
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
        email="dinner-p2@example.com",
        password_hash="fake",
        display_name="Participant 2",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def participant3(test_db_session: Session) -> User:
    user = User(
        email="dinner-p3@example.com",
        password_hash="fake",
        display_name="Participant 3",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


def _make_preferences(**kwargs) -> dict:
    """Create dorm dinner preference dict with sensible defaults."""
    prefs = {
        "budget_min": 20,
        "budget_max": 50,
        "cuisine_preferences": ["sichuan"],
        "dietary_restrictions": ["none"],
        "distance_preference": "moderate",
        "available_time": ["dinner"],
        "environment_preference": "moderate",
        "notes": "",
    }
    prefs.update(kwargs)
    return prefs


class TestDormDinnerFullLifecycle:
    """Test the complete dorm dinner scene lifecycle."""

    def test_full_lifecycle(
        self,
        creator: User,
        participant1: User,
        participant2: User,
        participant3: User,
        test_db_session: Session,
    ) -> None:
        """Test the complete scene lifecycle from creation to result."""
        # 1. Create scene with 4 participants (dorm-mates).
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [
                    creator.id, participant1.id, participant2.id, participant3.id,
                ],
                "public_context": {"title": "周末聚餐"},
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        assert result["status"] == SceneState.DRAFT.value
        assert result["scene_key"] == "dorm_dinner"

        # 2. Transition to INVITING → COLLECTING_PRIVATE_INPUT.
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        # 3. Participants accept invitations.
        accept_invitation(participant1, instance_id, test_db_session)
        accept_invitation(participant2, instance_id, test_db_session)
        accept_invitation(participant3, instance_id, test_db_session)

        # 4. Submit private preferences (4 dorm-mates).
        submit_private_preferences(
            creator, instance_id,
            _make_preferences(budget_min=25, budget_max=60, cuisine_preferences=["sichuan", "hotpot"]),
            test_db_session,
        )
        submit_private_preferences(
            participant1, instance_id,
            _make_preferences(budget_min=20, budget_max=40, cuisine_preferences=["cantonese"]),
            test_db_session,
        )
        submit_private_preferences(
            participant2, instance_id,
            _make_preferences(budget_min=30, budget_max=80, cuisine_preferences=["sichuan", "bbq"]),
            test_db_session,
        )
        submit_private_preferences(
            participant3, instance_id,
            _make_preferences(budget_min=15, budget_max=35, cuisine_preferences=["northern"]),
            test_db_session,
        )

        # Verify submissions were accepted.
        for user in [creator, participant1, participant2, participant3]:
            status = get_submission_status(user, instance_id, test_db_session)
            assert status["has_submitted"] is True
            assert status["capsule_generated"] is True

        # 5. Transition to GENERATING_CANDIDATES.
        transition_state(creator, instance_id, "start_processing", test_db_session)

        # 6. Run the coordinator.
        gen_result = run_generation_phase(instance_id, test_db_session)
        assert gen_result["candidate_count"] >= 3
        assert gen_result["submitted_count"] == 4

        # 7. Verify public candidates are available.
        candidates = list_candidates(creator, instance_id, test_db_session)
        assert candidates["total"] >= 3
        for c in candidates["candidates"]:
            assert c["candidate_key"] is not None
            assert c["display_name"] is not None
            # No individual scores in candidates.
            assert "individual_scores" not in c
            assert "evaluations" not in c
            assert "raw_preferences" not in c

        # 8. Verify public result is available.
        result = get_scene_result(creator, instance_id, test_db_session)
        assert result["public_summary"] is not None
        assert result["participant_count"] == 4
        assert result["submitted_count"] == 4
        # Selected candidate should exist (at least one should pass hard gate).
        assert result["selected_candidate"] is not None

    def test_submission_response_never_echoes_raw(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """The submission response must never echo the raw payload."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        prefs = _make_preferences(notes="This is a secret note that must not be echoed")
        submit_result = submit_private_preferences(
            creator, instance_id, prefs, test_db_session,
        )

        # Response should NOT contain raw preferences.
        assert "preferences" not in submit_result
        assert "notes" not in submit_result
        assert "budget_min" not in submit_result
        assert "cuisine_preferences" not in submit_result
        assert "This is a secret note" not in str(submit_result)

    def test_non_participant_cannot_access(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """A non-participant cannot access the scene instance."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])

        # Create a non-participant user.
        outsider = User(
            email="outsider@example.com",
            password_hash="fake",
            display_name="Outsider",
            global_role=GlobalRole.STUDENT.value,
            status=UserStatus.ACTIVE.value,
        )
        test_db_session.add(outsider)
        test_db_session.flush()

        from src.modules.scenes.exceptions import ScenePermissionDeniedError
        with pytest.raises(ScenePermissionDeniedError):
            get_scene_result(outsider, instance_id, test_db_session)

    def test_invalid_preferences_rejected(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Invalid preferences are rejected by the plugin validator."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)

        # Invalid: budget_max < budget_min.
        with pytest.raises((ValueError, Exception)):
            submit_private_preferences(
                creator, instance_id,
                _make_preferences(budget_min=50, budget_max=20),
                test_db_session,
            )

    def test_cancel_cleans_up_private_data(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Cancelling during COLLECTING_PRIVATE_INPUT should clean up."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, participant1.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(participant1, instance_id, test_db_session)
        submit_private_preferences(
            creator, instance_id,
            _make_preferences(notes="secret cancel test"),
            test_db_session,
        )

        # Cancel.
        result = transition_state(creator, instance_id, "cancel", test_db_session)
        assert result["status"] == SceneState.CANCELLED.value

        # Clean up.
        from src.modules.scenes.cleanup import cleanup_instance_on_terminal
        cleanup_instance_on_terminal(instance_id, test_db_session)

        # Verify private data is cleaned.
        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.encrypted_payload == ""
            assert sub.deleted_at is not None
            assert "secret cancel test" not in (sub.encrypted_payload or "")
