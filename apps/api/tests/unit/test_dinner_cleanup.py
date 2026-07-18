"""P9-15: Cleanup validation tests.

Tests cover (per P9 guide §17):
- After generation: raw input, capsule, private evaluation, model response are purged.
- DB query proves cleanup.
- API cannot read private data after cleanup.
- Cleanup is idempotent (repeated execution is safe).
"""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.cleanup import (
    cleanup_instance_on_terminal,
    cleanup_private_data,
)
from src.modules.scenes.coordinator import run_generation_phase
from src.modules.scenes.models import PrivateSubmission
from src.modules.scenes.plugins.dorm_dinner.plugin import DormDinnerPlugin
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import PrivateSubmissionRepository
from src.modules.scenes.service import (
    accept_invitation,
    create_scene_instance,
    get_submission_status,
    submit_private_preferences,
    transition_state,
)
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def setup_registry():
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(DormDinnerPlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def creator(test_db_session: Session) -> User:
    user = User(
        email="cleanup-creator@example.com",
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
        email="cleanup-p1@example.com",
        password_hash="fake",
        display_name="P1",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


def _make_prefs(**kwargs) -> dict:
    prefs = {
        "budget_min": 20,
        "budget_max": 50,
        "cuisine_preferences": ["sichuan"],
        "dietary_restrictions": ["none"],
        "distance_preference": "moderate",
        "available_time": ["dinner"],
        "environment_preference": "moderate",
        "notes": "secret cleanup test note",
    }
    prefs.update(kwargs)
    return prefs


class TestCleanupAfterGeneration:
    """Tests for cleanup after the generation phase."""

    def test_encrypted_payload_purged(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """After generation, encrypted_payload is empty."""
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
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)
        submit_private_preferences(participant1, instance_id, _make_prefs(), test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        # Verify encrypted_payload is empty.
        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.encrypted_payload == ""

    def test_capsule_purged(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """After generation, capsule_json is None."""
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
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)
        submit_private_preferences(participant1, instance_id, _make_prefs(), test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.capsule_json is None

    def test_deleted_at_set(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """After generation, deleted_at is set."""
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
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)
        submit_private_preferences(participant1, instance_id, _make_prefs(), test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.deleted_at is not None

    def test_raw_text_not_in_db(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """After cleanup, raw preference text is not in the database."""
        secret_note = "unique secret note for db search test 12345"
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
            _make_prefs(notes=secret_note),
            test_db_session,
        )
        submit_private_preferences(participant1, instance_id, _make_prefs(), test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        # Search all private submissions for the secret note text.
        all_subs = test_db_session.query(PrivateSubmission).filter(
            PrivateSubmission.scene_instance_id == instance_id,
        ).all()
        for sub in all_subs:
            assert secret_note not in (sub.encrypted_payload or "")
            assert secret_note not in (sub.capsule_json or "")
            assert secret_note not in (sub.payload_hash or "")


class TestCleanupIdempotent:
    """Tests that cleanup is idempotent (safe to run multiple times)."""

    def test_double_cleanup_safe(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Running cleanup twice is safe and doesn't error."""
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
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        # First cleanup (already done by coordinator, but explicit).
        _count1 = cleanup_private_data(instance_id, test_db_session)
        # Second cleanup.
        count2 = cleanup_private_data(instance_id, test_db_session)

        # Second cleanup should find 0 submissions to purge (already purged).
        assert count2 == 0

    def test_cleanup_on_cancel(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """Cleanup on cancel purges private data."""
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
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)

        transition_state(creator, instance_id, "cancel", test_db_session)
        count = cleanup_instance_on_terminal(instance_id, test_db_session)
        assert count >= 1

        # Verify data is purged.
        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            assert sub.encrypted_payload == ""
            assert sub.deleted_at is not None


class TestSubmissionStatusAfterCleanup:
    """Tests that the API cannot read private data after cleanup."""

    def test_submission_status_safe_after_cleanup(
        self,
        creator: User,
        participant1: User,
        test_db_session: Session,
    ) -> None:
        """get_submission_status returns no raw content after cleanup."""
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
            _make_prefs(notes="secret status test"),
            test_db_session,
        )

        # Before cleanup: has_submitted should be True.
        status = get_submission_status(creator, instance_id, test_db_session)
        assert status["has_submitted"] is True

        # Cleanup.
        cleanup_private_data(instance_id, test_db_session)

        # After cleanup: status should not contain raw content.
        status = get_submission_status(creator, instance_id, test_db_session)
        assert "notes" not in status
        assert "preferences" not in status
        assert "secret status test" not in str(status)
