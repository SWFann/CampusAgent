"""
Unit tests for message privacy guard (P5-07).

Tests:
- content with sensitive field name → rejected.
- payload with nested sensitive field → rejected (via service-level check).
- Sensitive field names:
  - private_preference
  - raw_preference
  - memory_content
  - budget_detail
  - dietary_restriction_private
  - personal_note
"""

from __future__ import annotations

from starlette.testclient import TestClient

from src.modules.conversations.exceptions import MessageSensitiveContentError
from src.modules.conversations.service import _check_sensitive_content
from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestMessagePrivacy:
    """Test that private preferences are blocked from messages."""

    # Sensitive field names to test
    SENSITIVE_FIELDS = [
        "private_preference",
        "raw_preference",
        "memory_content",
        "budget_detail",
        "dietary_restriction_private",
        "personal_note",
    ]

    def test_content_with_sensitive_field_rejected(
        self, db_client: TestClient
    ) -> None:
        """content containing a sensitive field name → rejected (422)."""
        alice = register_and_login(
            db_client, email="pv_a1@example.edu", student_no="20268001"
        )
        bob = register_and_login(
            db_client, email="pv_b1@example.edu", student_no="20268002"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Try to send a message with a sensitive field name in content
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "my private_preference is vegan",
                "message_type": "TEXT",
            },
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "MESSAGE_SENSITIVE_CONTENT"

    def test_each_sensitive_field_rejected(self) -> None:
        """Each sensitive field name in content is rejected."""
        for field in self.SENSITIVE_FIELDS:
            try:
                _check_sensitive_content(field, None)
                raise AssertionError(
                    f"Expected MessageSensitiveContentError for field: {field}"
                )
            except MessageSensitiveContentError:
                pass  # Expected

    def test_payload_with_sensitive_field_rejected(self) -> None:
        """payload_json with a sensitive field key → rejected."""
        import json

        for field in self.SENSITIVE_FIELDS:
            payload = json.dumps({field: "some value"})
            try:
                _check_sensitive_content(None, payload)
                raise AssertionError(
                    f"Expected MessageSensitiveContentError for payload field: {field}"
                )
            except MessageSensitiveContentError:
                pass  # Expected

    def test_safe_content_accepted(self) -> None:
        """Normal content without sensitive fields is accepted."""
        _check_sensitive_content("Hello, how are you?", None)
        _check_sensitive_content("Let's eat dinner tonight", None)

    def test_safe_payload_accepted(self) -> None:
        """Normal payload without sensitive fields is accepted."""
        import json

        _check_sensitive_content(None, json.dumps({"scene_type": "dinner"}))
        _check_sensitive_content(None, json.dumps({"location": "cafeteria"}))

    def test_normal_message_succeeds(self, db_client: TestClient) -> None:
        """Normal message without sensitive content succeeds."""
        alice = register_and_login(
            db_client, email="pv_a2@example.edu", student_no="20268003"
        )
        bob = register_and_login(
            db_client, email="pv_b2@example.edu", student_no="20268004"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "今晚一起吃饭吗？",
                "message_type": "TEXT",
            },
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["content"] == "今晚一起吃饭吗？"

    def test_case_insensitive_detection(self) -> None:
        """Sensitive field detection is case-insensitive in content."""
        for field in self.SENSITIVE_FIELDS:
            # Test uppercase
            try:
                _check_sensitive_content(field.upper(), None)
                raise AssertionError(
                    f"Expected MessageSensitiveContentError for uppercase: {field.upper()}"
                )
            except MessageSensitiveContentError:
                pass
