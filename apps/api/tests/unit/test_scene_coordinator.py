"""P8-08: Scene coordinator tests.

Tests:
- Coordinator generates candidates from capsules.
- Coordinator stores public candidates.
- Coordinator stores public result.
- Coordinator triggers cleanup after generation.
- Coordinator transitions to FAILED on plugin error.
- Individual evaluation results are never persisted.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.coordinator import run_generation_phase
from src.modules.scenes.exceptions import ScenePluginError
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import (
    PrivateSubmissionRepository,
    SceneCandidateRepository,
    SceneResultRepository,
)
from src.modules.scenes.service import (
    accept_invitation,
    create_scene_instance,
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
        email="coord-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def participant(test_db_session: Session) -> User:
    user = User(
        email="coord-participant@example.com",
        password_hash="fake",
        display_name="Participant",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def generating_scene(
    creator: User, participant: User, test_db_session: Session
) -> UUID:
    """Create a scene instance in GENERATING_CANDIDATES with submissions."""
    result = create_scene_instance(
        creator,
        {
            "scene_key": "noop_scene",
            "participant_user_ids": [creator.id, participant.id],
        },
        test_db_session,
    )
    instance_id = UUID(result["id"])

    # Transition to COLLECTING_PRIVATE_INPUT.
    transition_state(creator, instance_id, "publish", test_db_session)
    transition_state(creator, instance_id, "start_collecting", test_db_session)

    # Accept invitation.
    accept_invitation(participant, instance_id, test_db_session)

    # Submit preferences.
    submit_private_preferences(
        creator, instance_id, {"require_a": True, "prefer_b": 2}, test_db_session
    )
    submit_private_preferences(
        participant, instance_id, {"require_c": False, "prefer_d": 1}, test_db_session
    )

    # Transition to GENERATING_CANDIDATES.
    transition_state(creator, instance_id, "start_processing", test_db_session)

    return instance_id


class TestCoordinator:
    def test_generates_candidates(
        self, generating_scene: UUID, test_db_session: Session
    ) -> None:
        """Coordinator should generate public candidates."""
        result = run_generation_phase(generating_scene, test_db_session)

        assert result["candidate_count"] > 0
        assert result["submitted_count"] == 2
        assert "result_id" in result

    def test_stores_public_candidates(
        self, generating_scene: UUID, test_db_session: Session
    ) -> None:
        """Candidates should be persisted with only public data."""
        run_generation_phase(generating_scene, test_db_session)

        cand_repo = SceneCandidateRepository(test_db_session)
        candidates = cand_repo.list_by_instance(generating_scene)
        assert len(candidates) > 0

        for c in candidates:
            # Only public data — no private scores or preferences.
            assert c.candidate_key is not None
            assert c.display_name is not None
            assert c.aggregate_score is not None

    def test_stores_public_result(
        self, generating_scene: UUID, test_db_session: Session
    ) -> None:
        """A public result should be stored."""
        run_generation_phase(generating_scene, test_db_session)

        result_repo = SceneResultRepository(test_db_session)
        result = result_repo.get_by_instance(generating_scene)
        assert result is not None
        assert result.public_summary is not None
        assert result.participant_count == 2
        assert result.submitted_count == 2

    def test_cleanup_after_generation(
        self, generating_scene: UUID, test_db_session: Session
    ) -> None:
        """Private data should be cleaned up after generation."""
        run_generation_phase(generating_scene, test_db_session)

        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(generating_scene)
        for sub in submissions:
            # After cleanup, encrypted_payload should be empty.
            assert sub.encrypted_payload == ""
            assert sub.capsule_json is None
            assert sub.deleted_at is not None

    def test_no_individual_scores_persisted(
        self, generating_scene: UUID, test_db_session: Session
    ) -> None:
        """Individual evaluation results should never be persisted."""
        run_generation_phase(generating_scene, test_db_session)

        # Check that no individual scores are in the database.
        cand_repo = SceneCandidateRepository(test_db_session)
        candidates = cand_repo.list_by_instance(generating_scene)
        for c in candidates:
            # public_reason is aggregate-level, not individual.
            if c.public_reason:
                assert "Individual" not in c.public_reason
                assert "individual" not in c.public_reason.lower()

    def test_wrong_state_raises(
        self, creator: User, participant: User, test_db_session: Session
    ) -> None:
        """Running generation outside GENERATING_CANDIDATES should fail."""
        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])

        from src.modules.scenes.exceptions import SceneStateTransitionError

        with pytest.raises(SceneStateTransitionError):
            run_generation_phase(instance_id, test_db_session)

    def test_failed_generation_transitions_to_failed(
        self, creator: User, test_db_session: Session
    ) -> None:
        """If the plugin fails, the scene should transition to FAILED."""
        # Register a failing plugin.
        reset_scene_registry()
        registry = get_scene_registry()

        class FailingPlugin(NoopScenePlugin):
            scene_key = "noop_scene"  # same key to reuse
            def generate_candidates(self, capsules: list, public_context: Any, facade: Any) -> list:
                raise RuntimeError("Plugin failure")

        registry.register(FailingPlugin())

        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        submit_private_preferences(
            creator, instance_id, {"require_a": True}, test_db_session
        )
        transition_state(creator, instance_id, "start_processing", test_db_session)

        with pytest.raises(ScenePluginError):
            run_generation_phase(instance_id, test_db_session)

        # Check that the scene is now FAILED.
        from src.modules.scenes.repository import SceneInstanceRepository

        instance = SceneInstanceRepository(test_db_session).get_by_id(instance_id)
        assert instance is not None
        assert instance.status == SceneState.FAILED.value
