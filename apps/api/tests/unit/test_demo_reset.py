"""P11-03: Unit tests for demo reset service.

Verifies:
- Production environment raises DemoResetForbiddenError.
- Reset only deletes demo-namespace data.
- Non-demo users/orgs are preserved.
- Reset followed by seed restores full data.
- get_demo_status returns counts only (no sensitive data).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings
from src.demo.data import (
    DEMO_PRIVATE_PHRASE,
    DEMO_SCENE_IDEMPOTENCY_KEY,
    demo_emails,
)
from src.demo.reset import get_demo_status, reset_demo
from src.demo.security import DemoResetForbiddenError
from src.demo.seed import seed_demo
from src.modules.organizations.models import Organization
from src.modules.scenes.models import SceneInstance
from src.modules.scenes.plugins import DormDinnerPlugin
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry
from src.modules.users.models import User


@pytest.fixture(autouse=True)
def setup_scene_registry():
    """Register the dorm dinner plugin before each test."""
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(DormDinnerPlugin())
    yield
    reset_scene_registry()


def _make_test_settings(env: str = "test") -> Settings:
    """Create Settings with a specific APP_ENV.

    For production, set valid-length secrets so the production
    validator doesn't raise before our test can exercise the
    demo env guard.
    """
    old_env = os.environ.get("APP_ENV")
    old_secret = os.environ.get("APP_SECRET")
    old_enc = os.environ.get("FIELD_ENCRYPTION_KEY")
    old_db = os.environ.get("DATABASE_URL")
    old_redis = os.environ.get("REDIS_URL")
    old_log = os.environ.get("LOG_PROMPT_CONTENT")
    old_echo = os.environ.get("DB_ECHO_SQL")

    os.environ["APP_ENV"] = env
    os.environ["APP_SECRET"] = "production-strength-secret-key-32-chars!"
    os.environ["FIELD_ENCRYPTION_KEY"] = "production-encryption-key-32-chars!"
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/campus_agent"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["LOG_PROMPT_CONTENT"] = "false"
    os.environ["DB_ECHO_SQL"] = "false"
    try:
        return Settings(_env_file=None)  # type: ignore[call-arg]
    finally:
        for key, old_val in [
            ("APP_ENV", old_env),
            ("APP_SECRET", old_secret),
            ("FIELD_ENCRYPTION_KEY", old_enc),
            ("DATABASE_URL", old_db),
            ("REDIS_URL", old_redis),
            ("LOG_PROMPT_CONTENT", old_log),
            ("DB_ECHO_SQL", old_echo),
        ]:
            if old_val is not None:
                os.environ[key] = old_val
            else:
                os.environ.pop(key, None)


def _create_non_demo_user(session: Session) -> User:
    """Create a non-demo user that reset must preserve."""
    user = User(
        email="real_user@example.com",
        password_hash="$2b$12$fakehashrealuser",
        display_name="Real User",
        global_role="STUDENT",
        status="ACTIVE",
    )
    session.add(user)
    session.flush()
    return user


def _create_non_demo_org(session: Session, owner: User) -> Organization:
    """Create a non-demo organization that reset must preserve."""
    org = Organization(
        name="Real Org",
        slug="real-org",
        type="SCHOOL",
        parent_id=None,
        description="A real organization.",
        visibility="PUBLIC",
        join_policy="INVITE_ONLY",
        status="ACTIVE",
        created_by=owner.id,
    )
    session.add(org)
    session.flush()
    return org


class TestProductionGuard:
    """Reset must fail-closed in production."""

    def test_production_raises(self, test_db_session: Session) -> None:
        settings = _make_test_settings(env="production")
        with pytest.raises(DemoResetForbiddenError):
            reset_demo(test_db_session, settings)

    def test_development_allowed(self, test_db_session: Session) -> None:
        settings = _make_test_settings(env="development")
        summary = reset_demo(test_db_session, settings)
        assert isinstance(summary, dict)

    def test_test_env_allowed(self, test_db_session: Session) -> None:
        settings = _make_test_settings(env="test")
        summary = reset_demo(test_db_session, settings)
        assert isinstance(summary, dict)

    def test_error_contains_env_detail(self, test_db_session: Session) -> None:
        settings = _make_test_settings(env="production")
        with pytest.raises(DemoResetForbiddenError) as exc_info:
            reset_demo(test_db_session, settings)
        assert exc_info.value.code == "DEMO_RESET_FORBIDDEN"
        assert exc_info.value.status_code == 403
        assert "production" in str(exc_info.value.details)


class TestResetPreservesNonDemo:
    """Reset must not touch non-demo data."""

    def test_non_demo_user_preserved(self, test_db_session: Session) -> None:
        real_user = _create_non_demo_user(test_db_session)
        test_db_session.commit()

        seed_demo(test_db_session)

        settings = _make_test_settings(env="test")
        reset_demo(test_db_session, settings)
        test_db_session.commit()

        # Real user still exists
        user = test_db_session.get(User, real_user.id)
        assert user is not None
        assert user.email == "real_user@example.com"

    def test_non_demo_org_preserved(self, test_db_session: Session) -> None:
        real_user = _create_non_demo_user(test_db_session)
        real_org = _create_non_demo_org(test_db_session, real_user)
        test_db_session.commit()

        seed_demo(test_db_session)

        settings = _make_test_settings(env="test")
        reset_demo(test_db_session, settings)
        test_db_session.commit()

        org = test_db_session.get(Organization, real_org.id)
        assert org is not None
        assert org.slug == "real-org"

    def test_reset_deletes_demo_users(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        test_db_session.commit()

        settings = _make_test_settings(env="test")
        summary = reset_demo(test_db_session, settings)
        test_db_session.commit()

        assert summary["deleted_users"] >= 5

        remaining = test_db_session.execute(
            select(User).where(User.email.in_(demo_emails()))
        ).scalars().all()
        assert len(remaining) == 0

    def test_reset_deletes_demo_scene(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        test_db_session.commit()

        settings = _make_test_settings(env="test")
        reset_demo(test_db_session, settings)
        test_db_session.commit()

        remaining = test_db_session.execute(
            select(SceneInstance).where(
                SceneInstance.idempotency_key == DEMO_SCENE_IDEMPOTENCY_KEY
            )
        ).scalars().all()
        assert len(remaining) == 0

    def test_reset_summary_keys(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        test_db_session.commit()

        settings = _make_test_settings(env="test")
        summary = reset_demo(test_db_session, settings)
        test_db_session.commit()

        expected_keys = {
            "deleted_users",
            "deleted_organizations",
            "deleted_sessions",
            "deleted_messages",
            "deleted_scenes",
            "deleted_preferences",
        }
        assert set(summary.keys()) == expected_keys


class TestResetThenSeed:
    """Reset followed by seed restores full data."""

    def test_reset_then_seed_restores_users(
        self, test_db_session: Session
    ) -> None:
        settings = _make_test_settings(env="test")

        seed_demo(test_db_session)
        test_db_session.commit()

        reset_demo(test_db_session, settings)
        test_db_session.commit()

        summary = seed_demo(test_db_session)
        test_db_session.commit()

        assert summary["users_created"] >= 5
        assert summary["scenes_created"] == 1

    def test_double_reset_safe(self, test_db_session: Session) -> None:
        """Resetting twice in a row is safe (no crash, no negative counts)."""
        settings = _make_test_settings(env="test")
        seed_demo(test_db_session)
        test_db_session.commit()

        reset_demo(test_db_session, settings)
        test_db_session.commit()

        summary2 = reset_demo(test_db_session, settings)
        test_db_session.commit()

        for _key, val in summary2.items():
            assert isinstance(val, int)
            assert val >= 0


class TestDemoStatus:
    """get_demo_status returns non-sensitive counts."""

    def test_status_empty_before_seed(self, test_db_session: Session) -> None:
        status = get_demo_status(test_db_session)
        assert status["namespace"] == "demo"
        assert status["users_present"] == 0
        assert status["organizations_present"] == 0
        assert status["scenes_present"] == 0

    def test_status_populated_after_seed(
        self, test_db_session: Session
    ) -> None:
        seed_demo(test_db_session)
        test_db_session.commit()

        status = get_demo_status(test_db_session)
        assert status["users_present"] >= 5
        assert status["organizations_present"] >= 1
        assert status["scenes_present"] == 1

    def test_status_no_sensitive_data(self, test_db_session: Session) -> None:
        seed_demo(test_db_session)
        test_db_session.commit()

        status = get_demo_status(test_db_session)
        status_str = str(status)

        # No emails or passwords leaked
        assert "@" not in status_str
        assert "password" not in status_str.lower()
        # No DEMO_PRIVATE_PHRASE leaked
        assert DEMO_PRIVATE_PHRASE not in status_str

    def test_status_after_reset(self, test_db_session: Session) -> None:
        settings = _make_test_settings(env="test")
        seed_demo(test_db_session)
        test_db_session.commit()

        reset_demo(test_db_session, settings)
        test_db_session.commit()

        status = get_demo_status(test_db_session)
        assert status["users_present"] == 0
        assert status["organizations_present"] == 0
        assert status["scenes_present"] == 0
