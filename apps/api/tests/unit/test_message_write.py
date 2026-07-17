"""
Unit tests for message writing (P5-05).

Tests:
- MEMBER sends TEXT → success.
- Non-member send → fails.
- LEFT participant send → fails.
- Duplicate idempotency_key → no duplicate write.
- Normal user cannot forge SYSTEM message type (handled via sender_type).
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestMessageWrite:
    """Test message writing operations."""

    def test_member_can_send_text(self, db_client: TestClient) -> None:
        """MEMBER sends TEXT → success."""
        alice = register_and_login(
            db_client, email="msg_a1@example.edu", student_no="20266001"
        )
        bob = register_and_login(
            db_client, email="msg_b1@example.edu", student_no="20266002"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Alice sends a message
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "Hello Bob!", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["content"] == "Hello Bob!"
        assert data["message_type"] == "TEXT"
        assert data["status"] == "ACTIVE"
        assert data["sender_type"] == "USER"
        assert data["sender_user_id"] == alice["user_id"]

    def test_non_member_send_fails(self, db_client: TestClient) -> None:
        """Non-member send → fails."""
        alice = register_and_login(
            db_client, email="msg_a2@example.edu", student_no="20266003"
        )
        bob = register_and_login(
            db_client, email="msg_b2@example.edu", student_no="20266004"
        )
        carol = register_and_login(
            db_client, email="msg_c2@example.edu", student_no="20266005"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Carol (non-member) tries to send
        set_auth_cookies(db_client, carol)
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "intrusion", "message_type": "TEXT"},
            headers=auth_headers(carol["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_left_participant_send_fails(
        self, db_client: TestClient
    ) -> None:
        """LEFT participant send → fails."""
        owner = register_and_login(
            db_client, email="msg_o3@example.edu", student_no="20266006"
        )
        m1 = register_and_login(
            db_client, email="msg_m3@example.edu", student_no="20266007"
        )

        set_auth_cookies(db_client, owner)
        resp = db_client.post(
            "/api/v1/conversations",
            json={
                "title": "Left Test",
                "participant_user_ids": [m1["user_id"]],
            },
            headers=auth_headers(owner["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Owner removes m1
        db_client.delete(
            f"/api/v1/conversations/{conv_id}/participants/{m1['user_id']}",
            headers=auth_headers(owner["csrf_token"]),
        )

        # m1 tries to send after being removed
        set_auth_cookies(db_client, m1)
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "after removal", "message_type": "TEXT"},
            headers=auth_headers(m1["csrf_token"]),
        )
        assert resp.status_code == 403

    def test_idempotency_key_no_duplicate(
        self, db_client: TestClient
    ) -> None:
        """Duplicate idempotency_key → no duplicate write."""
        alice = register_and_login(
            db_client, email="msg_a4@example.edu", student_no="20266008"
        )
        bob = register_and_login(
            db_client, email="msg_b4@example.edu", student_no="20266009"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # First message with idempotency_key
        resp1 = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "first message",
                "message_type": "TEXT",
                "idempotency_key": "idem-001",
            },
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp1.status_code == 201
        msg1_id = resp1.json()["data"]["id"]

        # Second message with same idempotency_key
        resp2 = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={
                "content": "second message",
                "message_type": "TEXT",
                "idempotency_key": "idem-001",
            },
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp2.status_code == 201
        msg2_id = resp2.json()["data"]["id"]

        # Same message returned (idempotent)
        assert msg1_id == msg2_id
        assert resp2.json()["data"]["content"] == "first message"

    def test_scene_card_message_type(self, db_client: TestClient) -> None:
        """SCENE_CARD message type is accepted (placeholder for P8+)."""
        alice = register_and_login(
            db_client, email="msg_a5@example.edu", student_no="20266010"
        )
        bob = register_and_login(
            db_client, email="msg_b5@example.edu", student_no="20266011"
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
                "content": "Scene card placeholder",
                "message_type": "SCENE_CARD",
            },
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["message_type"] == "SCENE_CARD"
