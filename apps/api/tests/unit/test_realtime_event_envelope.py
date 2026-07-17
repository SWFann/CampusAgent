"""
Unit tests for realtime event envelope (P5-10).

Tests:
- version is fixed to "v1".
- event_id is unique.
- occurred_at/timestamp is UTC.
- sequence is monotonic.
- payload has no sensitive fields.
- error event format.
- connection.established event.
- message.created event format.
"""

from __future__ import annotations

from uuid import uuid4

from src.realtime.events import (
    build_connection_established,
    build_conversation_subscribed,
    build_error_event,
    build_message_created,
    build_pong,
    build_server_event,
    serialize_event,
)


class TestEventEnvelope:
    """Test the event envelope construction."""

    def test_version_is_v1(self) -> None:
        """Server event version is always 'v1'."""
        event = build_server_event("test.event", {"key": "value"}, sequence=1)
        assert event["version"] == "v1"

    def test_event_id_is_unique(self) -> None:
        """Each event has a unique event_id."""
        event1 = build_server_event("test", {}, sequence=1)
        event2 = build_server_event("test", {}, sequence=2)
        assert event1["event_id"] != event2["event_id"]
        assert event1["event_id"].startswith("evt_")

    def test_timestamp_is_utc(self) -> None:
        """Timestamp is UTC RFC 3339 with Z suffix."""
        event = build_server_event("test", {}, sequence=1)
        ts = event["timestamp"]
        assert ts.endswith("Z")
        # Should be parseable
        from datetime import datetime
        # Parse without milliseconds: 2026-07-17T10:30:00Z
        parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        assert parsed is not None

    def test_sequence_starts_at_1(self) -> None:
        """Sequence must be >= 1."""
        event = build_server_event("test", {}, sequence=1)
        assert event["sequence"] == 1

    def test_sequence_rejects_zero(self) -> None:
        """Sequence of 0 should raise ValueError."""
        try:
            build_server_event("test", {}, sequence=0)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass

    def test_sequence_is_monotonic(self) -> None:
        """Sequence increments within a connection."""
        events = [
            build_server_event("test", {}, sequence=i)
            for i in range(1, 6)
        ]
        sequences = [e["sequence"] for e in events]
        assert sequences == [1, 2, 3, 4, 5]

    def test_request_id_null_for_push(self) -> None:
        """Push events have request_id=None."""
        event = build_server_event("push.event", {"data": 1}, sequence=1)
        assert event["request_id"] is None

    def test_request_id_echoed_for_response(self) -> None:
        """Response events echo the client request_id."""
        event = build_server_event(
            "response.event", {}, sequence=1, request_id="client-req-123"
        )
        assert event["request_id"] == "client-req-123"

    def test_payload_has_no_sensitive_fields(self) -> None:
        """Event data should not contain sensitive fields."""
        event = build_message_created(
            message_id=uuid4(),
            conversation_id=uuid4(),
            sender_type="USER",
            sender_user_id=uuid4(),
            sender_agent_id=None,
            message_type="TEXT",
            content="Hello world",
            created_at="2026-07-17T10:00:00Z",
            sequence=1,
        )
        data = event["data"]
        # Sensitive field names should not appear in data
        sensitive = {
            "private_preference",
            "raw_preference",
            "memory_content",
            "budget_detail",
            "dietary_restriction_private",
            "personal_note",
        }
        for field in sensitive:
            assert field not in data, f"Sensitive field '{field}' found in event data"

    def test_connection_established_format(self) -> None:
        """connection.established event has correct format."""
        event = build_connection_established(
            connection_id="conn_test_001",
            sequence=1,
        )
        assert event["event"] == "connection.established"
        assert event["version"] == "v1"
        assert event["sequence"] == 1
        assert event["data"]["connection_id"] == "conn_test_001"
        assert "server_time" in event["data"]
        assert "access_token_expires_at" in event["data"]
        assert event["request_id"] is None

    def test_message_created_format(self) -> None:
        """message.created event has correct format."""
        msg_id = uuid4()
        conv_id = uuid4()
        user_id = uuid4()
        event = build_message_created(
            message_id=msg_id,
            conversation_id=conv_id,
            sender_type="USER",
            sender_user_id=user_id,
            sender_agent_id=None,
            message_type="TEXT",
            content="Test message",
            created_at="2026-07-17T10:00:00Z",
            sequence=5,
        )
        assert event["event"] == "message.created"
        assert event["version"] == "v1"
        assert event["sequence"] == 5
        assert event["request_id"] is None
        assert event["data"]["message_id"] == str(msg_id)
        assert event["data"]["conversation_id"] == str(conv_id)
        assert event["data"]["sender_type"] == "USER"
        assert event["data"]["sender_user_id"] == str(user_id)
        assert event["data"]["sender_agent_id"] is None
        assert event["data"]["message_type"] == "TEXT"
        assert event["data"]["content"] == "Test message"

    def test_error_event_format(self) -> None:
        """Error event has correct format."""
        event = build_error_event(
            error_code="CONVERSATION_PERMISSION_DENIED",
            message="Permission denied",
            sequence=3,
            request_id="client-req-456",
        )
        assert event["event"] == "error"
        assert event["version"] == "v1"
        assert event["sequence"] == 3
        assert event["data"]["code"] == "CONVERSATION_PERMISSION_DENIED"
        assert event["data"]["message"] == "Permission denied"
        assert event["request_id"] == "client-req-456"

    def test_pong_format(self) -> None:
        """pong event has correct format."""
        event = build_pong(sequence=2, request_id="client-ping-001")
        assert event["event"] == "pong"
        assert event["data"] == {}
        assert event["sequence"] == 2
        assert event["request_id"] == "client-ping-001"

    def test_serialize_event(self) -> None:
        """serialize_event produces valid JSON."""
        event = build_server_event("test", {"key": "value"}, sequence=1)
        json_str = serialize_event(event)
        assert isinstance(json_str, str)
        import json
        parsed = json.loads(json_str)
        assert parsed["event"] == "test"
        assert parsed["data"]["key"] == "value"

    def test_subscribed_format(self) -> None:
        """conversation.subscribed event has correct format."""
        conv_id = uuid4()
        event = build_conversation_subscribed(
            conversation_id=conv_id,
            sequence=2,
            request_id="client-req-789",
        )
        assert event["event"] == "conversation.subscribed"
        assert event["data"]["conversation_id"] == str(conv_id)
        assert event["data"]["success"] is True
        assert event["request_id"] == "client-req-789"
