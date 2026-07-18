"""P12-04: Input validation and output filtering.

Verifies that malicious/malformed input is rejected gracefully:
- Overly long display_name / student_no → 422.
- Invalid email → 422.
- Invalid UUID in path → 422 or 404, never 500.
- HTML/script input is stored as plain text (no execution).
- SQL-like strings do not cause 500.
- Empty required fields → 422.

Key safety property: no unhandled input causes a 500 Internal Server Error.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import auth_headers, register_and_login, set_auth_cookies

# ---------------------------------------------------------------------------
# 1. Field-length validation
# ---------------------------------------------------------------------------


class TestFieldLengthValidation:
    def test_overly_long_display_name_rejected(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12long1@example.edu",
                "password": "SecurePass123",
                "display_name": "A" * 10_000,
                "student_no": "20264001",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 422

    def test_overly_long_student_no_rejected(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12long2@example.edu",
                "password": "SecurePass123",
                "display_name": "OK",
                "student_no": "9" * 10_000,
                "organization_ids": [],
            },
        )
        assert resp.status_code == 422

    def test_empty_display_name_rejected(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12empty@example.edu",
                "password": "SecurePass123",
                "display_name": "",
                "student_no": "20264002",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 2. Invalid email / type validation
# ---------------------------------------------------------------------------


class TestEmailValidation:
    def test_invalid_email_rejected(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
                "display_name": "Bad Email",
                "student_no": "20264010",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 422

    def test_missing_email_rejected(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "password": "SecurePass123",
                "display_name": "No Email",
                "student_no": "20264011",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 3. Invalid UUID in path does not cause 500
# ---------------------------------------------------------------------------


class TestInvalidUuidHandling:
    def test_invalid_uuid_in_org_path(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="p12uuid@example.edu", student_no="20264020"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/organizations/not-a-uuid")
        assert resp.status_code in (404, 422)
        assert resp.status_code != 500

    def test_invalid_uuid_in_conversation_path(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="p12uuidc@example.edu", student_no="20264021"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/conversations/xyz-not-uuid")
        assert resp.status_code in (404, 422)
        assert resp.status_code != 500

    def test_invalid_uuid_in_scene_path(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="p12uuids@example.edu", student_no="20264022"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.get("/api/v1/scenes/not-a-uuid")
        assert resp.status_code in (404, 422)
        assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 4. HTML / script / SQL-like input is safe
# ---------------------------------------------------------------------------


class TestHtmlAndSqlInput:
    def test_html_in_display_name_accepted_as_text(self, db_client: TestClient):
        """HTML in display_name should be stored as plain text, not executed.

        The API stores it as-is; the frontend is responsible for escaping.
        We only assert no 500 and that the response echoes the value safely.
        """
        payload = "<script>alert('xss')</script>"
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12html@example.edu",
                "password": "SecurePass123",
                "display_name": payload,
                "student_no": "20264030",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 201
        # Response body contains the display_name as a JSON string (escaped),
        # but no actual script execution occurs server-side.
        data = resp.json()["data"]
        assert data["display_name"] == payload

    def test_sql_injection_string_in_display_name(self, db_client: TestClient):
        """SQL-like strings must not crash the server."""
        payload = "'; DROP TABLE users; --"
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12sql@example.edu",
                "password": "SecurePass123",
                "display_name": payload,
                "student_no": "20264031",
                "organization_ids": [],
            },
        )
        assert resp.status_code == 201
        # Verify a subsequent registration still works (table not dropped).
        resp2 = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12sql2@example.edu",
                "password": "SecurePass123",
                "display_name": "After SQL",
                "student_no": "20264032",
                "organization_ids": [],
            },
        )
        assert resp2.status_code == 201

    def test_unicode_and_emoji_in_display_name(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/register",
            json={
                "email": "p12uni@example.edu",
                "password": "SecurePass123",
                "display_name": "测试用户 🎓\u0000newline",
                "student_no": "20264033",
                "organization_ids": [],
            },
        )
        # May be accepted or rejected, but must not 500.
        assert resp.status_code != 500


# ---------------------------------------------------------------------------
# 5. Malformed JSON body
# ---------------------------------------------------------------------------


class TestMalformedJson:
    def test_invalid_json_body(self, db_client: TestClient):
        resp = db_client.post(
            "/api/v1/auth/login",
            content='{"email": "broken", "password":}',
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)
        assert resp.status_code != 500

    def test_wrong_content_type_no_detail_leak(self, db_client: TestClient):
        """Form-encoded body to a JSON endpoint returns 422, not 500.

        P12-04 fix: validation error details are coerced to JSON-safe values
        so bytes from form-encoded bodies no longer cause a serialization
        TypeError.
        """
        resp = db_client.post(
            "/api/v1/auth/login",
            content="email=foo@example.edu&password=bar",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 422
        body = resp.text
        assert "Traceback" not in body
        assert "/root/" not in body
        assert "src.modules" not in body


# ---------------------------------------------------------------------------
# 6. Organization creation input validation
# ---------------------------------------------------------------------------


class TestOrganizationInputValidation:
    def test_invalid_org_type_rejected(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="p12orgv@example.edu", student_no="20264040"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            "/api/v1/organizations",
            json={
                "name": "Test",
                "type": "INVALID_TYPE",
                "visibility": "PUBLIC",
                "join_policy": "OPEN",
            },
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code in (400, 422)
        assert resp.status_code != 500

    def test_overly_long_org_name_rejected(self, db_client: TestClient):
        user = register_and_login(
            db_client, email="p12orgl@example.edu", student_no="20264041"
        )
        set_auth_cookies(db_client, user)
        resp = db_client.post(
            "/api/v1/organizations",
            json={
                "name": "X" * 100_000,
                "type": "CLUB",
                "visibility": "PUBLIC",
                "join_policy": "OPEN",
            },
            headers=auth_headers(user["csrf_token"]),
        )
        assert resp.status_code in (422, 400)
        assert resp.status_code != 500
