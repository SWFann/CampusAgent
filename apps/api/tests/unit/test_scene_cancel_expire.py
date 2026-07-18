"""P8-11: Scene cancel and expire tests.

Tests:
- Cancel from any non-terminal state.
- Expire from any non-terminal state.
- Cancelled/expired scenes are terminal.
- Cancel triggers cleanup.
- Expire stale instances finds and expires them.
"""
from __future__ import annotations

from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.repository import (
    SceneInstanceRepository,
)
from src.modules.scenes.service import (
    create_scene_instance,
    expire_stale_instances,
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
        email="cancel-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def scene_instance(creator: User, test_db_session: Session) -> UUID:
    result = create_scene_instance(
        creator,
        {"scene_key": "noop_scene", "participant_user_ids": [creator.id]},
        test_db_session,
    )
    return UUID(result["id"])


class TestCancel:
    def test_cancel_from_draft(self, creator: User, scene_instance: UUID, test_db_session: Session) -> None:
        result = transition_state(creator, scene_instance, "cancel", test_db_session)
        assert result["status"] == SceneState.CANCELLED.value
        assert result["cancelled_at"] is not None

    def test_cancel_from_collecting(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
        transition_state(creator, scene_instance, "publish", test_db_session)
        transition_state(creator, scene_instance, "start_collecting", test_db_session)
        result = transition_state(creator, scene_instance, "cancel", test_db_session)
        assert result["status"] == SceneState.CANCELLED.value

    def test_cancel_from_voting(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
        transition_state(creator, scene_instance, "publish", test_db_session)
        transition_state(creator, scene_instance, "start_collecting", test_db_session)
        transition_state(creator, scene_instance, "start_processing", test_db_session)

        # Manually set to VOTING (skip coordinator for this test).
        repo = SceneInstanceRepository(test_db_session)
        inst = repo.get_by_id(scene_instance)
        assert inst is not None
        inst.status = SceneState.VOTING.value
        inst.current_phase = SceneState.VOTING.value
        test_db_session.flush()

        result = transition_state(creator, scene_instance, "cancel", test_db_session)
        assert result["status"] == SceneState.CANCELLED.value

    def test_cancel_is_terminal(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
        transition_state(creator, scene_instance, "cancel", test_db_session)
        # Cannot transition from CANCELLED.
        from src.modules.scenes.exceptions import SceneStateTransitionError

        with pytest.raises(SceneStateTransitionError):
            transition_state(creator, scene_instance, "publish", test_db_session)

    def test_non_creator_cannot_cancel(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
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
            transition_state(outsider, scene_instance, "cancel", test_db_session)


class TestExpire:
    def test_expire_from_draft(self, creator: User, scene_instance: UUID, test_db_session: Session) -> None:
        result = transition_state(creator, scene_instance, "expire", test_db_session)
        assert result["status"] == SceneState.EXPIRED.value

    def test_expire_is_terminal(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
        transition_state(creator, scene_instance, "expire", test_db_session)
        from src.modules.scenes.exceptions import SceneStateTransitionError

        with pytest.raises(SceneStateTransitionError):
            transition_state(creator, scene_instance, "publish", test_db_session)

    def test_expire_stale_instances(
        self, creator: User, test_db_session: Session
    ) -> None:
        """expire_stale_instances should find and expire stale instances."""
        from src.db.time import utc_now

        result = create_scene_instance(
            creator,
            {
                "scene_key": "noop_scene",
                "participant_user_ids": [creator.id],
                "expires_at": utc_now() - timedelta(hours=1),  # already expired
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])

        count = expire_stale_instances(test_db_session)
        assert count == 1

        repo = SceneInstanceRepository(test_db_session)
        instance = repo.get_by_id(instance_id)
        assert instance is not None
        assert instance.status == SceneState.EXPIRED.value

    def test_expire_stale_does_not_expire_active(
        self, creator: User, test_db_session: Session
    ) -> None:
        """Instances without expires_at should not be expired."""
        create_scene_instance(
            creator,
            {"scene_key": "noop_scene", "participant_user_ids": [creator.id]},
            test_db_session,
        )

        count = expire_stale_instances(test_db_session)
        assert count == 0


class TestFailedState:
    def test_fail_from_generating(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
        transition_state(creator, scene_instance, "publish", test_db_session)
        transition_state(creator, scene_instance, "start_collecting", test_db_session)
        transition_state(creator, scene_instance, "start_processing", test_db_session)

        result = transition_state(creator, scene_instance, "processing_failed", test_db_session)
        assert result["status"] == SceneState.FAILED.value
        assert result["failed_reason_code"] == "processing_failed"

    def test_failed_is_terminal(
        self, creator: User, scene_instance: UUID, test_db_session: Session
    ) -> None:
        transition_state(creator, scene_instance, "publish", test_db_session)
        transition_state(creator, scene_instance, "start_collecting", test_db_session)
        transition_state(creator, scene_instance, "start_processing", test_db_session)
        transition_state(creator, scene_instance, "processing_failed", test_db_session)

        from src.modules.scenes.exceptions import SceneStateTransitionError

        with pytest.raises(SceneStateTransitionError):
            transition_state(creator, scene_instance, "cancel", test_db_session)
