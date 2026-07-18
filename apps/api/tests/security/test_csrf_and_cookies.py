"""P12-02: CSRF enforcement and cookie attribute review.

Verifies:
- CSRF token is required on write endpoints (POST /organizations).
- Missing CSRF header → 403 CSRF_TOKEN_MISSING.
- Mismatched CSRF header → 403 CSRF_TOKEN_MISMATCH.
- Cookie attributes: HttpOnly, SameSite, Path, Max-Age present.
- access_token cookie has Path=/api/v1.
- refresh_token cookie has Path=/api/v1/auth.
- csrf_token cookie is non-HttpOnly (readable by JS).
- Secure flag absent in test env (present only in production).
"""

from __future__ import annotations

from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register(client: TestClient, email: str, student_no: str) -> dict[str, str]:
    client.cookies.clear()
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePass123",
            "display_name": "CSRF User",
            "student_no": student_no,
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


def _cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def _parse_cookie_attrs(raw_header: str) -> dict[str, str]:
    """Parse a Set-Cookie header into {attr: value}."""
    parts = [p.strip() for p in raw_header.split(";")]
    attrs: dict[str, str] = {}
    # first part is name=value
    name, value = parts[0].split("=", 1)
    attrs["__name"] = name.strip()
    attrs["__value"] = value.strip()
    for part in parts[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            attrs[k.strip().lower()] = v.strip()
        else:
            attrs[part.strip().lower()] = "true"
    return attrs


# ---------------------------------------------------------------------------
# 1. CSRF enforcement on write endpoints
# ---------------------------------------------------------------------------


class TestCsrfEnforcement:
    def test_post_organizations_requires_csrf(self, db_client: TestClient):
        cookies = _register(db_client, "p12csrf1@example.edu", "20261301")
        # No CSRF header
        resp = db_client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Org",
                "type": "CLUB",
                "visibility": "PUBLIC",
                "join_policy": "OPEN",
            },
            headers={"Cookie": _cookie_header(cookies)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISSING"

    def test_post_organizations_csrf_mismatch(self, db_client: TestClient):
        cookies = _register(db_client, "p12csrf2@example.edu", "20261302")
        resp = db_client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Org",
                "type": "CLUB",
                "visibility": "PUBLIC",
                "join_policy": "OPEN",
            },
            headers={
                "Cookie": _cookie_header(cookies),
                "X-CSRF-Token": "wrong-csrf-value",
            },
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "CSRF_TOKEN_MISMATCH"

    def test_post_organizations_with_valid_csrf_succeeds(self, db_client: TestClient):
        cookies = _register(db_client, "p12csrf3@example.edu", "20261303")
        resp = db_client.post(
            "/api/v1/organizations",
            json={
                "name": "CSRF Org",
                "type": "CLUB",
                "visibility": "PUBLIC",
                "join_policy": "OPEN",
            },
            headers={
                "Cookie": _cookie_header(cookies),
                "X-CSRF-Token": cookies["csrf_token"],
            },
        )
        assert resp.status_code == 201

    def test_login_csrf_exempt(self, db_client: TestClient):
        """Login/register must not require CSRF (bootstrap endpoints)."""
        resp = db_client.post(
            "/api/v1/auth/login",
            json={"email": "no-such-p12@example.edu", "password": "AnyPass123"},
        )
        # Should return 401 (invalid creds), NOT 403 (CSRF missing).
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Cookie attribute review
# ---------------------------------------------------------------------------


class TestCookieAttributes:
    def test_access_cookie_httponly_and_path(self, db_client: TestClient):
        # Re-register to capture headers
        db_client.cookies.clear()
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12cookie2@example.edu",
                "password": "SecurePass123",
                "display_name": "Cookie User",
                "student_no": "20261402",
                "organization_ids": [],
            },
        )
        headers = resp.headers.get_list("set-cookie")
        access = next(h for h in headers if h.startswith("access_token="))
        attrs = _parse_cookie_attrs(access)
        assert attrs.get("httponly") == "true"
        assert attrs.get("samesite", "").lower() == "lax"
        assert attrs.get("path") == "/api/v1"
        assert "max-age" in attrs
        # Secure flag absent in test env
        assert "secure" not in attrs

    def test_refresh_cookie_httponly_and_path(self, db_client: TestClient):
        db_client.cookies.clear()
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12cookie3@example.edu",
                "password": "SecurePass123",
                "display_name": "Cookie User",
                "student_no": "20261403",
                "organization_ids": [],
            },
        )
        headers = resp.headers.get_list("set-cookie")
        refresh = next(h for h in headers if h.startswith("refresh_token="))
        attrs = _parse_cookie_attrs(refresh)
        assert attrs.get("httponly") == "true"
        assert attrs.get("samesite", "").lower() == "lax"
        assert attrs.get("path") == "/api/v1/auth"
        assert "max-age" in attrs

    def test_csrf_cookie_not_httponly(self, db_client: TestClient):
        """csrf_token must be readable by JS (non-HttpOnly)."""
        db_client.cookies.clear()
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12cookie4@example.edu",
                "password": "SecurePass123",
                "display_name": "Cookie User",
                "student_no": "20261404",
                "organization_ids": [],
            },
        )
        headers = resp.headers.get_list("set-cookie")
        csrf = next(h for h in headers if h.startswith("csrf_token="))
        attrs = _parse_cookie_attrs(csrf)
        assert "httponly" not in attrs
        assert attrs.get("samesite", "").lower() == "lax"
        assert attrs.get("path") == "/"

    def test_all_cookies_have_samesite_lax(self, db_client: TestClient):
        db_client.cookies.clear()
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12cookie5@example.edu",
                "password": "SecurePass123",
                "display_name": "Cookie User",
                "student_no": "20261405",
                "organization_ids": [],
            },
        )
        headers = resp.headers.get_list("set-cookie")
        assert len(headers) >= 3
        for h in headers:
            attrs = _parse_cookie_attrs(h)
            assert attrs.get("samesite", "").lower() == "lax"
