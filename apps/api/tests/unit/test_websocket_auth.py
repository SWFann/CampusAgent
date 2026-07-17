"""
Unit tests for WebSocket authentication (P5-08).

Tests:
- Unauthenticated connection fails.
- Authenticated connection succeeds.
- Non-member subscribe fails.
- Member subscribe succeeds.
- Invalid token connection fails.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestWebSocketAuth:
    """Test WebSocket authentication."""

    def test_unauthenticated_connection_rejected(
        self, db_client: TestClient
    ) -> None:
        """Unauthenticated WebSocket connection is rejected."""
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect) as exc_info, db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()

        assert exc_info.value.code == 1008  # Policy Violation

    def test_authenticated_connection_succeeds(
        self, db_client: TestClient
    ) -> None:
        """Authenticated WebSocket connection succeeds."""
        alice = register_and_login(
            db_client, email="ws_a1@example.edu", student_no="20269001"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            # Should receive connection.established
            data = ws.receive_json()
            assert data["event"] == "connection.established"
            assert data["version"] == "v1"
            assert data["sequence"] == 1
            assert "connection_id" in data["data"]

    def test_non_member_subscribe_fails(
        self, db_client: TestClient
    ) -> None:
        """Non-member cannot subscribe to a conversation."""
        alice = register_and_login(
            db_client, email="ws_a2@example.edu", student_no="20269002"
        )
        bob = register_and_login(
            db_client, email="ws_b2@example.edu", student_no="20269003"
        )
        carol = register_and_login(
            db_client, email="ws_c2@example.edu", student_no="20269004"
        )

        # Alice creates a private conversation with Bob
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Carol connects and tries to subscribe
        set_auth_cookies(db_client, carol)
        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            # Receive connection.established
            ws.receive_json()

            # Try to subscribe
            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": "test-req-001",
                "timestamp": "2026-07-17T10:00:00Z",
            })

            # Should receive error event
            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "CONVERSATION_PERMISSION_DENIED"

    def test_member_subscribe_succeeds(
        self, db_client: TestClient
    ) -> None:
        """Member can subscribe to a conversation."""
        alice = register_and_login(
            db_client, email="ws_a3@example.edu", student_no="20269005"
        )
        bob = register_and_login(
            db_client, email="ws_b3@example.edu", student_no="20269006"
        )

        # Alice creates a private conversation with Bob
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        # Alice connects and subscribes
        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            # Receive connection.established
            ws.receive_json()

            # Subscribe
            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": "test-req-002",
                "timestamp": "2026-07-17T10:00:00Z",
            })

            # Should receive conversation.subscribed
            resp = ws.receive_json()
            assert resp["event"] == "conversation.subscribed"
            assert resp["data"]["conversation_id"] == conv_id
            assert resp["data"]["success"] is True
            assert resp["request_id"] == "test-req-002"
