"""
Unit tests for POST /api/v1/auth/register (P3-03).

Tests verify:
- Successful registration creates a User and StudentProfile.
- Three cookies (access_token, refresh_token, csrf_token) are set.
- Cookie attributes match the API contract.
- Response body does NOT contain access_token or refresh_token.
- Duplicate email returns 409 with USER_ALREADY_EXISTS.
- Duplicate student_no returns 409 with USER_ALREADY_EXISTS.
- Weak password returns 400 with AUTH_WEAK_PASSWORD.
- Register is CSRF-exempt (no CSRF header required).
"""

from __future__ import annotations

from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_payload(
    *,
    email: str = "student@example.edu",
    password: str = "SecurePass123",
    display_name: str = "张三",
    student_no: str = "20260001",
    phone_number: str | None = None,
) -> dict:
    """Return a valid register request payload."""
    payload = {
        "email": email,
        "password": password,
        "display_name": display_name,
        "student_no": student_no,
        "organization_ids": [],
    }
    if phone_number is not None:
        payload["phone_number"] = phone_number
    return payload


def _extract_cookies(set_cookie_headers: list[str]) -> dict[str, dict[str, str]]:
    """Parse Set-Cookie headers into a dict of cookie_name -> attributes."""
    cookies: dict[str, dict[str, str]] = {}
    for header in set_cookie_headers:
        parts = header.split(";")
        if not parts:
            continue
        name_value = parts[0].strip()
        if "=" not in name_value:
            continue
        name, value = name_value.split("=", 1)
        name = name.strip()
        attrs: dict[str, str] = {"value": value.strip()}
        for part in parts[1:]:
            part = part.strip().lower()
            if "=" in part:
                k, v = part.split("=", 1)
                attrs[k.strip()] = v.strip()
            else:
                attrs[part] = "true"
        cookies[name] = attrs
    return cookies


# ---------------------------------------------------------------------------
# 1. Successful registration
# ---------------------------------------------------------------------------


class TestRegisterSuccess:
    def test_register_returns_201(self, db_client: TestClient):
        """Successful registration returns 201 Created."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        assert resp.status_code == 201

    def test_register_response_has_user_fields(self, db_client: TestClient):
        """Response body contains user public fields."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "id" in data
        assert data["email"] == "student@example.edu"
        assert data["display_name"] == "张三"
        assert data["global_role"] == "STUDENT"

    def test_register_response_no_tokens(self, db_client: TestClient):
        """Response body must NOT contain access_token or refresh_token."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        body = resp.json()
        data_str = str(body)
        assert "access_token" not in data_str.lower() or body.get("data", {}).get("access_token") is None
        assert "refresh_token" not in str(body.get("data", {})).lower()

    def test_phone_and_agent_code_are_stored_but_not_exposed(
        self, db_client: TestClient, test_session_factory
    ):
        """Private phone and deterministic agent code stay in the student profile."""
        from src.modules.users.models import StudentProfile

        resp = db_client.post(
            "/api/v1/auth/register",
            json=_register_payload(phone_number="138 0013-8000"),
        )
        assert resp.status_code == 201
        assert "phone" not in str(resp.json()).lower()

        with test_session_factory() as session:
            profile = session.query(StudentProfile).filter_by(
                student_no="20260001"
            ).one()
            assert profile.phone_number == "13800138000"
            assert profile.agent_code == "campusagent20260001"

    def test_register_sets_three_cookies(self, db_client: TestClient):
        """Three auth cookies are set: access_token, refresh_token, csrf_token."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        set_cookie = resp.headers.get_list("set-cookie")
        cookies = _extract_cookies(set_cookie)
        assert "access_token" in cookies
        assert "refresh_token" in cookies
        assert "csrf_token" in cookies

    def test_access_token_cookie_attributes(self, db_client: TestClient):
        """access_token cookie has correct attributes."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        set_cookie = resp.headers.get_list("set-cookie")
        cookies = _extract_cookies(set_cookie)
        at = cookies["access_token"]
        assert "httponly" in at
        assert at.get("samesite") == "lax"
        assert at.get("path") == "/api/v1"
        assert at.get("max-age") == "3600"

    def test_refresh_token_cookie_attributes(self, db_client: TestClient):
        """refresh_token cookie has correct attributes."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        set_cookie = resp.headers.get_list("set-cookie")
        cookies = _extract_cookies(set_cookie)
        rt = cookies["refresh_token"]
        assert "httponly" in rt
        assert rt.get("samesite") == "lax"
        assert rt.get("path") == "/api/v1/auth"
        assert rt.get("max-age") == "604800"

    def test_csrf_cookie_attributes(self, db_client: TestClient):
        """csrf_token cookie is non-HttpOnly."""
        resp = db_client.post("/api/v1/auth/register", json=_register_payload())
        set_cookie = resp.headers.get_list("set-cookie")
        cookies = _extract_cookies(set_cookie)
        csrf = cookies["csrf_token"]
        assert "httponly" not in csrf
        assert csrf.get("samesite") == "lax"
        assert csrf.get("path") == "/"
        assert csrf.get("max-age") == "604800"


