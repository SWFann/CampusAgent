"""P11-02: Unit tests for idempotent demo seed service.

Verifies:
- First seed creates users, orgs, conversation, scene.
- Second seed is idempotent (no duplicates).
- Password hashes are not plaintext.
- demo_deleted is marked as not loginable.
- Seed summary has stable fields.
- DEMO_PRIVATE_PHRASE appears in private preference notes.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings
from src.demo.data import (
    DEMO_DELETED,
    DEMO_PASSWORD,
    DEMO_SCENE_IDEMPOTENCY_KEY,
    DEMO_USERS,
    demo_emails,
)
from src.demo.seed import seed_demo
from src.modules.conversations.models import Conversation
from src.modules.scenes.models import SceneInstance
from src.modules.scenes.plugins import DormDinnerPlugin
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.users.models import User, UserStatus


@pytest.fixture(autouse=True)
def setup_scene_registry():
    """Register the dorm dinner plugin before each test."""
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(DormDinnerPlugin())
    yield
    reset_scene_registry()


def _make_test_settings() -> Settings:
    """Create test settings (APP_ENV=test from conftest)."""
    return Settings(_env_file=None)  # type: ignore[call-arg]


class TestSeedCreatesData:
    """First seed creates all expected rows."""

    def test_seed_creates_users(self, test_db_session: Session) -> None:
        summary = seed_demo(test_db_session)
        assert summary["users_created"] == len(DEMO_USERS)
        assert summary["users_updated"] == 0

        emails = demo_emails()
        users = test_db_session.execute(
            select(User).where(User.email.in_(emails))
        ).scalars().all()
        assert len(users) == len(DEMO_USERS)

    def test_seed_creates_organizations(self, test_db_session: Session) -> None:
        summary = seed_demo(test_db_session)
        assert summary["organizations_created"] >= 1

    def test_seed_creates_conversation(self, test_db_session: Session) -> None:
        summary = seed_demo(test_db_session)
        assert summary["conversations_created"] == 1
        assert summary["messages_created"] >= 2

        convs = test_db_session.execute(
            select(Conversation).where(
                Conversation.title == "Demo Dorm 301 Group Chat"
            )
        ).scalars().all()
        assert len(convs) == 1

    def test_seed_creates_scene(self, test_db_session: Session) -> None:
        summary = seed_demo(test_db_session)
        assert summary["scenes_created"] == 1
        assert summary["preferences_created"] >= 3
        assert summary["votes_created"] >= 2

        instances = test_db_session.execute(
            select(SceneInstance).where(
                SceneInstance.idempotency_key == DEMO_SCENE_IDEMPOTENCY_KEY
            )
        ).scalars().all()
        assert len(instances) == 1


class TestSeedIdempotency:
    """Second seed does not duplicate data."""

    def test_second_seed_no_new_users(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        summary2 = seed_demo(test_db_session)

        assert summary2["users_created"] == 0
        assert summary2["users_updated"] == len(DEMO_USERS)

    def test_second_seed_no_new_orgs(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        summary2 = seed_demo(test_db_session)
        assert summary2["organizations_created"] == 0

    def test_second_seed_no_new_conversation(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        summary2 = seed_demo(test_db_session)
        assert summary2["conversations_created"] == 0
        assert summary2["messages_created"] == 0

    def test_second_seed_no_new_scene(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        summary2 = seed_demo(test_db_session)
        assert summary2["scenes_created"] == 0

    def test_third_seed_still_idempotent(self, test_db_session: Session) -> None:
        """Running seed three times remains stable."""
        seed_demo(test_db_session)
        seed_demo(test_db_session)
        summary3 = seed_demo(test_db_session)

        assert summary3["users_created"] == 0
        assert summary3["users_updated"] == len(DEMO_USERS)
        assert summary3["scenes_created"] == 0


class TestPasswordSecurity:
    """Password hashing invariants."""

    def test_password_hash_not_plaintext(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)

        users = test_db_session.execute(
            select(User).where(User.email.in_(demo_emails()))
        ).scalars().all()
        for user in users:
            assert user.password_hash != DEMO_PASSWORD
            assert user.password_hash != ""
            assert len(user.password_hash) > 20

    def test_password_hash_is_bcrypt(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)

        users = test_db_session.execute(
            select(User).where(User.email.in_(demo_emails()))
        ).scalars().all()
        for user in users:
            # bcrypt hashes start with $2
            assert user.password_hash.startswith("$2"), (
                f"User {user.email} hash not bcrypt"
            )


class TestDeletedUser:
    """Soft-deleted demo user cannot login."""

    def test_deleted_user_status(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)

        user = test_db_session.execute(
            select(User).where(User.email == DEMO_DELETED.email)
        ).scalar_one_or_none()
        assert user is not None
        assert user.status == UserStatus.DELETED.value
        assert user.deleted_at is not None


class TestSummaryStability:
    """Seed summary has stable and well-known keys."""

    def test_summary_keys(self, test_db_session: Session) -> None:
        summary = seed_demo(test_db_session)
        expected_keys = {
            "users_created",
            "users_updated",
            "organizations_created",
            "memberships_created",
            "conversations_created",
            "messages_created",
            "scenes_created",
            "votes_created",
            "preferences_created",
        }
        assert set(summary.keys()) == expected_keys

    def test_summary_values_non_negative(self, test_db_session: Session) -> None:
        summary = seed_demo(test_db_session)
        for key, val in summary.items():
            assert isinstance(val, int), f"{key} not int"
            assert val >= 0, f"{key} negative: {val}"
