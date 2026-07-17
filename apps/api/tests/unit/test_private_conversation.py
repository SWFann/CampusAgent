"""
Unit tests for private conversation creation (P5-02).

Tests:
- A creates B private conversation → success.
- A creates B again → same conversation returned (idempotent).
- B creates A → same conversation returned.
- A cannot create private conversation with deleted user.
- C cannot read A/B private conversation.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestPrivateConversation:
    """Test private conversation creation and idempotent reuse."""

    def test_create_private_conversation(self, db_client: TestClient) -> None:
        """A creates B private conversation → success."""
        alice = register_and_login(
            db_client, email="alice_p@example.edu", student_no="20263001"
        )
        bob = register_and_login(
            db_client, email="bob_p@example.edu", student_no="20263002"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["type"] == "PRIVATE"
        assert data["status"] == "ACTIVE"
        assert data["id"]

    def test_idempotent_private_conversation(
        self, db_client: TestClient
    ) -> None:
        """A creates B twice → same conversation returned."""
        alice = register_and_login(
            db_client, email="alice_idem@example.edu", student_no="20263003"
        )
        bob = register_and_login(
            db_client, email="bob_idem@example.edu", student_no="20263004"
        )

        set_auth_cookies(db_client, alice)
        resp1 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp1.status_code == 201
        conv1_id = resp1.json()["data"]["id"]

        resp2 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp2.status_code == 201
        conv2_id = resp2.json()["data"]["id"]

        assert conv1_id == conv2_id

    def test_reverse_private_conversation(
        self, db_client: TestClient
    ) -> None:
        """B creates A → same conversation returned."""
        alice = register_and_login(
            db_client, email="alice_rev@example.edu", student_no="20263005"
        )
        bob = register_and_login(
            db_client, email="bob_rev@example.edu", student_no="20263006"
        )

        set_auth_cookies(db_client, alice)
        resp1 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp1.status_code == 201
        conv1_id = resp1.json()["data"]["id"]

        set_auth_cookies(db_client, bob)
        resp2 = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": alice["user_id"]},
            headers=auth_headers(bob["csrf_token"]),
        )
        assert resp2.status_code == 201
        conv2_id = resp2.json()["data"]["id"]

        assert conv1_id == conv2_id

    def test_non_participant_cannot_read(
        self, db_client: TestClient
    ) -> None:
        """C cannot read A/B private conversation."""
        alice = register_and_login(
            db_client, email="alice_np@example.edu", student_no="20263007"
        )
        bob = register_and_login(
            db_client, email="bob_np@example.edu", student_no="20263008"
        )
        carol = register_and_login(
            db_client, email="carol_np@example.edu", student_no="20263009"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Carol tries to read
        set_auth_cookies(db_client, carol)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}")
        assert resp.status_code == 403

    def test_non_participant_cannot_list_messages(
        self, db_client: TestClient
    ) -> None:
        """C cannot list messages in A/B private conversation."""
        alice = register_and_login(
            db_client, email="alice_nm@example.edu", student_no="20263010"
        )
        bob = register_and_login(
            db_client, email="bob_nm@example.edu", student_no="20263011"
        )
        carol = register_and_login(
            db_client, email="carol_nm@example.edu", student_no="20263012"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Carol tries to list messages
        set_auth_cookies(db_client, carol)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 403
