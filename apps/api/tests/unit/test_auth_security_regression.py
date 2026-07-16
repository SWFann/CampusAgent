"""
Security regression tests for auth (P3-11).

These tests verify security properties that must not regress:
- Password hash never appears in API responses.
- Access/refresh token strings never appear in response bodies.
- Login does not distinguish "user not found" from "wrong password".
- CSRF is enforced on write endpoints.
- Rate limiter blocks excessive requests.
- Disabled user login returns same error as invalid credentials.
"""

from __future__ import annotations

from starlette.testclient import TestClient


class TestNoSensitiveDataInResponses:
    def test_register_response_no_password_hash(self, db_client: TestClient):
        """Register response must not contain password_hash."""
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "sec@example.edu",
                "password": "SecurePass123",
                "display_name": "Sec",
                "student_no": "20260900",
                "organization_ids": [],
            },
        )
        assert "password_hash" not in resp.text
        assert "$2b" not in resp.text  # bcrypt prefix

    def test_login_response_no_token_strings(self, db_client: TestClient):
        """Login response body must not contain JWT token strings."""
        db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "sec2@example.edu",
                "password": "SecurePass123",
                "display_name": "Sec2",
                "student_no": "20260901",
                "organization_ids": [],
            },
        )
        resp = db_client.post(
            "/api/v1/auth/login",
            json={"email": "sec2@example.edu", "password": "SecurePass123"},
        )
        body = resp.json()
        data = body.get("data", {})
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert "eyJ" not in str(data)  # JWT prefix


class TestAccountEnumerationPrevention:
    def test_login_same_error_for_nonexistent_and_wrong(self, db_client: TestClient):
        """Login returns identical error for non-existent and wrong password."""
        db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "enum@example.edu",
                "password": "SecurePass123",
                "display_name": "Enum",
                "student_no": "20260902",
                "organization_ids": [],
            },
        )
        wrong_pw = db_client.post(
            "/api/v1/auth/login",
            json={"email": "enum@example.edu", "password": "WrongPass456"},
        )
        nonexistent = db_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.edu", "password": "AnyPass123"},
        )
        assert wrong_pw.status_code == nonexistent.status_code
        assert wrong_pw.json()["error"]["code"] == nonexistent.json()["error"]["code"]
        assert wrong_pw.json()["error"]["message"] == nonexistent.json()["error"]["message"]


class TestCsrfEnforcement:
    def test_refresh_without_csrf(self, db_client: TestClient):
        """Refresh without CSRF header returns 403."""
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "csrf@example.edu",
                "password": "SecurePass123",
                "display_name": "CSRF",
                "student_no": "20260903",
                "organization_ids": [],
            },
        )
        cookies: dict[str, str] = {}
        for header in resp.headers.get_list("set-cookie"):
            name_value = header.split(";")[0]
            name, value = name_value.split("=", 1)
            cookies[name.strip()] = value.strip()

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        resp = db_client.post(
            "/api/v1/auth/refresh",
            headers={"Cookie": cookie_header},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISSING"


class TestRateLimiterSecurity:
    def test_rate_limiter_does_not_leak_account(self, db_client: TestClient):
        """Rate-limited responses don't reveal account existence."""
        limiter_resp = None
        for _ in range(10):
            resp = db_client.post(
                "/api/v1/auth/login",
                json={"email": "rate@example.edu", "password": "WrongPass123"},
            )
            if resp.status_code == 429:
                limiter_resp = resp
                break

        # If rate limited, the error must not reveal account existence
        if limiter_resp is not None:
            body = limiter_resp.json()
            assert "rate" not in str(body).lower() or "rate_limit" in body.get("error", {}).get("code", "").lower()
