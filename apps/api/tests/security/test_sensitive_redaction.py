"""P12-06: Sensitive data redaction in logs, traces, and metrics.

Verifies:
- The denylist covers all known sensitive fields (P2–P11).
- redact() removes sensitive values from nested structures.
- redact_headers() removes Authorization/Cookie/Set-Cookie.
- Request logs do not include body, cookies, or tokens.
- Metrics labels do not carry user email or message body.
- password_hash is redacted (P12-06 addition).
"""

from __future__ import annotations

import io
import logging

import pytest

from src.utils.redaction import (
    SENSITIVE_FIELDS,
    is_sensitive,
    redact,
    redact_headers,
)

# ---------------------------------------------------------------------------
# 1. Denylist coverage
# ---------------------------------------------------------------------------


class TestDenylistCoverage:
    REQUIRED_FIELDS = [
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set-cookie",
        "secret",
        "app_secret",
        "field_encryption_key",
        "api_key",
        "model_gateway_api_key",
        "prompt",
        "private_preference",
        "memory_content",
        "chain_of_thought",
    ]

    def test_all_required_fields_in_denylist(self):
        for field in self.REQUIRED_FIELDS:
            assert field in SENSITIVE_FIELDS, f"{field} missing from denylist"

    def test_denylist_is_case_insensitive(self):
        assert is_sensitive("PASSWORD")
        assert is_sensitive("Access_Token")
        assert is_sensitive("API_KEY")

    def test_password_hash_is_sensitive(self):
        """P12-06: password_hash must be redacted."""
        assert is_sensitive("password_hash")
        assert is_sensitive("PASSWORD_HASH")


# ---------------------------------------------------------------------------
# 2. redact() behaviour
# ---------------------------------------------------------------------------


class TestRedactBehaviour:
    def test_redact_top_level(self):
        data = {"name": "ok", "password": "secret", "api_key": "sk-leak"}
        result = redact(data)
        assert result["name"] == "ok"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"

    def test_redact_nested(self):
        data = {"outer": {"inner": {"access_token": "eyJ"}}}
        result = redact(data)
        assert result["outer"]["inner"]["access_token"] == "[REDACTED]"

    def test_redact_list(self):
        data = [{"password": "a"}, {"password": "b"}]
        result = redact(data)
        assert all(item["password"] == "[REDACTED]" for item in result)

    def test_redact_does_not_modify_original(self):
        data = {"password": "secret"}
        redact(data)
        assert data["password"] == "secret"

    def test_redact_password_hash(self):
        data = {"user": {"password_hash": "$2b$secret", "email": "ok"}}
        result = redact(data)
        assert result["user"]["password_hash"] == "[REDACTED]"
        assert result["user"]["email"] == "ok"

    def test_redact_preserves_safe_fields(self):
        data = {"id": "123", "display_name": "Alice", "email": "a@b.edu"}
        result = redact(data)
        assert result == data


# ---------------------------------------------------------------------------
# 3. redact_headers() behaviour
# ---------------------------------------------------------------------------


class TestRedactHeaders:
    def test_authorization_redacted(self):
        headers = {"Authorization": "Bearer secret", "Content-Type": "application/json"}
        result = redact_headers(headers)
        assert result["Authorization"] == "[REDACTED]"
        assert result["Content-Type"] == "application/json"

    def test_cookie_redacted(self):
        headers = {"Cookie": "access_token=eyJ; csrf=abc"}
        result = redact_headers(headers)
        assert result["Cookie"] == "[REDACTED]"

    def test_set_cookie_redacted(self):
        headers = {"Set-Cookie": "access_token=eyJ; HttpOnly"}
        result = redact_headers(headers)
        assert result["Set-Cookie"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# 4. Request log does not contain sensitive data
# ---------------------------------------------------------------------------


class TestRequestLogSanitisation:
    """Capture the request logger output and assert no secrets leak."""

    @pytest.fixture()
    def captured_log(self):
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("campus_agent.request")
        logger.addHandler(handler)
        old_level = logger.level
        logger.setLevel(logging.DEBUG)
        yield buf
        logger.removeHandler(handler)
        logger.setLevel(old_level)

    def test_log_does_not_contain_cookie_value(self, db_client, captured_log):
        from tests.unit.helpers_p4 import register_and_login, set_auth_cookies

        creds = register_and_login(
            db_client, email="p12log1@example.edu", student_no="20265001"
        )
        set_auth_cookies(db_client, creds)
        db_client.get("/api/v1/auth/me")
        output = captured_log.getvalue()
        # The access_token cookie value must not appear in logs.
        assert creds["access_token"] not in output
        assert creds["csrf_token"] not in output

    def test_log_does_not_contain_authorization_header(self, db_client, captured_log):
        from tests.unit.helpers_p4 import register_and_login, set_auth_cookies

        creds = register_and_login(
            db_client, email="p12log2@example.edu", student_no="20265002"
        )
        set_auth_cookies(db_client, creds)
        db_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer test-bearer-secret"},
        )
        output = captured_log.getvalue()
        assert "test-bearer-secret" not in output


# ---------------------------------------------------------------------------
# 5. Metrics labels do not carry sensitive data
# ---------------------------------------------------------------------------


class TestMetricsLabelSafety:
    def test_metrics_text_has_no_email_or_token(self, db_client):
        from tests.unit.helpers_p4 import register_and_login, set_auth_cookies

        creds = register_and_login(
            db_client, email="p12metrics@example.edu", student_no="20265010"
        )
        set_auth_cookies(db_client, creds)
        db_client.get("/api/v1/auth/me")
        resp = db_client.get("/metrics")
        assert resp.status_code == 200
        text = resp.text
        # Metrics must not contain the user's email or token.
        assert "p12metrics@example.edu" not in text
        assert creds["access_token"] not in text
