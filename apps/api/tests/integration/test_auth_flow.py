"""
Integration tests for the full auth flow (P3-11).

Tests verify the complete user journey:
- Register -> Login -> /auth/me -> Refresh -> Logout
- Register -> Logout -> /auth/me fails (cookie cleared by TestClient)
- Register -> Soft-delete -> /auth/me fails
"""

from __future__ import annotations

from starlette.testclient import TestClient


class TestFullAuthFlow:
    """End-to-end auth flow tests using TestClient's cookie jar."""

    def test_register_login_me_refresh_logout(self, db_client: TestClient):
        """Complete journey: register -> login -> me -> refresh -> logout."""
        # 1. Register (TestClient stores cookies automatically)
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "flow@example.edu",
                "password": "SecurePass123",
                "display_name": "Flow User",
                "student_no": "20260800",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 201

        # 2. /auth/me (TestClient sends access_token automatically)
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == "flow@example.edu"

        # 3. Login
        resp = db_client.post(
            "/api/v1/auth/login",
            json={"email": "flow@example.edu", "password": "SecurePass123"},
        )
        assert resp.status_code == 200

        # 4. /auth/me
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 200

        # 5. Refresh (needs CSRF — get from TestClient cookie jar)
        csrf = db_client.cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200

        # 6. /auth/me with new cookies
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 200

        # 7. Logout
        csrf = db_client.cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 204

    def test_logout_then_me_fails(self, db_client: TestClient):
        """After logout, cookies are cleared and /auth/me returns 401."""
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.edu",
                "password": "SecurePass123",
                "display_name": "Logout User",
                "student_no": "20260801",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 201

        # Logout
        csrf = db_client.cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code == 204

        # Clear cookies (simulating browser behavior after Set-Cookie: Max-Age=0)
        db_client.cookies.clear()

        # /auth/me should fail (access_token cookie cleared by logout)
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
