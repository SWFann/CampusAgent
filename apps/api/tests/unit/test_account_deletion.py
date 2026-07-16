"""
Unit tests for account deletion (P3-09).

Tests verify:
- Soft-delete sets status to DELETED.
- deleted_at is set.
- Active sessions are revoked.
- After deletion, /auth/me fails.
- After deletion, login fails.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from src.modules.users.models import UserStatus
from src.modules.users.service import deactivate_user


def _register_and_get_cookies(client: TestClient, email: str = "delete@example.edu") -> dict:
    """Register and return cookies + user_id."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "display_name": "Delete User",
            "student_no": "20260700",
            "organization_ids": [],
        },
    )
    assert resp.status_code == 201
    cookies: dict[str, str] = {}
    for header in resp.headers.get_list("set-cookie"):
        name_value = header.split(";")[0]
        name, value = name_value.split("=", 1)
        cookies[name.strip()] = value.strip()
    user_id = resp.json()["data"]["id"]
    return {"cookies": cookies, "user_id": user_id}


def _make_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


class TestAccountDeletion:
    def test_soft_delete_sets_status(self, db_client: TestClient):
        """Deactivate sets status to DELETED."""
        from uuid import UUID

        from src.modules.users.models import User

        result = _register_and_get_cookies(db_client)
        user_id = UUID(result["user_id"])

        # Use the DB session from the app state
        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(user_id, session)
            # Verify directly from DB (bypass repository's soft-delete filter)
            user = session.get(User, user_id)
            assert user is not None
            assert user.status == UserStatus.DELETED.value
            assert user.deleted_at is not None
        finally:
            session.close()

    def test_after_deletion_auth_me_fails(self, db_client: TestClient):
        """After deletion, /auth/me returns 401."""
        from uuid import UUID

        result = _register_and_get_cookies(db_client)
        cookies = result["cookies"]
        user_id = UUID(result["user_id"])

        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(user_id, session)
        finally:
            session.close()

        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": _make_cookie_header(cookies)},
        )
        assert resp.status_code == 401

    def test_after_deletion_login_fails(self, db_client: TestClient):
        """After deletion, login returns AUTH_INVALID_CREDENTIALS."""
        from uuid import UUID

        result = _register_and_get_cookies(db_client, email="del2@example.edu")
        user_id = UUID(result["user_id"])

        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(user_id, session)
        finally:
            session.close()

        resp = db_client.post(
            "/api/v1/auth/login",
            json={"email": "del2@example.edu", "password": "SecurePass123"},
        )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_deletion_revokes_sessions(self, db_client: TestClient):
        """Active sessions are revoked after deletion."""
        from uuid import UUID

        from sqlalchemy import select

        from src.modules.auth.models import AuthSession, SessionStatus

        result = _register_and_get_cookies(db_client, email="del3@example.edu")
        user_id = UUID(result["user_id"])

        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(user_id, session)

            # Check sessions are revoked
            stmt = select(AuthSession).where(AuthSession.user_id == user_id)
            sessions = session.execute(stmt).scalars().all()
            for s in sessions:
                assert s.status == SessionStatus.REVOKED.value
        finally:
            session.close()

    def test_deleted_user_public_profile_returns_404(self, db_client: TestClient):
        """Soft-deleted users are no longer exposed by the public profile endpoint."""
        from uuid import UUID

        result = _register_and_get_cookies(db_client, email="del4@example.edu")
        user_id = UUID(result["user_id"])

        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(user_id, session)
        finally:
            session.close()

        resp = db_client.get(f"/api/v1/users/{user_id}")
        assert resp.status_code == 404
