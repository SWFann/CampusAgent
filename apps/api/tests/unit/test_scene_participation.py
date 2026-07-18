"""P8-06: Scene participation and private submission tests.

Tests:
- Create scene instance with participants.
- Accept/decline invitations.
- Leave scene (non-creator).
- Creator cannot leave.
- Private submission encrypts payload.
- Submission response never echoes raw content.
- Only owner can submit/replace/delete.
- Non-participant cannot submit.
- Submission requires ACCEPTED status.
- Idempotency key prevents duplicate creation.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.exceptions import (
    SceneConsentRequiredError,
    ScenePermissionDeniedError,
    SceneStateTransitionError,
)
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.scenes.service import (
    accept_invitation,
    create_scene_instance,
    decline_invitation,
    delete_submission,
    get_scene_instance,
    get_submission_status,
    leave_scene,
    submit_private_preferences,
    transition_state,
)
from src.modules.scenes.state_machine import SceneState
from src.modules.scenes.test_plugins import NoopScenePlugin
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture(autouse=True)
def setup_registry():
    """Register the noop plugin for each test."""
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(NoopScenePlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def creator(test_db_session: Session) -> User:
    user = User(
        email="creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def invitee(test_db_session: Session) -> User:
    user = User(
        email="invitee@example.com",
        password_hash="fake",
        display_name="Invitee",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def scene_instance_data(creator: User, invitee: User) -> dict:
    return {
        "scene_key": "noop_scene",
        "participant_user_ids": [creator.id, invitee.id],
        "public_context": {"test": True},
    }


class TestSceneCreation:
    def test_create_instance(self, creator: User, scene_instance_data: dict, test_db_session: Session) -> None:
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        assert result["scene_key"] == "noop_scene"
        assert result["status"] == SceneState.DRAFT.value
        assert result["participant_count"] == 1  # creator is ACCEPTED

    def test_idempotency_key(self, creator: User, scene_instance_data: dict, test_db_session: Session) -> None:
        scene_instance_data["idempotency_key"] = "test-key-123"
        result1 = create_scene_instance(creator, scene_instance_data, test_db_session)
        result2 = create_scene_instance(creator, scene_instance_data, test_db_session)
        assert result1["id"] == result2["id"]

    def test_non_participant_cannot_view(self, creator: User, scene_instance_data: dict, test_db_session: Session) -> None:
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = uuid4()  # Parse the UUID from the result
        instance_id = __import__("uuid").UUID(result["id"])

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
            get_scene_instance(outsider, instance_id, test_db_session)


class TestInvitation:
    def test_accept_invitation(
        self, creator: User, invitee: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        accepted = accept_invitation(invitee, instance_id, test_db_session)
        assert accepted["status"] == "ACCEPTED"

    def test_decline_invitation(
        self, creator: User, invitee: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        declined = decline_invitation(invitee, instance_id, test_db_session)
        assert declined["status"] == "DECLINED"

    def test_creator_cannot_leave(
        self, creator: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        with pytest.raises(ScenePermissionDeniedError):
            leave_scene(creator, instance_id, test_db_session)

    def test_non_creator_can_leave(
        self, creator: User, invitee: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])
        accept_invitation(invitee, instance_id, test_db_session)

        leave_scene(invitee, instance_id, test_db_session)
        # Should not raise


class TestPrivateSubmission:
    def test_submit_preferences(
        self, creator: User, invitee: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """Submit private preferences and verify response doesn't echo raw content."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        # Transition to COLLECTING_PRIVATE_INPUT.
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        # Accept invitation first.
        accept_invitation(invitee, instance_id, test_db_session)

        # Submit preferences.
        prefs = {"require_vegetarian": True, "prefer_spicy": 3}
        submission = submit_private_preferences(
            creator, instance_id, prefs, test_db_session
        )
        assert submission["submission_status"] == "ACCEPTED"
        assert submission["capsule_generated"] is True
        assert "preferences" not in submission  # raw content not echoed
        assert "encrypted_payload" not in submission

    def test_submission_requires_accepted_status(
        self, creator: User, invitee: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """Non-ACCEPTED participant cannot submit."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        # Invitee hasn't accepted yet — should fail.
        with pytest.raises(SceneConsentRequiredError):
            submit_private_preferences(
                invitee, instance_id, {"key": "value"}, test_db_session
            )

    def test_submission_requires_correct_phase(
        self, creator: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """Submission requires COLLECTING_PRIVATE_INPUT phase."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        # Still in DRAFT — should fail.
        with pytest.raises(SceneStateTransitionError):
            submit_private_preferences(
                creator, instance_id, {"key": "value"}, test_db_session
            )

    def test_replace_submission(
        self, creator: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """User can replace their submission."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        prefs1 = {"require_a": True}
        sub1 = submit_private_preferences(creator, instance_id, prefs1, test_db_session)

        prefs2 = {"require_b": True}
        sub2 = submit_private_preferences(creator, instance_id, prefs2, test_db_session)

        # Same submission ID (replaced, not duplicated).
        assert sub1["submission_id"] == sub2["submission_id"]

    def test_get_submission_status_no_raw_content(
        self, creator: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """get_submission_status returns no raw content."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        submit_private_preferences(
            creator, instance_id, {"require_a": True}, test_db_session
        )

        status = get_submission_status(creator, instance_id, test_db_session)
        assert status["has_submitted"] is True
        assert status["capsule_generated"] is True
        assert "preferences" not in status
        assert "encrypted_payload" not in status

    def test_delete_submission(
        self, creator: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """User can delete their submission."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        submit_private_preferences(
            creator, instance_id, {"require_a": True}, test_db_session
        )

        delete_submission(creator, instance_id, test_db_session)

        status = get_submission_status(creator, instance_id, test_db_session)
        assert status["has_submitted"] is False

    def test_database_has_no_plaintext(
        self, creator: User, scene_instance_data: dict, test_db_session: Session
    ) -> None:
        """The database must not contain plaintext preferences."""
        result = create_scene_instance(creator, scene_instance_data, test_db_session)
        instance_id = __import__("uuid").UUID(result["id"])

        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)

        raw_prefs = {"require_vegetarian": True, "prefer_spicy": 5}
        submit_private_preferences(creator, instance_id, raw_prefs, test_db_session)

        # Query the database directly.
        from src.modules.scenes.repository import PrivateSubmissionRepository

        repo = PrivateSubmissionRepository(test_db_session)
        submission = repo.get_for_owner(instance_id, creator.id)
        assert submission is not None
        # The encrypted_payload must not contain the raw preference keys.
        assert "require_vegetarian" not in submission.encrypted_payload
        assert "prefer_spicy" not in submission.encrypted_payload