# ---------------------------------------------------------------------------
# 2. Duplicate registration
# ---------------------------------------------------------------------------


class TestRegisterDuplicate:
    def test_duplicate_email_returns_409(self, db_client: TestClient):
        """Duplicate email returns 409 with USER_ALREADY_EXISTS."""
        payload = _register_payload(email="dup@example.edu")
        resp1 = db_client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        payload2 = _register_payload(
            email="dup@example.edu", student_no="20260002"
        )
        resp2 = db_client.post("/api/v1/auth/register", json=payload2)
        assert resp2.status_code == 409
        body = resp2.json()
        assert body["error"]["code"] == "USER_ALREADY_EXISTS"

    def test_duplicate_student_no_returns_409(self, db_client: TestClient):
        """Duplicate student_no returns 409 with USER_ALREADY_EXISTS."""
        payload = _register_payload(student_no="20260003")
        resp1 = db_client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        payload2 = _register_payload(
            email="other@example.edu", student_no="20260003"
        )
        resp2 = db_client.post("/api/v1/auth/register", json=payload2)
        assert resp2.status_code == 409
        body = resp2.json()
        assert body["error"]["code"] == "USER_ALREADY_EXISTS"

    def test_duplicate_phone_returns_409(self, db_client: TestClient):
        """One phone number cannot be bound to multiple student identities."""
        resp1 = db_client.post(
            "/api/v1/auth/register",
            json=_register_payload(phone_number="13800138000"),
        )
        assert resp1.status_code == 201

        resp2 = db_client.post(
            "/api/v1/auth/register",
            json=_register_payload(
                email="phone-owner@example.edu",
                student_no="20260009",
                phone_number="13800138000",
            ),
        )
        assert resp2.status_code == 409
        assert resp2.json()["error"]["code"] == "USER_ALREADY_EXISTS"


# ---------------------------------------------------------------------------
# 3. Weak password
# ---------------------------------------------------------------------------


class TestRegisterWeakPassword:
    def test_weak_password_returns_400(self, db_client: TestClient):
        """Weak password returns 400 with AUTH_WEAK_PASSWORD."""
        payload = _register_payload(password="short1")
        resp = db_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"]["code"] == "AUTH_WEAK_PASSWORD"

    def test_no_digit_returns_400(self, db_client: TestClient):
        """Password without digits returns 400."""
        payload = _register_payload(password="NoDigitsHere")
        resp = db_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_weak_password_no_leak(self, db_client: TestClient):
        """Error response must not contain the plaintext password."""
        password = "MyWeakPwd"
        payload = _register_payload(password=password)
        resp = db_client.post("/api/v1/auth/register", json=payload)
        assert password not in resp.text


# ---------------------------------------------------------------------------
# 4. CSRF exemption
# ---------------------------------------------------------------------------


class TestRegisterCsrfExempt:
    def test_register_no_csrf_header_required(self, db_client: TestClient):
        """Register endpoint does not require X-CSRF-Token header."""
        resp = db_client.post(
            "/api/v1/auth/register",
            json=_register_payload(),
            # No X-CSRF-Token header
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# 5. Email normalisation
# ---------------------------------------------------------------------------


class TestEmailNormalisation:
    def test_email_lowercased(self, db_client: TestClient):
        """Email is normalised to lowercase."""
        payload = _register_payload(email="Student@Example.edu")
        resp = db_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["data"]["email"] == "student@example.edu"
