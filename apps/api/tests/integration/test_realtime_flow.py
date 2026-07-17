"""
Integration tests for the realtime WebSocket flow (P5-13).

Tests verify the complete end-to-end WebSocket journeys:
- WebSocket connection.established delivery
- conversation.subscribe → conversation.subscribed confirmation
- conversation.unsubscribe → conversation.unsubscribed confirmation
- ping → pong heartbeat
- Non-member subscription fails with error event
- HTTP backfill after simulated disconnect
- Duplicate event_id deduplication
- Message creation flow with WebSocket subscription
"""

from __future__ import annotations

import uuid

from starlette.testclient import TestClient

from src.realtime.connection_manager import EventDedupCache
from src.realtime.events import (
    build_message_created,
)
from tests.unit.helpers_p4 import (
    auth_headers,
    register_and_login,
    set_auth_cookies,
)


class TestRealtimeConnectionFlow:
    """End-to-end WebSocket connection flow."""

    def test_connection_established_sequence(
        self, db_client: TestClient
    ) -> None:
        """Authenticated connection receives connection.established first."""
        alice = register_and_login(
            db_client, email="rt_flow_a@example.edu", student_no="20268001"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            data = ws.receive_json()
            assert data["event"] == "connection.established"
            assert data["version"] == "v1"
            assert data["sequence"] == 1
            assert "connection_id" in data["data"]
            assert "server_time" in data["data"]
            assert "access_token_expires_at" in data["data"]

    def test_ping_pong_flow(self, db_client: TestClient) -> None:
        """Client ping → server pong with request_id echo."""
        alice = register_and_login(
            db_client, email="rt_flow_b@example.edu", student_no="20268002"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            # Consume connection.established
            ws.receive_json()

            # Send ping
            req_id = str(uuid.uuid4())
            ws.send_json({
                "event": "ping",
                "data": {},
                "version": "v1",
                "request_id": req_id,
                "timestamp": "2026-07-17T10:00:00Z",
            })

            # Receive pong
            resp = ws.receive_json()
            assert resp["event"] == "pong"
            assert resp["request_id"] == req_id
            assert resp["data"] == {}
            assert resp["version"] == "v1"
            assert resp["sequence"] >= 2

    def test_subscribe_unsubscribe_flow(
        self, db_client: TestClient
    ) -> None:
        """Full subscribe → unsubscribe cycle with confirmations."""
        alice = register_and_login(
            db_client, email="rt_flow_c@example.edu", student_no="20268003"
        )
        bob = register_and_login(
            db_client, email="rt_flow_d@example.edu", student_no="20268004"
        )

        # Create a private conversation
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Connect as Bob and subscribe
        set_auth_cookies(db_client, bob)
        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            # Subscribe
            sub_req_id = str(uuid.uuid4())
            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": sub_req_id,
                "timestamp": "2026-07-17T10:00:00Z",
            })

            resp = ws.receive_json()
            assert resp["event"] == "conversation.subscribed"
            assert resp["data"]["conversation_id"] == conv_id
            assert resp["data"]["success"] is True
            assert resp["request_id"] == sub_req_id

            # Unsubscribe
            unsub_req_id = str(uuid.uuid4())
            ws.send_json({
                "event": "conversation.unsubscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": unsub_req_id,
                "timestamp": "2026-07-17T10:01:00Z",
            })

            resp = ws.receive_json()
            assert resp["event"] == "conversation.unsubscribed"
            assert resp["data"]["conversation_id"] == conv_id
            assert resp["data"]["success"] is True
            assert resp["request_id"] == unsub_req_id


