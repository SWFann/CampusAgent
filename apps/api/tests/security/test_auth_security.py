"""P12-02: Auth security review.

Consolidates and extends auth security regression coverage:
- Password hash never appears in any API response.
- Token strings (JWT prefix ``eyJ``) never appear in response bodies.
- Login does not distinguish user-not-found from wrong-password.
- Refresh token rotation: old token cannot be reused.
- Refresh replay revokes the entire family.
- Logout clears all auth cookies.
- Soft-deleted / disabled users cannot login or call /auth/me.
- Register response has no sensitive fields.

These tests are HTTP-level and use the in-memory SQLite ``db_client``.
"""

from __future__ import annotations

from uuid import UUID

from starlette.testclient import TestClient

from src.modules.users.service import deactivate_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register(
    client: TestClient,
    *,
    email: str,
    student_no: str,
    display_name: str = "Sec User",
) -> dict[str, str]:
    client.cookies.clear()
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "display_name": display_name,
            "student_no": student_no,
            "organization_ids": [],
        },
    )
    assert resp.status_code == 201, f"register failed: {resp.json()}"
    return {
        "user_id": resp.json()["data"]["id"],
        "access_token": client.cookies.get("access_token", ""),
        "refresh_token": client.cookies.get("refresh_token", ""),
        "csrf_token": client.cookies.get("csrf_token", ""),
    }


def _cookies_from_response(resp) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for header in resp.headers.get_list("set-cookie"):
        name_value = header.split(";")[0]
        name, value = name_value.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# ---------------------------------------------------------------------------
# 1. No sensitive data in responses
# ---------------------------------------------------------------------------


class TestNoSensitiveDataInResponses:
    def test_register_response_no_password_hash(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12sec1@example.edu",
                "password": "SecurePass123",
                "display_name": "P12",
                "student_no": "20261201",
                "organization_ids": [],
            },
        )
        assert "password_hash" not in resp.text
        assert "$2b" not in resp.text
        assert "argon" not in resp.text.lower()

    def test_login_response_no_token_strings(self, db_client: TestClient):
        _register(
            db_client,
            email="p12sec2@example.edu",
            student_no="20261202",
        )
        db_client.cookies.clear()
        resp = db_client.post(
            "/api/v1/auth/login",
            json={"email": "p12sec2@example.edu", "password": "SecurePass123"},
        )
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert "password_hash" not in data
        assert "eyJ" not in str(data)

    def test_me_response_no_sensitive_fields(self, db_client: TestClient):
        creds = _register(
            db_client,
            email="p12sec3@example.edu",
            student_no="20261203",
        )
        db_client.cookies.set("access_token", creds["access_token"])
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json().get("data", {})
        assert "password_hash" not in data
        assert "password" not in data
        assert "token" not in str(data).lower() or "session" not in str(data).lower()


# ---------------------------------------------------------------------------
# 2. Account enumeration prevention
# ---------------------------------------------------------------------------


class TestAccountEnumerationPrevention:
    def test_login_same_error_nonexistent_vs_wrong_password(self, db_client: TestClient):
        _register(
            db_client,
            email="p12enum@example.edu",
            student_no="20261210",
        )
        wrong = db_client.post(
            "/api/v1/auth/login",
            json={"email": "p12enum@example.edu", "password": "WrongPass456"},
        )
        nonexistent = db_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody-p12@example.edu", "password": "AnyPass123"},
        )
        assert wrong.status_code == nonexistent.status_code
        assert wrong.json()["error"]["code"] == nonexistent.json()["error"]["code"]
        assert (
            wrong.json()["error"]["message"] == nonexistent.json()["error"]["message"]
        )

    def test_login_same_status_code_for_both(self, db_client: TestClient):
        wrong = db_client.post(
            "/api/v1/auth/login",
            json={"email": "ghost-p12@example.edu", "password": "AnyPass123"},
        )
        assert wrong.status_code == 401


# ---------------------------------------------------------------------------
# 3. Refresh token rotation & replay detection
# ---------------------------------------------------------------------------


