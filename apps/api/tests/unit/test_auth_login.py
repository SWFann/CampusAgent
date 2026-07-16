"""
Unit tests for POST /api/v1/auth/login (P3-04).

Tests verify:
- Correct credentials login succeeds.
- Wrong password fails with AUTH_INVALID_CREDENTIALS.
- Non-existent email fails with AUTH_INVALID_CREDENTIALS.
- Wrong password and non-existent email produce the same response shape.
- Disabled user login fails (does not leak disabled status).
- Tokens are NOT in the response body.
- Login is CSRF-exempt.
"""

from __future__ import annotations

from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_user(client: TestClient, email: str = "loginuser@example.edu", password: str = "SecurePass123") -> None:
    """Register a user for login tests."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Login User",
            "student_no": "20260100",
            "organization_ids": [],
        },
    )
    assert resp.status_code == 201


def _login_payload(email: str = "loginuser@example.edu", password: str = "SecurePass123") -> dict:
    return {"email": email, "password": password}


# ---------------------------------------------------------------------------
# 1. Successful login
# ---------------------------------------------------------------------------


class TestLoginSuccess:
    def test_login_returns_200(self, db_client: TestClient):
        """Correct credentials return 200."""
        _register_user(db_client)
        resp = db_client.post("/api/v1/auth/login", json=_login_payload())
        assert resp.status_code == 200

    def test_login_response_has_user_fields(self, db_client: TestClient):
        """Login response contains user public fields."""
        _register_user(db_client)
        resp = db_client.post("/api/v1/auth/login", json=_login_payload())
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["email"] == "loginuser@example.edu"
        assert data["display_name"] == "Login User"
        assert data["global_role"] == "STUDENT"

    def test_login_sets_three_cookies(self, db_client: TestClient):
        """Login sets access_token, refresh_token, csrf_token cookies."""
        _register_user(db_client)
        resp = db_client.post("/api/v1/auth/login", json=_login_payload())
        set_cookie = resp.headers.get_list("set-cookie")
        cookie_names = [h.split("=")[0].strip() for h in set_cookie]
        assert "access_token" in cookie_names
        assert "refresh_token" in cookie_names
        assert "csrf_token" in cookie_names

    def test_login_no_tokens_in_body(self, db_client: TestClient):
        """Login response body must NOT contain token strings."""
        _register_user(db_client)
        resp = db_client.post("/api/v1/auth/login", json=_login_payload())
        data = resp.json().get("data", {})
        assert "access_token" not in data
        assert "refresh_token" not in data


# ---------------------------------------------------------------------------
# 2. Failed login
# ---------------------------------------------------------------------------


class TestLoginFailure:
    def test_wrong_password_fails(self, db_client: TestClient):
        """Wrong password returns 401 with AUTH_INVALID_CREDENTIALS."""
        _register_user(db_client)
        resp = db_client.post(
            "/api/v1/auth/login",
            json=_login_payload(password="WrongPass456"),
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_nonexistent_email_fails(self, db_client: TestClient):
        """Non-existent email returns 401 with AUTH_INVALID_CREDENTIALS."""
        resp = db_client.post(
            "/api/v1/auth/login",
            json=_login_payload(email="nobody@example.edu"),
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_wrong_password_and_nonexistent_same_shape(self, db_client: TestClient):
        """Wrong password and non-existent email produce the same response shape."""
        _register_user(db_client)
        wrong_pw = db_client.post(
            "/api/v1/auth/login",
            json=_login_payload(password="WrongPass456"),
        )
        nonexistent = db_client.post(
            "/api/v1/auth/login",
            json=_login_payload(email="nobody@example.edu"),
        )
        assert wrong_pw.status_code == nonexistent.status_code == 401
        wrong_body = wrong_pw.json()
        nonexist_body = nonexistent.json()
        assert wrong_body["error"]["code"] == nonexist_body["error"]["code"]
        assert wrong_body["error"]["message"] == nonexist_body["error"]["message"]


# ---------------------------------------------------------------------------
# 3. CSRF exemption
# ---------------------------------------------------------------------------


class TestLoginCsrfExempt:
    def test_login_no_csrf_required(self, db_client: TestClient):
        """Login does not require X-CSRF-Token header."""
        _register_user(db_client)
        resp = db_client.post("/api/v1/auth/login", json=_login_payload())
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. Disabled user
# ---------------------------------------------------------------------------


class TestLoginDisabledUser:
    def test_disabled_user_login_fails(self, db_client: TestClient):
        """Disabled user cannot login and does not leak disabled status."""
        _register_user(db_client, email="disabled@example.edu")

        # Manually disable the user via DB
        import sqlalchemy

        engine = db_client.app.state.db_engine  # type: ignore[attr-defined]
        with engine.connect() as conn:
            conn.execute(
                sqlalchemy.text(
                    "UPDATE users SET status = 'DISABLED' WHERE email = 'disabled@example.edu'"
                )
            )
            conn.commit()

        resp = db_client.post(
            "/api/v1/auth/login",
            json=_login_payload(email="disabled@example.edu"),
        )
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
        # Must not mention "disabled" or "deleted" in the message
        assert "disabled" not in body["error"]["message"].lower()
        assert "deleted" not in body["error"]["message"].lower()
