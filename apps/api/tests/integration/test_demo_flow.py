"""P11-06 through P11-09: Demo flow integration tests.

Covers:
- P11-06: Main path E2E smoke (reset → seed → login → browse → scene → admin).
- P11-07: Privacy E2E (DEMO_PRIVATE_PHRASE does not leak in results/admin).
- P11-08: Cleanup proof E2E (reset preserves non-demo data).
- P11-09: Failure scenarios (wrong password, soft-deleted, non-admin, CSRF).

Uses TestClient with an in-memory SQLite database — no Docker needed.
"""

from __future__ import annotations

import pytest
from httpx import Response
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from src.demo.data import (
    DEMO_ADMIN,
    DEMO_ALICE,
    DEMO_DELETED,
    DEMO_PASSWORD,
    DEMO_PRIVATE_PHRASE,
)
from src.demo.seed import seed_demo
from src.modules.scenes.plugins import DormDinnerPlugin
from src.modules.scenes.registry import get_scene_registry, reset_scene_registry


@pytest.fixture(autouse=True)
def setup_scene_registry():
    """Register the dorm dinner plugin before each test."""
    reset_scene_registry()
    registry = get_scene_registry()
    registry.register(DormDinnerPlugin())
    yield
    reset_scene_registry()


@pytest.fixture()
def seeded_client(db_client: TestClient, test_engine) -> TestClient:
    """A TestClient with demo data already seeded."""
    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = session_factory()
    try:
        seed_demo(session)
        session.commit()
    finally:
        session.close()
    return db_client


