"""
Unit tests for sensitive field redaction (P2-08).

These tests verify:
- Sensitive fields in dict are redacted.
- Nested dict redaction works.
- List inside dict is redacted.
- Case-insensitive key matching.
- Headers are redacted.
- Non-sensitive fields are preserved.
- Original object is not modified.
- Sensitive values do not appear in redacted output.
"""

from __future__ import annotations

from src.utils.redaction import (
    SENSITIVE_FIELDS,
    is_sensitive,
    redact,
    redact_headers,
)

# ---------------------------------------------------------------------------
# 1. is_sensitive
# ---------------------------------------------------------------------------


class TestIsSensitive:
    def test_password_is_sensitive(self) -> None:
        assert is_sensitive("password") is True

    def test_token_is_sensitive(self) -> None:
        assert is_sensitive("token") is True

    def test_prompt_is_sensitive(self) -> None:
        assert is_sensitive("prompt") is True

    def test_chain_of_thought_is_sensitive(self) -> None:
        assert is_sensitive("chain_of_thought") is True

    def test_case_insensitive(self) -> None:
        assert is_sensitive("PASSWORD") is True
        assert is_sensitive("Token") is True
        assert is_sensitive("ACCESS_TOKEN") is True

    def test_non_sensitive_field(self) -> None:
        assert is_sensitive("username") is False
        assert is_sensitive("email") is False
        assert is_sensitive("id") is False

    def test_all_defined_fields_are_sensitive(self) -> None:
        for field in SENSITIVE_FIELDS:
            assert is_sensitive(field) is True
            assert is_sensitive(field.upper()) is True


# ---------------------------------------------------------------------------
# 2. redact dict
# ---------------------------------------------------------------------------


class TestRedactDict:
    def test_simple_dict_redaction(self) -> None:
        data = {"username": "alice", "password": "secret123"}
        result = redact(data)
        assert result["username"] == "alice"
        assert result["password"] == "[REDACTED]"
        assert "secret123" not in str(result)

    def test_nested_dict_redaction(self) -> None:
        data = {
            "user": {
                "name": "bob",
                "password": "hunter2",
                "profile": {
                    "email": "bob@example.com",
                    "api_key": "key-abc",
                },
            }
        }
        result = redact(data)
        assert result["user"]["name"] == "bob"
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["profile"]["email"] == "bob@example.com"
        assert result["user"]["profile"]["api_key"] == "[REDACTED]"
        assert "hunter2" not in str(result)
        assert "key-abc" not in str(result)

    def test_list_inside_dict(self) -> None:
        data = {
            "users": [
                {"name": "alice", "token": "tok-1"},
                {"name": "bob", "token": "tok-2"},
            ]
        }
        result = redact(data)
        assert result["users"][0]["name"] == "alice"
        assert result["users"][0]["token"] == "[REDACTED]"
        assert result["users"][1]["name"] == "bob"
        assert result["users"][1]["token"] == "[REDACTED]"
        assert "tok-1" not in str(result)
        assert "tok-2" not in str(result)

    def test_case_insensitive_keys(self) -> None:
        data = {
            "PASSWORD": "upper-secret",
            "Password": "mixed-secret",
            "password": "lower-secret",
        }
        result = redact(data)
        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Password"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"

    def test_non_sensitive_preserved(self) -> None:
        data = {
            "id": 123,
            "name": "test",
            "email": "test@example.com",
            "role": "admin",
            "created_at": "2026-01-01",
        }
        result = redact(data)
        assert result == data  # No changes

    def test_original_not_modified(self) -> None:
        data = {"username": "alice", "password": "secret123"}
        original = dict(data)
        _ = redact(data)
        assert data == original  # Original unchanged


# ---------------------------------------------------------------------------
# 3. redact headers
# ---------------------------------------------------------------------------


class TestRedactHeaders:
    def test_authorization_header_redacted(self) -> None:
        headers = {"Authorization": "Bearer my-secret-token"}
        result = redact_headers(headers)
        assert result["Authorization"] == "[REDACTED]"
        assert "my-secret-token" not in str(result)

    def test_cookie_header_redacted(self) -> None:
        headers = {"Cookie": "session=abc123"}
        result = redact_headers(headers)
        assert result["Cookie"] == "[REDACTED]"

    def test_safe_headers_preserved(self) -> None:
        headers = {
            "User-Agent": "TestClient/1.0",
            "Content-Type": "application/json",
            "X-Correlation-ID": "abc-123",
        }
        result = redact_headers(headers)
        assert result["User-Agent"] == "TestClient/1.0"
        assert result["Content-Type"] == "application/json"
        assert result["X-Correlation-ID"] == "abc-123"

    def test_case_insensitive_headers(self) -> None:
        headers = {
            "AUTHORIZATION": "Bearer secret",
            "cookie": "session=xyz",
            "Set-Cookie": "token=abc",
        }
        result = redact_headers(headers)
        assert result["AUTHORIZATION"] == "[REDACTED]"
        assert result["cookie"] == "[REDACTED]"
        assert result["Set-Cookie"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# 4. Log regression: sensitive values never in output
# ---------------------------------------------------------------------------


class TestLogRegression:
    def test_no_secret_in_redacted_log(self) -> None:
        """Redacted data must not contain any sensitive values."""
        sensitive_values = [
            "my-password-123",
            "Bearer my-access-token",
            "my-refresh-token-xyz",
            "sk-model-api-key-abc",
            "What is the meaning of life?",
            "private-preference-content",
            "memory-of-childhood",
            "step1: think about the problem",
        ]
        data = {
            "password": sensitive_values[0],
            "access_token": sensitive_values[1],
            "refresh_token": sensitive_values[2],
            "api_key": sensitive_values[3],
            "prompt": sensitive_values[4],
            "private_preference": sensitive_values[5],
            "memory_content": sensitive_values[6],
            "chain_of_thought": sensitive_values[7],
        }
        result = redact(data)
        result_str = str(result)
        for value in sensitive_values:
            assert value not in result_str, f"Sensitive value leaked: {value}"

    def test_nested_secret_not_leaked(self) -> None:
        """Secrets in nested structures must not leak."""
        data = {
            "config": {
                "database": {"host": "localhost", "secret": "db-pwd-xyz"},
                "api": {"api_key": "api-key-secret", "url": "http://localhost"},
            }
        }
        result = redact(data)
        result_str = str(result)
        assert "db-pwd-xyz" not in result_str
        assert "api-key-secret" not in result_str
        assert "localhost" in result_str  # Non-sensitive preserved