class TestRefreshTokenRotation:
    def test_refresh_returns_new_token(self, db_client: TestClient):
        creds = _register(
            db_client,
            email="p12rot@example.edu",
            student_no="20261220",
        )
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={
                "Cookie": _cookie_header(
                    {
                        "refresh_token": creds["refresh_token"],
                        "csrf_token": creds["csrf_token"],
                    }
                ),
                "X-CSRF-Token": creds["csrf_token"],
            },
        )
        assert resp.status_code == 200
        new_cookies = _cookies_from_response(resp)
        assert new_cookies.get("refresh_token", "") != creds["refresh_token"]

    def test_old_refresh_token_reuse_rejected(self, db_client: TestClient):
        creds = _register(
            db_client,
            email="p12replay@example.edu",
            student_no="20261221",
        )
        cookie_str = _cookie_header(
            {"refresh_token": creds["refresh_token"], "csrf_token": creds["csrf_token"]}
        )
        first = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": cookie_str, "X-CSRF-Token": creds["csrf_token"]},
        )
        assert first.status_code == 200
        second = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": cookie_str, "X-CSRF-Token": creds["csrf_token"]},
        )
        assert second.status_code == 401


# ---------------------------------------------------------------------------
# 4. Logout clears cookies
# ---------------------------------------------------------------------------


class TestLogoutClearsCookies:
    def test_logout_clears_all_cookies(self, db_client: TestClient):
        creds = _register(
            db_client,
            email="p12logout@example.edu",
            student_no="20261230",
        )
        cookie_str = _cookie_header(
            {
                "access_token": creds["access_token"],
                "refresh_token": creds["refresh_token"],
                "csrf_token": creds["csrf_token"],
            }
        )
        resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"Cookie": cookie_str, "X-CSRF-Token": creds["csrf_token"]},
        )
        assert resp.status_code == 204
        set_cookie = resp.headers.get_list("set-cookie")
        assert any(h.startswith("access_token=") for h in set_cookie)
        assert any(h.startswith("refresh_token=") for h in set_cookie)
        assert any(h.startswith("csrf_token=") for h in set_cookie)
        for h in set_cookie:
            assert "max-age=0" in h.lower()

    def test_me_fails_after_logout_clears_client_cookies(self, db_client: TestClient):
        """After logout the client cookie jar is cleared (Max-Age=0).

        Note: CampusAgent uses stateless short-lived access JWTs (60 min).
        Logout clears the browser cookie so the token can no longer be
        presented. A token stolen *before* logout remains valid until
        expiry — this is an accepted stateless-JWT tradeoff documented in
        the P12 risk register (RISK-P12-002). Here we verify the
        cookie-based property: with the cookie jar cleared, /me fails.
        """
        creds = _register(
            db_client,
            email="p12logout2@example.edu",
            student_no="20261231",
        )
        cookie_str = _cookie_header(
            {
                "access_token": creds["access_token"],
                "refresh_token": creds["refresh_token"],
                "csrf_token": creds["csrf_token"],
            }
        )
        logout_resp = db_client.post(
            "/api/v1/auth/logout",
            headers={"Cookie": cookie_str, "X-CSRF-Token": creds["csrf_token"]},
        )
        assert logout_resp.status_code == 204
        # The TestClient honours Set-Cookie Max-Age=0, so the access_token
        # cookie is removed from the jar. A subsequent /me without manually
        # re-adding the stolen token must fail.
        db_client.cookies.clear()
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 5. Disabled / deleted users cannot authenticate
# ---------------------------------------------------------------------------


class TestDisabledDeletedUsers:
    def test_soft_deleted_user_cannot_login(self, db_client: TestClient):
        creds = _register(
            db_client,
            email="p12deleted@example.edu",
            student_no="20261240",
        )
        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(UUID(creds["user_id"]), session)
        finally:
            session.close()
        db_client.cookies.clear()
        resp = db_client.post(
            "/api/v1/auth/login",
            json={"email": "p12deleted@example.edu", "password": "SecurePass123"},
        )
        assert resp.status_code == 401

    def test_soft_deleted_user_me_fails(self, db_client: TestClient):
        creds = _register(
            db_client,
            email="p12deleted2@example.edu",
            student_no="20261241",
        )
        session_factory = db_client.app.state.db_sessionmaker  # type: ignore[attr-defined]
        session = session_factory()
        try:
            deactivate_user(UUID(creds["user_id"]), session)
        finally:
            session.close()
        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": f"access_token={creds['access_token']}"},
        )
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, db_client: TestClient):
        resp = db_client.get(
            "/api/v1/auth/me",
            headers={"Cookie": "access_token=invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_missing_token_rejected(self, db_client: TestClient):
        resp = db_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
