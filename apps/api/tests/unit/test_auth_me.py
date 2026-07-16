"""
Unit tests for GET /api/v1/auth/me (P3-06).

Tests verify:
- Valid access token returns current user info.
- Missing token fails with AUTH_INVALID_TOKEN.
- Refresh token cannot be used for /auth/me.
- Tampered token fails.
- Expired access token fails.
- Disabled user fails.
"""

from __future__ import annotations

import time

import jwt
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_get_cookies(client: TestClient) -> dict[str, str]:
    """Register a user and return cookies as a dict."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "meuser@example.edu",
            "password": "SecurePass123",
            "display_name": "Me User",
            "student_no": "20260300",
            "organization_ids": [],
        },
    )
    assert resp.status_code == 201
    cookies: dict[str, str] = {}
    for header in resp.headers.get_list("set-cookie"):
        name_value = header.split(";")[0]
        name, value = name_value.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _make_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ---------------------------------------------------------------------------
# 1. Valid access token
# ---------------------------------------------------------------------------


class TestMeSuccess:
    def test_me_returns_user_info(self, db_client: TestClient):
        """Valid access token returns 200 with user info."""
        cookies = _register_and_get_cookies(db_client)
        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": _make_cookie_header(cookies)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["email"] == "meuser@example.edu"
        assert data["display_name"] == "Me User"
        assert data["global_role"] == "STUDENT"


# ---------------------------------------------------------------------------
# 2. Token failures
# ---------------------------------------------------------------------------


class TestMeTokenFailures:
    def test_missing_token_fails(self, db_client: TestClient):
        """Missing access_token returns 401."""
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID_TOKEN"

    def test_refresh_token_cannot_be_used(self, db_client: TestClient):
        """Refresh token cannot be used for /auth/me."""
        cookies = _register_and_get_cookies(db_client)
        # Use refresh_token as access_token
        fake_cookies = {"access_token": cookies.get("refresh_token", "")}
        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": _make_cookie_header(fake_cookies)},
        )
        assert resp.status_code == 401

    def test_tampered_token_fails(self, db_client: TestClient):
        """Tampered access token fails."""
        cookies = _register_and_get_cookies(db_client)
        at = cookies.get("access_token", "")
        # Tamper: add extra char to signature
        tampered = at + "x"
        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": f"access_token={tampered}"},
        )
        assert resp.status_code == 401

    def test_garbage_token_fails(self, db_client: TestClient):
        """Non-JWT string fails."""
        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": "access_token=not-a-jwt"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. Expired token
# ---------------------------------------------------------------------------


class TestMeExpiredToken:
    def test_expired_access_token_fails(self, db_client: TestClient):
        """Expired access token fails."""
        cookies = _register_and_get_cookies(db_client)
        at = cookies.get("access_token", "")

        # Decode the token to get claims
        payload = jwt.decode(at, "test-secret-key-at-least-32-chars-long", algorithms=["HS256"])

        # Create an expired token with the same claims
        payload["exp"] = int(time.time()) - 3600  # expired 1 hour ago
        expired_token = jwt.encode(payload, "test-secret-key-at-least-32-chars-long", algorithm="HS256")

        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": f"access_token={expired_token}"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Disabled user
# ---------------------------------------------------------------------------


class TestMeDisabledUser:
    def test_disabled_user_fails(self, db_client: TestClient):
        """Disabled user cannot access /auth/me."""
        cookies = _register_and_get_cookies(db_client)
        at = cookies.get("access_token", "")

        # Disable user via DB
        import sqlalchemy

        engine = db_client.app.state.db_engine  # type: ignore[attr-defined]
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy.text(
                    "UPDATE users SET status = 'DISABLED' WHERE email = 'meuser@example.edu'"
                )
            )
            conn.commit()

        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": f"access_token={at}"},
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID_TOKEN"
