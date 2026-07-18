"""P12-10: WebSocket stability tests.

Verifies P5 WebSocket behaviour under adverse conditions:
- Unauthenticated connection rejected (1008).
- Invalid token connection rejected (1008).
- Missing origin header rejected.
- Normal connection receives connection.established ack.
- Invalid message format does not crash the server.
- Disconnection cleans up without errors.
- Multiple connections can coexist.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)

ORIGIN = {"origin": "http://localhost:3000"}


# ---------------------------------------------------------------------------
# 1. Authentication failures
# ---------------------------------------------------------------------------


class TestWebSocketAuthFailures:
    def test_unauthenticated_rejected(self, db_client: TestClient):
        with pytest.raises(WebSocketDisconnect) as exc, db_client.websocket_connect(
            "/api/v1/ws", headers=ORIGIN
        ) as ws:
            ws.receive_json()
        assert exc.value.code == 1008

    def test_invalid_token_rejected(self, db_client: TestClient):
        with pytest.raises(WebSocketDisconnect) as exc, db_client.websocket_connect(
            "/api/v1/ws",
            headers={**ORIGIN, "Cookie": "access_token=invalid.token.here"},
        ) as ws:
            ws.receive_json()
        assert exc.value.code == 1008

    def test_missing_origin_rejected(self, db_client: TestClient):
        """Connections without an origin header are rejected."""
        with pytest.raises(WebSocketDisconnect) as exc, db_client.websocket_connect(
            "/api/v1/ws"
        ) as ws:
            ws.receive_json()
        assert exc.value.code == 1008


# ---------------------------------------------------------------------------
# 2. Normal connection lifecycle
# ---------------------------------------------------------------------------


class TestWebSocketConnectionLifecycle:
    def test_connection_established_ack(self, db_client: TestClient):
        creds = register_and_login(
            db_client, email="p12ws-ack@example.edu", student_no="20261001"
        )
        set_auth_cookies(db_client, creds)
        with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws:
            data = ws.receive_json()
            assert data["event"] == "connection.established"
            assert data["version"] == "v1"
            assert data["sequence"] == 1

    def test_disconnect_cleans_up(self, db_client: TestClient):
        """Disconnecting should not raise."""
        creds = register_and_login(
            db_client, email="p12ws-disc@example.edu", student_no="20261002"
        )
        set_auth_cookies(db_client, creds)
        with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws:
            ws.receive_json()
        # Exiting the context manager closes the connection cleanly.

    def test_multiple_connections_coexist(self, db_client: TestClient):
        creds = register_and_login(
            db_client, email="p12ws-multi@example.edu", student_no="20261003"
        )
        set_auth_cookies(db_client, creds)
        with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws1:
            ws1.receive_json()
            with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws2:
                ws2.receive_json()
                # Both connections are alive.


# ---------------------------------------------------------------------------
# 3. Invalid message handling
# ---------------------------------------------------------------------------


class TestWebSocketInvalidMessages:
    def test_invalid_json_does_not_crash(self, db_client: TestClient):
        """Sending invalid text should not crash the server."""
        creds = register_and_login(
            db_client, email="p12ws-inv@example.edu", student_no="20261004"
        )
        set_auth_cookies(db_client, creds)
        with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws:
            ws.receive_json()
            # Send invalid text — server should respond with error, not crash.
            ws.send_text("not-valid-json{{{")
            try:
                resp = ws.receive_json()
                assert resp["event"] == "error"
            except WebSocketDisconnect:
                # Disconnecting on invalid input is also acceptable.
                pass

    def test_unknown_event_returns_error(self, db_client: TestClient):
        creds = register_and_login(
            db_client, email="p12ws-unk@example.edu", student_no="20261005"
        )
        set_auth_cookies(db_client, creds)
        with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws:
            ws.receive_json()
            ws.send_json({
                "event": "totally.unknown.event",
                "data": {},
                "version": "v1",
                "request_id": "req-unk-001",
                "timestamp": "2026-07-18T10:00:00Z",
            })
            try:
                resp = ws.receive_json()
                assert resp["event"] == "error"
            except WebSocketDisconnect:
                pass


# ---------------------------------------------------------------------------
# 4. Non-member subscribe rejection
# ---------------------------------------------------------------------------


class TestWebSocketNonMemberSubscribe:
    def test_non_member_subscribe_denied(self, db_client: TestClient):
        alice = register_and_login(
            db_client, email="p12ws-a@example.edu", student_no="20261010"
        )
        bob = register_and_login(
            db_client, email="p12ws-b@example.edu", student_no="20261011"
        )
        carol = register_and_login(
            db_client, email="p12ws-c@example.edu", student_no="20261012"
        )
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        assert resp.status_code == 201
        conv_id = resp.json()["data"]["id"]

        set_auth_cookies(db_client, carol)
        with db_client.websocket_connect("/api/v1/ws", headers=ORIGIN) as ws:
            ws.receive_json()
            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": "req-nm-001",
                "timestamp": "2026-07-18T10:00:00Z",
            })
            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "CONVERSATION_PERMISSION_DENIED"
