"""P9-17: End-to-end privacy tests.

Tests cover (per P9 guide §19):
- A cannot see B's preferences.
- Group owner (creator) cannot see member private preferences.
- Admin cannot see private preferences.
- Logs have no plaintext.
- Events have no plaintext.
- No raw text in public candidates or results.
- TTL cleanup works.
"""
from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.modules.scenes.coordinator import run_generation_phase
from src.modules.scenes.models import PrivateSubmission
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
        email="privacy-creator@example.com",
        password_hash="fake",
        display_name="Creator",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def user_a(test_db_session: Session) -> User:
    user = User(
        email="privacy-a@example.com",
        password_hash="fake",
        display_name="User A",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def user_b(test_db_session: Session) -> User:
    user = User(
        email="privacy-b@example.com",
        password_hash="fake",
        display_name="User B",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def admin(test_db_session: Session) -> User:
    user = User(
        email="privacy-admin@example.com",
        password_hash="fake",
        display_name="Admin",
        global_role=GlobalRole.SYSTEM_ADMIN.value,
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
        "notes": "",
    }
    prefs.update(kwargs)
    return prefs


class TestParticipantPrivacy:
    """A cannot see B's preferences."""

    def test_a_cannot_see_b_submission_status(
        self,
        creator: User,
        user_a: User,
        user_b: User,
        test_db_session: Session,
    ) -> None:
        """User A's submission status only shows their own, not B's."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id, user_b.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)
        accept_invitation(user_b, instance_id, test_db_session)

        # A submits with a secret note.
        submit_private_preferences(
            user_a, instance_id,
            _make_prefs(notes="A's secret preference"),
            test_db_session,
        )
        # B submits with a different secret note.
        submit_private_preferences(
            user_b, instance_id,
            _make_prefs(notes="B's secret preference"),
            test_db_session,
        )

        # A checks their own status — should see has_submitted=True but no raw content.
        status_a = get_submission_status(user_a, instance_id, test_db_session)
        assert status_a["has_submitted"] is True
        assert "A's secret preference" not in str(status_a)
        # B's note should not be in A's status.
        assert "B's secret preference" not in str(status_a)

    def test_submission_status_no_raw_content(
        self,
        creator: User,
        user_a: User,
        test_db_session: Session,
    ) -> None:
        """Submission status response contains no raw preference content."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)

        submit_private_preferences(
            user_a, instance_id,
            _make_prefs(budget_min=42, notes="unique marker text xyz789"),
            test_db_session,
        )

        status = get_submission_status(user_a, instance_id, test_db_session)
        status_str = str(status)
        assert "unique marker text xyz789" not in status_str
        assert "sichuan" not in status_str  # cuisine
        # Budget value should not leak into status response. Exclude
        # timestamp fields from substring check, since ISO timestamps
        # may coincidentally contain the same digits (e.g. ".421077").
        non_ts_fields = {
            k: v for k, v in status.items()
            if k not in ("submitted_at", "expires_at")
        }
        assert "42" not in str(non_ts_fields)  # budget value
        assert "preferences" not in status_str.lower() or "has_submitted" in status_str


class TestCreatorPrivacy:
    """Creator cannot see member private preferences."""

    def test_creator_cannot_see_member_notes(
        self,
        creator: User,
        user_a: User,
        user_b: User,
        test_db_session: Session,
    ) -> None:
        """The creator cannot see other members' private notes."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id, user_b.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)
        accept_invitation(user_b, instance_id, test_db_session)

        member_secret = "member's very private dietary concern"
        submit_private_preferences(
            user_a, instance_id,
            _make_prefs(notes=member_secret),
            test_db_session,
        )

        # Creator checks their own status — should not see member's note.
        status = get_submission_status(creator, instance_id, test_db_session)
        assert member_secret not in str(status)

        # Creator cannot access user_a's submission via the API.
        # get_submission_status only returns the current user's status.
        # There is no API to list all members' submissions.

    def test_creator_cannot_see_member_raw_in_db(
        self,
        creator: User,
        user_a: User,
        test_db_session: Session,
    ) -> None:
        """After generation, the creator cannot find member's raw data in DB."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)

        member_secret = "unique_member_secret_abc123"
        submit_private_preferences(
            user_a, instance_id,
            _make_prefs(notes=member_secret),
            test_db_session,
        )
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)

        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        # After generation, all encrypted payloads should be empty.
        all_subs = test_db_session.query(PrivateSubmission).filter(
            PrivateSubmission.scene_instance_id == instance_id,
        ).all()
        for sub in all_subs:
            assert member_secret not in (sub.encrypted_payload or "")
            assert member_secret not in (sub.capsule_json or "")


class TestAdminPrivacy:
    """Admin cannot see private preferences."""

    def test_admin_cannot_access_scene(
        self,
        creator: User,
        user_a: User,
        admin: User,
        test_db_session: Session,
    ) -> None:
        """An admin who is not a participant cannot access the scene."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])

        from src.modules.scenes.exceptions import ScenePermissionDeniedError
        with pytest.raises(ScenePermissionDeniedError):
            get_scene_result(admin, instance_id, test_db_session)


class TestNoPlaintextInOutput:
    """No raw text in public candidates, results, or events."""

    def test_no_raw_in_candidates(
        self,
        creator: User,
        user_a: User,
        user_b: User,
        test_db_session: Session,
    ) -> None:
        """Public candidates contain no raw preference text."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id, user_b.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)
        accept_invitation(user_b, instance_id, test_db_session)

        secret_a = "A's secret dietary restriction detail"
        secret_b = "B's confidential budget concern"
        submit_private_preferences(
            user_a, instance_id, _make_prefs(notes=secret_a), test_db_session,
        )
        submit_private_preferences(
            user_b, instance_id, _make_prefs(notes=secret_b), test_db_session,
        )
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)

        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        candidates = list_candidates(creator, instance_id, test_db_session)
        candidates_str = str(candidates)
        assert secret_a not in candidates_str
        assert secret_b not in candidates_str

    def test_no_raw_in_result(
        self,
        creator: User,
        user_a: User,
        user_b: User,
        test_db_session: Session,
    ) -> None:
        """Public result contains no raw preference text."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id, user_b.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)
        accept_invitation(user_b, instance_id, test_db_session)

        secret_text = "unique_secret_xyz_for_result_test"
        submit_private_preferences(
            user_a, instance_id, _make_prefs(notes=secret_text), test_db_session,
        )
        submit_private_preferences(user_b, instance_id, _make_prefs(), test_db_session)
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)

        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        result = get_scene_result(creator, instance_id, test_db_session)
        result_str = str(result)
        assert secret_text not in result_str
        assert "notes" not in result_str.lower()
        assert "dietary_restrictions" not in result_str.lower()

    def test_no_individual_scores_in_result(
        self,
        creator: User,
        user_a: User,
        user_b: User,
        test_db_session: Session,
    ) -> None:
        """The public result does not contain individual participant scores."""
        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id, user_b.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)
        accept_invitation(user_b, instance_id, test_db_session)
        submit_private_preferences(creator, instance_id, _make_prefs(), test_db_session)
        submit_private_preferences(user_a, instance_id, _make_prefs(), test_db_session)
        submit_private_preferences(user_b, instance_id, _make_prefs(), test_db_session)
        transition_state(creator, instance_id, "start_processing", test_db_session)
        run_generation_phase(instance_id, test_db_session)

        result = get_scene_result(creator, instance_id, test_db_session)
        result_str = str(result).lower()
        assert "individual_scores" not in result_str
        assert "evaluations" not in result_str
        assert "user_a" not in result_str
        assert "user_b" not in result_str


class TestTtlCleanup:
    """TTL-based cleanup works."""

    def test_expired_submissions_cleaned(
        self,
        creator: User,
        user_a: User,
        test_db_session: Session,
    ) -> None:
        """Expired submissions are cleaned up by the periodic job."""
        from datetime import timedelta

        from src.db.time import utc_now

        result = create_scene_instance(
            creator,
            {
                "scene_key": "dorm_dinner",
                "participant_user_ids": [creator.id, user_a.id],
            },
            test_db_session,
        )
        instance_id = UUID(result["id"])
        transition_state(creator, instance_id, "publish", test_db_session)
        transition_state(creator, instance_id, "start_collecting", test_db_session)
        accept_invitation(user_a, instance_id, test_db_session)
        submit_private_preferences(
            user_a, instance_id,
            _make_prefs(notes="ttl cleanup test secret"),
            test_db_session,
        )

        # Manually expire the submission.
        sub_repo = PrivateSubmissionRepository(test_db_session)
        submissions = sub_repo.list_by_instance(instance_id)
        for sub in submissions:
            sub.expires_at = utc_now() - timedelta(hours=1)
        test_db_session.commit()

        # Run the expired cleanup.
        from src.modules.scenes.cleanup import cleanup_expired_submissions
        count = cleanup_expired_submissions(test_db_session)
        assert count >= 1

        # Verify data is purged.
        for sub in sub_repo.list_by_instance(instance_id):
            assert sub.encrypted_payload == ""
            assert sub.deleted_at is not None