class TestRealtimePermissionFlow:
    """Test permission enforcement in WebSocket subscription."""

    def test_non_member_subscribe_denied(
        self, db_client: TestClient
    ) -> None:
        """A non-member cannot subscribe to a conversation."""
        alice = register_and_login(
            db_client, email="rt_perm_a@example.edu", student_no="20268010"
        )
        bob = register_and_login(
            db_client, email="rt_perm_b@example.edu", student_no="20268011"
        )
        carol = register_and_login(
            db_client, email="rt_perm_c@example.edu", student_no="20268012"
        )

        # Alice creates a private conversation with Bob
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Carol connects and tries to subscribe
        set_auth_cookies(db_client, carol)
        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": str(uuid.uuid4()),
                "timestamp": "2026-07-17T10:00:00Z",
            })

            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "CONVERSATION_PERMISSION_DENIED"

    def test_subscribe_to_nonexistent_conversation(
        self, db_client: TestClient
    ) -> None:
        """Subscribing to a non-existent conversation returns error."""
        alice = register_and_login(
            db_client, email="rt_perm_d@example.edu", student_no="20268013"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            fake_conv_id = str(uuid.uuid4())
            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": fake_conv_id},
                "version": "v1",
                "request_id": str(uuid.uuid4()),
                "timestamp": "2026-07-17T10:00:00Z",
            })

            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "CONVERSATION_NOT_FOUND"

    def test_invalid_json_returns_error(
        self, db_client: TestClient
    ) -> None:
        """Invalid JSON message returns WS_INVALID_MESSAGE error."""
        alice = register_and_login(
            db_client, email="rt_perm_e@example.edu", student_no="20268014"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            ws.send_text("not valid json")

            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "WS_INVALID_MESSAGE"

    def test_missing_event_returns_error(
        self, db_client: TestClient
    ) -> None:
        """Message without event field returns WS_MISSING_EVENT error."""
        alice = register_and_login(
            db_client, email="rt_perm_f@example.edu", student_no="20268015"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            ws.send_json({"data": {}, "version": "v1"})

            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "WS_MISSING_EVENT"

    def test_unknown_event_returns_error(
        self, db_client: TestClient
    ) -> None:
        """Unknown event returns WS_UNKNOWN_EVENT error."""
        alice = register_and_login(
            db_client, email="rt_perm_g@example.edu", student_no="20268016"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            ws.send_json({
                "event": "some.unknown.event",
                "data": {},
                "version": "v1",
                "request_id": str(uuid.uuid4()),
                "timestamp": "2026-07-17T10:00:00Z",
            })

            resp = ws.receive_json()
            assert resp["event"] == "error"
            assert resp["data"]["code"] == "WS_UNKNOWN_EVENT"


class TestRealtimeBackfillFlow:
    """Test HTTP backfill after simulated disconnect."""

    def test_http_backfill_after_disconnect(
        self, db_client: TestClient
    ) -> None:
        """After WebSocket disconnect, HTTP API provides missed messages."""
        alice = register_and_login(
            db_client, email="rt_bf_a@example.edu", student_no="20268020"
        )
        bob = register_and_login(
            db_client, email="rt_bf_b@example.edu", student_no="20268021"
        )

        # Create conversation and send initial messages
        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Alice sends 2 messages
        db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "before disconnect 1", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "before disconnect 2", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )

        # Bob reads via HTTP (simulating backfill after reconnect)
        set_auth_cookies(db_client, bob)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        messages = resp.json()["data"]["messages"]
        assert len(messages) == 2

        # Simulate: more messages sent while Bob was "disconnected"
        set_auth_cookies(db_client, alice)
        for i in range(3):
            db_client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                json={"content": f"missed-{i}", "message_type": "TEXT"},
                headers=auth_headers(alice["csrf_token"]),
            )

        # Bob "reconnects" and does HTTP backfill
        set_auth_cookies(db_client, bob)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        messages = resp.json()["data"]["messages"]
        assert len(messages) == 5  # 2 + 3 = 5 total

        # Verify message_id dedup works (same message_ids returned)
        first_backfill_ids = {m["id"] for m in messages}

        # Second fetch should return same message_ids
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        second_ids = {m["id"] for m in resp.json()["data"]["messages"]}
        assert first_backfill_ids == second_ids

    def test_event_dedup_in_backfill_scenario(
        self, db_client: TestClient
    ) -> None:
        """Event dedup cache prevents duplicate processing during backfill."""
        alice = register_and_login(
            db_client, email="rt_bf_c@example.edu", student_no="20268022"
        )
        bob = register_and_login(
            db_client, email="rt_bf_d@example.edu", student_no="20268023"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Send a message
        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "dedup test", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        msg = resp.json()["data"]

        # Simulate receiving duplicate event_ids via dedup cache
        cache = EventDedupCache()
        event_id = "evt_duplicate_001"

        # First time — not seen
        assert not cache.seen(event_id)
        cache.add(event_id)

        # Second time — seen (duplicate)
        assert cache.seen(event_id)

        # HTTP backfill returns same message_id (business dedup)
        set_auth_cookies(db_client, bob)
        resp = db_client.get(f"/api/v1/conversations/{conv_id}/messages")
        messages = resp.json()["data"]["messages"]
        assert len(messages) == 1
        assert messages[0]["id"] == msg["id"]


class TestRealtimeEnvelopeFlow:
    """Test event envelope compliance in an integration context."""

    def test_message_created_envelope_shape(
        self, db_client: TestClient
    ) -> None:
        """message.created event envelope matches WEBSOCKET_CONTRACT.md §4.3.1."""
        alice = register_and_login(
            db_client, email="rt_env_a@example.edu", student_no="20268030"
        )
        bob = register_and_login(
            db_client, email="rt_env_b@example.edu", student_no="20268031"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        resp = db_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "envelope test", "message_type": "TEXT"},
            headers=auth_headers(alice["csrf_token"]),
        )
        msg = resp.json()["data"]

        # Build a message.created event (simulating server-side)
        event = build_message_created(
            message_id=msg["id"],
            conversation_id=conv_id,
            sender_type="USER",
            sender_user_id=alice["user_id"],
            sender_agent_id=None,
            message_type="TEXT",
            content="envelope test",
            created_at=msg["created_at"],
            sequence=1,
        )

        # Verify envelope shape per §2.2
        assert event["event"] == "message.created"
        assert event["version"] == "v1"
        assert "event_id" in event
        assert event["sequence"] == 1
        assert "timestamp" in event
        assert event["request_id"] is None  # push events have null request_id

        # Verify data fields per §4.3.1
        data = event["data"]
        assert data["message_id"] == msg["id"]
        assert data["conversation_id"] == conv_id
        assert data["sender_type"] == "USER"
        assert data["sender_user_id"] == alice["user_id"]
        assert data["sender_agent_id"] is None
        assert data["message_type"] == "TEXT"
        assert data["content"] == "envelope test"
        assert "created_at" in data

    def test_error_envelope_shape(
        self, db_client: TestClient
    ) -> None:
        """Error event envelope matches WEBSOCKET_CONTRACT.md §4.7.1."""
        alice = register_and_login(
            db_client, email="rt_env_c@example.edu", student_no="20268032"
        )
        bob = register_and_login(
            db_client, email="rt_env_d@example.edu", student_no="20268033"
        )

        set_auth_cookies(db_client, alice)
        resp = db_client.post(
            "/api/v1/conversations/private",
            json={"target_user_id": bob["user_id"]},
            headers=auth_headers(alice["csrf_token"]),
        )
        conv_id = resp.json()["data"]["id"]

        # Carol tries to subscribe (non-member)
        carol = register_and_login(
            db_client, email="rt_env_e@example.edu", student_no="20268034"
        )
        set_auth_cookies(db_client, carol)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            ws.receive_json()  # connection.established

            req_id = str(uuid.uuid4())
            ws.send_json({
                "event": "conversation.subscribe",
                "data": {"conversation_id": conv_id},
                "version": "v1",
                "request_id": req_id,
                "timestamp": "2026-07-17T10:00:00Z",
            })

            resp = ws.receive_json()

            # Verify error envelope per §4.7.1
            assert resp["event"] == "error"
            assert resp["version"] == "v1"
            assert "event_id" in resp
            assert resp["sequence"] >= 2
            assert "timestamp" in resp
            assert resp["request_id"] == req_id  # echoes client request_id

            # Verify error data
            data = resp["data"]
            assert "code" in data
            assert "message" in data
            assert data["code"] == "CONVERSATION_PERMISSION_DENIED"

    def test_connection_established_envelope(
        self, db_client: TestClient
    ) -> None:
        """connection.established matches WEBSOCKET_CONTRACT.md §4.1.1."""
        alice = register_and_login(
            db_client, email="rt_env_f@example.edu", student_no="20268035"
        )
        set_auth_cookies(db_client, alice)

        with db_client.websocket_connect(
            "/api/v1/ws",
            headers={"origin": "http://localhost:3000"},
        ) as ws:
            resp = ws.receive_json()

            # Verify per §4.1.1
            assert resp["event"] == "connection.established"
            assert resp["version"] == "v1"
            assert resp["sequence"] == 1
            assert resp["request_id"] is None  # push event

            data = resp["data"]
            assert "connection_id" in data
            assert "server_time" in data
            assert "access_token_expires_at" in data
