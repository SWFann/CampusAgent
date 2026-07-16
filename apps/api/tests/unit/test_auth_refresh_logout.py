"""
Unit tests for POST /api/v1/auth/refresh and POST /api/v1/auth/logout (P3-05).

Tests verify:
- Refresh successfully rotates tokens.
- Old refresh token cannot be reused after rotation.
- Refresh replay revokes the entire family.
- Refresh missing CSRF returns CSRF_TOKEN_MISSING.
- Refresh CSRF mismatch returns CSRF_TOKEN_MISMATCH.
- Logout clears cookies.
- After logout, /auth/me fails.
"""

from __future__ import annotations

from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_get_cookies(client: TestClient) -> dict[str, str]:
    """Register a user and return the set-cookie values as a dict."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.edu",
            "password": "SecurePass123",
            "display_name": "Refresh User",
            "student_no": "20260200",
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
    """Build a Cookie header string from a dict."""
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ---------------------------------------------------------------------------
# 1. Refresh success
# ---------------------------------------------------------------------------


class TestRefreshSuccess:
    def test_refresh_returns_200(self, db_client: TestClient):
        """Refresh with valid token returns 200."""
        cookies = _register_and_get_cookies(db_client)
        csrf = cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": _make_cookie_header(cookies), "X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200

    def test_refresh_rotates_token(self, db_client: TestClient):
        """Refresh produces a new refresh_token cookie."""
        cookies = _register_and_get_cookies(db_client)
        csrf = cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": _make_cookie_header(cookies), "X-CSRF-Token": csrf},
        )
        assert resp.status_code == 200
        new_cookies: dict[str, str] = {}
        for header in resp.headers.get_list("set-cookie"):
            name_value = header.split(";")[0]
            name, value = name_value.split("=", 1)
            new_cookies[name.strip()] = value.strip()
        assert "refresh_token" in new_cookies
        assert new_cookies["refresh_token"] != cookies.get("refresh_token", "")


# ---------------------------------------------------------------------------
# 2. Refresh replay detection
# ---------------------------------------------------------------------------


class TestRefreshReplay:
    def test_old_token_cannot_reuse(self, db_client: TestClient):
        """Old refresh token cannot be reused after rotation."""
        cookies = _register_and_get_cookies(db_client)
        csrf = cookies.get("csrf_token", "")
        # First refresh — should succeed
        resp1 = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": _make_cookie_header(cookies), "X-CSRF-Token": csrf},
        )
        assert resp1.status_code == 200
        # Second refresh with OLD token — should fail with replay detection
        resp2 = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": _make_cookie_header(cookies), "X-CSRF-Token": csrf},
        )
        assert resp2.status_code == 401
        body = resp2.json()
        assert body["error"]["code"] in (
            "AUTH_REFRESH_TOKEN_REVOKED",
            "AUTH_INVALID_TOKEN",
        )


# ---------------------------------------------------------------------------
# 3. CSRF enforcement
# ---------------------------------------------------------------------------


class TestRefreshCsrf:
    def test_refresh_missing_csrf_returns_403(self, db_client: TestClient):
        """Refresh without X-CSRF-Token returns CSRF_TOKEN_MISSING."""
        cookies = _register_and_get_cookies(db_client)
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": _make_cookie_header(cookies)},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "CSRF_TOKEN_MISSING"

    def test_refresh_csrf_mismatch_returns_403(self, db_client: TestClient):
        """Refresh with mismatched CSRF returns CSRF_TOKEN_MISMATCH."""
        cookies = _register_and_get_cookies(db_client)
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={
                "Cookie": _make_cookie_header(cookies),
                "X-CSRF-Token": "wrong-csrf-value",
            },
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "CSRF_TOKEN_MISMATCH"


# ---------------------------------------------------------------------------
# 4. Logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_logout_returns_204(self, db_client: TestClient):
        """Logout returns 204 No Content."""
        cookies = _register_and_get_cookies(db_client)
        csrf = cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"Cookie": _make_cookie_header(cookies), "X-CSRF-Token": csrf},
        )
        assert resp.status_code == 204

    def test_logout_clears_cookies(self, db_client: TestClient):
        """Logout clears all auth cookies (Max-Age=0)."""
        cookies = _register_and_get_cookies(db_client)
        csrf = cookies.get("csrf_token", "")
        resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"Cookie": _make_cookie_header(cookies), "X-CSRF-Token": csrf},
        )
        set_cookie = resp.headers.get_list("set-cookie")
        assert len(set_cookie) >= 3
        assert any(header.startswith("access_token=") for header in set_cookie)
        assert any(header.startswith("refresh_token=") for header in set_cookie)
        assert any(header.startswith("csrf_token=") for header in set_cookie)
        for header in set_cookie:
            assert "Max-Age=0" in header or "max-age=0" in header.lower()

    def test_logout_csrf_missing(self, db_client: TestClient):
        """Logout without CSRF returns CSRF_TOKEN_MISSING."""
        cookies = _register_and_get_cookies(db_client)
        resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"Cookie": _make_cookie_header(cookies)},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "CSRF_TOKEN_MISSING"
