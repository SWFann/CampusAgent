"""P8-12: Scene cleanup tests.

Tests:
- Immediate cleanup clears encrypted_payload and capsule.
- Cleanup is idempotent (running twice is safe).
- After cleanup, API cannot read private payload.
- cleanup_expired_submissions catches expired submissions.
- Cleanup event is published with only count (no private data).
"""
from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.cleanup import (
    cleanup_expired_submissions,
    cleanup_private_data,
)
from src.modules.scenes.events import ScenePrivateDataCleaned
from src.modules.scenes.models import PrivateSubmission
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import PrivateSubmissionRepository
from src.modules.scenes.service import (
    create_scene_instance,
    submit_private_preferences,
    transition_state,
)
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
def scene_with_submission(creator: User, test_db_session: Session) -> UUID:
    """Create a scene with a private submission."""
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

    return instance_id


class TestCleanup:
    def test_immediate_cleanup_clears_payload(
        self, scene_with_submission: UUID, test_db_session: Session
    ) -> None:
        """cleanup_private_data should clear encrypted_payload and capsule."""
        count = cleanup_private_data(scene_with_submission, test_db_session)

        assert count == 1

        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(scene_with_submission)
        for sub in submissions:
            assert sub.encrypted_payload == ""
            assert sub.capsule_json is None
            assert sub.deleted_at is not None

    def test_cleanup_is_idempotent(
        self, scene_with_submission: UUID, test_db_session: Session
    ) -> None:
        """Running cleanup twice should not raise and should return 0 the second time."""
        count1 = cleanup_private_data(scene_with_submission, test_db_session)
        assert count1 == 1

        count2 = cleanup_private_data(scene_with_submission, test_db_session)
        assert count2 == 0  # already cleaned

    def test_cleanup_publishes_event(
        self, scene_with_submission: UUID, test_db_session: Session
    ) -> None:
        """Cleanup should publish a ScenePrivateDataCleaned event."""
        events: list[ScenePrivateDataCleaned] = []

        from src.events.bus import default_event_bus

        class CaptureHandler:
            def handle(self, event: ScenePrivateDataCleaned) -> None:
                events.append(event)

        default_event_bus.subscribe(ScenePrivateDataCleaned, CaptureHandler())  # type: ignore[arg-type]

        cleanup_private_data(scene_with_submission, test_db_session)

        assert len(events) == 1
        event = events[0]
        assert event.submission_count == 1
        assert event.scene_instance_id == scene_with_submission
        # Event must not contain private data.
        assert not hasattr(event, "encrypted_payload")
        assert not hasattr(event, "capsule")
        assert not hasattr(event, "preferences")

    def test_after_cleanup_api_cannot_read_payload(
        self, scene_with_submission: UUID, creator: User, test_db_session: Session
    ) -> None:
        """After cleanup, the submission status should show no active submission."""
        from src.modules.scenes.service import get_submission_status

        cleanup_private_data(scene_with_submission, test_db_session)

        status = get_submission_status(creator, scene_with_submission, test_db_session)
        assert status["has_submitted"] is False

    def test_cleanup_expired_submissions(
        self, creator: User, test_db_session: Session
    ) -> None:
        """Expired submissions should be cleaned up by the periodic job."""
        from src.db.time import utc_now

        result = create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id]},
            test_db_session,
        )
        instance_id = UUID(result["id"])

        # Manually create an expired submission.
        sub = PrivateSubmission(
            scene_instance_id=instance_id,
            user_id=creator.id,
            encrypted_payload="encrypted_data",
            capsule_json='{"hard_constraints": {}}',
            expires_at=utc_now() - timedelta(hours=1),  # expired
        )
        test_db_session.add(sub)
        test_db_session.flush()

        count = cleanup_expired_submissions(test_db_session)
        assert count == 1

        # Verify it's cleaned.
        test_db_session.refresh(sub)
        assert sub.encrypted_payload == ""
        assert sub.deleted_at is not None
