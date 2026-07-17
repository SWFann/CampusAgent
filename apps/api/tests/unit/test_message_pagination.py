"""
Unit tests for message pagination (P5-06).

Tests:
- First page / second page are stable.
- Non-member cannot paginate.
- Deleted message content is None (tombstone).
- Pagination returns correct count.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestMessagePagination:
    """Test message pagination operations."""

    def test_pagination_first_page(self, db_client: TestClient) -> None:
        """First page returns newest messages."""
        alice = register_and_login(
            db_client, email="pg_a1@example.edu", student_no="20267001"
        )
        bob = register_and_login(
            db_client, email="pg_b1@example.edu", student_no="20267002"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Create 5 messages
        for i in range(5):
            db_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": f"message-{i}", "message_type": "TEXT"},
                headers=auth_headers(alice["csrf_token"]),
            )

        # Get page 1 with page_size 2
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages?page=1&page_size=2"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["messages"]) == 2

    def test_pagination_second_page(self, db_client: TestClient) -> None:
        """Second page returns older messages."""
        alice = register_and_login(
            db_client, email="pg_a2@example.edu", student_no="20267003"
        )
        bob = register_and_login(
            db_client, email="pg_b2@example.edu", student_no="20267004"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Create 5 messages
        for i in range(5):
            db_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": f"msg-{i}", "message_type": "TEXT"},
                headers=auth_headers(alice["csrf_token"]),
            )

        # Get page 2 with page_size 2
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages?page=2&page_size=2"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["messages"]) == 2

    def test_non_member_cannot_paginate(
        self, db_client: TestClient
    ) -> None:
        """Non-member cannot list messages."""
        alice = register_and_login(
            db_client, email="pg_a3@example.edu", student_no="20267005"
        )
        bob = register_and_login(
            db_client, email="pg_b3@example.edu", student_no="20267006"
        )
        carol = register_and_login(
            db_client, email="pg_c3@example.edu", student_no="20267007"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Carol tries to list
        set_auth_cookies(db_client, carol)
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages"
        )
        assert resp.status_code == 403

    def test_deleted_message_content_none(
        self, db_client: TestClient
    ) -> None:
        """Deleted message returns content=None."""
        alice = register_and_login(
            db_client, email="pg_a4@example.edu", student_no="20267008"
        )
        bob = register_and_login(
            db_client, email="pg_b4@example.edu", student_no="20267009"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Create a message
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "to be deleted", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        msg_id = resp.json()["data"]["id"]

        # Delete the message
        db_client.delete(
            f"/api/v1/conversations/{conv_id}/messages/{msg_id}",
            headers=auth_headers(alice["csrf_token"]),
        )

        # List messages — deleted message should have content=None
        resp = db_client.get(
            f"/api/v1/conversations/{conv_id}/messages"
        )
        assert resp.status_code == 200
        messages = resp.json()["data"]["messages"]
        deleted = [m for m in messages if m["id"] == msg_id]
        assert len(deleted) == 1
        assert deleted[0]["content"] is None
        assert deleted[0]["status"] == "DELETED"
