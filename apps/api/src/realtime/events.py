"""
Realtime event envelope construction for CampusAgent WebSocket.

This module builds the server-side event envelope as defined in
WEBSOCKET_CONTRACT.md §2.2:

```json
{
  "event": "connection.established",
  "data": {...},
  "version": "v1",
  "event_id": "evt_001",
  "sequence": 1,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": null
}
```

Privacy requirements:
- Events do NOT contain message content, payload, email, student_no,
  password_hash, token, or session info.
- Events only store IDs, types, and status — no private content.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


def _utc_timestamp() -> str:
    """Return UTC RFC 3339 timestamp with second precision and Z suffix."""
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt_{secrets.token_hex(12)}"


def build_server_event(
    event: str,
    data: dict[str, Any],
    sequence: int,
    *,
    request_id: str | UUID | None = None,
    event_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a server-side event envelope.

    Args:
        event: Event name (e.g., "message.created").
        data: Event data dict.
        sequence: Per-connection sequence number (>= 1).
        request_id: Client request_id for responses, None for pushes.
        event_id: Optional explicit event_id; auto-generated if None.
        timestamp: Optional explicit timestamp; auto-generated if None.

    Returns:
        A dict matching the WEBSOCKET_CONTRACT.md v1.0 server envelope.
    """
    if sequence < 1:
        raise ValueError("sequence must be >= 1")

    return {
        "event": event,
        "data": data,
        "version": "v1",
        "event_id": event_id or _generate_event_id(),
        "sequence": sequence,
        "timestamp": timestamp or _utc_timestamp(),
        "request_id": str(request_id) if request_id else None,
    }


def build_client_command(
    event: str,
    data: dict[str, Any],
    request_id: str | UUID,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build a client-side command envelope (for testing).

    Args:
        event: Command name (e.g., "conversation.subscribe").
        data: Command data dict.
        request_id: Client-generated UUID v4 request identifier.
        timestamp: Optional explicit timestamp.

    Returns:
        A dict matching the WEBSOCKET_CONTRACT.md v1.0 client envelope.
    """
    return {
        "event": event,
        "data": data,
        "version": "v1",
        "request_id": str(request_id),
        "timestamp": timestamp or _utc_timestamp(),
    }


def build_error_event(
    error_code: str,
    message: str,
    sequence: int,
    *,
    request_id: str | UUID | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an error event envelope.

    Error events follow the same server envelope shape with event="error".
    """
    data: dict[str, Any] = {
        "code": error_code,
        "message": message,
    }
    if details:
        data["details"] = details

    return build_server_event(
        event="error",
        data=data,
        sequence=sequence,
        request_id=request_id,
    )


def serialize_event(event: dict[str, Any]) -> str:
    """Serialize an event dict to a JSON string."""
    return json.dumps(event, ensure_ascii=False, default=str)


def build_connection_established(
    connection_id: str,
    sequence: int,
    *,
    access_token_expires_at: str | None = None,
) -> dict[str, Any]:
    """Build a connection.established event."""
    data = {
        "connection_id": connection_id,
        "server_time": _utc_timestamp(),
        "access_token_expires_at": access_token_expires_at or _utc_timestamp(),
    }
    return build_server_event(
        event="connection.established",
        data=data,
        sequence=sequence,
    )


def build_conversation_subscribed(
    conversation_id: UUID | str,
    sequence: int,
    request_id: str | UUID,
) -> dict[str, Any]:
    """Build a conversation.subscribed event."""
    return build_server_event(
        event="conversation.subscribed",
        data={
            "conversation_id": str(conversation_id),
            "success": True,
        },
        sequence=sequence,
        request_id=request_id,
    )


def build_conversation_unsubscribed(
    conversation_id: UUID | str,
    sequence: int,
    request_id: str | UUID,
) -> dict[str, Any]:
    """Build a conversation.unsubscribed event."""
    return build_server_event(
        event="conversation.unsubscribed",
        data={
            "conversation_id": str(conversation_id),
            "success": True,
        },
        sequence=sequence,
        request_id=request_id,
    )


def build_message_created(
    message_id: UUID | str,
    conversation_id: UUID | str,
    sender_type: str,
    sender_user_id: UUID | str | None,
    sender_agent_id: UUID | str | None,
    message_type: str,
    content: str | None,
    created_at: str,
    sequence: int,
) -> dict[str, Any]:
    """Build a message.created event.

    NOTE: content is the authorized conversation-visible projection.
    Private preference fields must never be included.
    """
    return build_server_event(
        event="message.created",
        data={
            "message_id": str(message_id),
            "conversation_id": str(conversation_id),
            "sender_type": sender_type,
            "sender_user_id": str(sender_user_id) if sender_user_id else None,
            "sender_agent_id": str(sender_agent_id) if sender_agent_id else None,
            "message_type": message_type,
            "content": content,
            "created_at": created_at,
        },
        sequence=sequence,
    )


def build_pong(sequence: int, request_id: str | UUID) -> dict[str, Any]:
    """Build a pong event."""
    return build_server_event(
        event="pong",
        data={},
        sequence=sequence,
        request_id=request_id,
    )