def _login_as(
    client: TestClient,
    email: str,
    password: str = DEMO_PASSWORD,
) -> Response:
    """Login via the API and return the HTTP response."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp


def _get_csrf(client: TestClient) -> str:
    """Extract the CSRF token from the TestClient cookie jar."""
    return client.cookies.get("csrf_token", "")


# ---------------------------------------------------------------------------
# P11-06: Main path E2E smoke
# ---------------------------------------------------------------------------


class TestMainPathSmoke:
    """Verifies the product main path end-to-end."""

    def test_demo_admin_login(self, seeded_client: TestClient) -> None:
        """demo_admin can login with the demo password."""
        resp = _login_as(seeded_client, DEMO_ADMIN.email)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == DEMO_ADMIN.email
        assert data["global_role"] == "SYSTEM_ADMIN"

    def test_demo_admin_can_access_directory(self, seeded_client: TestClient) -> None:
        """After login, admin can browse the organization directory."""
        _login_as(seeded_client, DEMO_ADMIN.email)
        resp = seeded_client.get("/api/v1/directory/tree")
        assert resp.status_code == 200

    def test_demo_alice_can_login_and_view_scenes(
        self, seeded_client: TestClient
    ) -> None:
        """Alice can login and list her scenes."""
        _login_as(seeded_client, DEMO_ALICE.email)
        resp = seeded_client.get("/api/v1/scenes")
        assert resp.status_code == 200

    def test_demo_status_endpoint(
        self, seeded_client: TestClient
    ) -> None:
        """Admin can check demo status via the internal API."""
        _login_as(seeded_client, DEMO_ADMIN.email)
        csrf = _get_csrf(seeded_client)
        resp = seeded_client.get(
            "/api/v1/internal/demo/status",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["users_present"] >= 5
        assert data["scenes_present"] == 1

    def test_demo_seed_endpoint_idempotent(
        self, seeded_client: TestClient
    ) -> None:
        """Re-seeding via the API does not duplicate data."""
        _login_as(seeded_client, DEMO_ADMIN.email)
        csrf = _get_csrf(seeded_client)
        resp = seeded_client.post(
            "/api/v1/internal/demo/seed",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        summary = resp.json()["data"]
        assert summary["users_created"] == 0
        assert summary["users_updated"] >= 5
        assert summary["scenes_created"] == 0


# ---------------------------------------------------------------------------
# P11-07: Privacy E2E
# ---------------------------------------------------------------------------


class TestPrivacyE2E:
    """DEMO_PRIVATE_PHRASE must not leak in results, admin, or storage."""

    def test_private_phrase_not_in_scene_result(
        self, seeded_client: TestClient
    ) -> None:
        """The scene result does not contain the private phrase."""
        _login_as(seeded_client, DEMO_ALICE.email)
        resp = seeded_client.get("/api/v1/scenes")
        assert resp.status_code == 200
        scenes_data = str(resp.json())
        assert DEMO_PRIVATE_PHRASE not in scenes_data

    def test_private_phrase_not_in_directory(
        self, seeded_client: TestClient
    ) -> None:
        """The directory listing does not contain the private phrase."""
        _login_as(seeded_client, DEMO_ADMIN.email)
        resp = seeded_client.get("/api/v1/directory/tree")
        assert resp.status_code == 200
        assert DEMO_PRIVATE_PHRASE not in str(resp.json())

    def test_private_phrase_not_in_demo_status(
        self, seeded_client: TestClient
    ) -> None:
        """The demo status endpoint returns no private data."""
        _login_as(seeded_client, DEMO_ADMIN.email)
        csrf = _get_csrf(seeded_client)
        resp = seeded_client.get(
            "/api/v1/internal/demo/status",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        assert DEMO_PRIVATE_PHRASE not in str(resp.json())

    def test_private_phrase_not_in_auth_me(
        self, seeded_client: TestClient
    ) -> None:
        """The /auth/me endpoint does not expose private preferences."""
        _login_as(seeded_client, DEMO_ALICE.email)
        resp = seeded_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert DEMO_PRIVATE_PHRASE not in str(resp.json())


# ---------------------------------------------------------------------------
# P11-08: Cleanup proof E2E
# ---------------------------------------------------------------------------


class TestCleanupProof:
    """Reset preserves non-demo data and allows re-seed."""

    def test_reset_preserves_non_demo_via_api(
        self, seeded_client: TestClient, test_engine
    ) -> None:
        """Reset via API preserves non-demo rows."""
        # Create a non-demo user via register
        resp = seeded_client.post(
            "/api/v1/auth/register",
            json={
                "email": "nondemo@example.edu",
                "password": "SecurePass123",
                "display_name": "Non Demo",
                "student_no": "20269999",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 201

        # Login as admin and reset
        _login_as(seeded_client, DEMO_ADMIN.email)
        csrf = _get_csrf(seeded_client)
        resp = seeded_client.post(
            "/api/v1/internal/demo/reset",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200

        # Non-demo user can still login
        resp = _login_as(seeded_client, "nondemo@example.edu", "SecurePass123")
        assert resp.status_code == 200

    def test_reset_then_reseed_restores_demo(
        self, seeded_client: TestClient, test_engine
    ) -> None:
        """After reset, re-seed restores full demo data.

        Reset deletes all demo users (including demo_admin), so no demo
        admin session remains to authenticate the seed API endpoint.
        The realistic reset+reseed flow therefore runs at the service
        layer — exactly what ``scripts/demo/seed_demo.py`` does (it
        calls reset_demo then seed_demo on the same session). This test
        mirrors that CLI flow: reset via the API (while the admin is
        still authenticated), then re-seed at the service layer, then
        prove demo_admin can log in again.
        """
        _login_as(seeded_client, DEMO_ADMIN.email)
        csrf = _get_csrf(seeded_client)

        # Reset via API (admin is still authenticated at this point).
        resp = seeded_client.post(
            "/api/v1/internal/demo/reset",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200

        # Re-seed at the service layer — mirrors the CLI flow in
        # scripts/demo/seed_demo.py. The API path cannot be used here
        # because reset deleted demo_admin and their auth session.
        session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
        session = session_factory()
        try:
            summary = seed_demo(session)
            session.commit()
        finally:
            session.close()

        assert summary["users_created"] >= 5
        assert summary["scenes_created"] == 1

        # Demo admin can login again after re-seed restored the dataset.
        resp = _login_as(seeded_client, DEMO_ADMIN.email)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# P11-09: Failure scenarios
# ---------------------------------------------------------------------------


class TestFailureScenarios:
    """System handles common failure states gracefully."""

    def test_wrong_password_login_fails(
        self, seeded_client: TestClient
    ) -> None:
        """Wrong password returns a non-200 status without leaking user existence."""
        resp = _login_as(seeded_client, DEMO_ALICE.email, "WrongPassword123!")
        assert resp.status_code in (401, 403, 422)
        resp_str = str(resp.json())
        # Should not reveal whether the email exists
        assert "not found" not in resp_str.lower()

    def test_soft_deleted_user_cannot_login(
        self, seeded_client: TestClient
    ) -> None:
        """A soft-deleted demo user cannot login."""
        resp = _login_as(seeded_client, DEMO_DELETED.email)
        assert resp.status_code in (401, 403)

    def test_non_admin_cannot_access_demo_routes(
        self, seeded_client: TestClient
    ) -> None:
        """A non-admin user cannot access demo reset/seed/status."""
        _login_as(seeded_client, DEMO_ALICE.email)
        csrf = _get_csrf(seeded_client)

        resp = seeded_client.get(
            "/api/v1/internal/demo/status",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code in (403, 401)

        resp = seeded_client.post(
            "/api/v1/internal/demo/reset",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code in (403, 401)

    def test_csrf_missing_on_write_fails(
        self, seeded_client: TestClient
    ) -> None:
        """A write request without CSRF token fails."""
        _login_as(seeded_client, DEMO_ADMIN.email)
        resp = seeded_client.post("/api/v1/internal/demo/seed")
        assert resp.status_code in (403, 401, 422)

    def test_nonexistent_user_login_fails_gracefully(
        self, seeded_client: TestClient
    ) -> None:
        """Login with a non-existent email fails without revealing details."""
        resp = _login_as(seeded_client, "nonexistent@example.com", "SomePassword1!")
        assert resp.status_code in (401, 403, 422)
        resp_str = str(resp.json())
        assert "not found" not in resp_str.lower()
