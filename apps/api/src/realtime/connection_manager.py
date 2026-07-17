"""
WebSocket connection manager for CampusAgent.

Manages WebSocket connections, subscriptions, and event delivery.

Design principles:
- Each connection has a unique connection_id and per-connection sequence.
- Subscriptions are per-conversation, with resource-level authorization.
- Events are delivered via the pubsub backend.
- No sensitive data (token, cookie, message content) is logged.
- Disconnected clients are cleaned up.
"""

from __future__ import annotations

import logging
import secrets
from collections import OrderedDict
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from ..modules.conversations.permissions import permission_service
from ..modules.conversations.repository import (
    ConversationParticipantRepository,
    ConversationRepository,
)
from ..modules.users.models import User
from .events import (
    build_connection_established,
    build_conversation_subscribed,
    build_conversation_unsubscribed,
    build_error_event,
    build_pong,
    serialize_event,
)
from .pubsub import PubSubBackend, default_pubsub

logger = logging.getLogger("campus_agent.realtime.connection")

# Event dedup cache (bounded) per WEBSOCKET_CONTRACT.md §6.4
MAX_DEDUP_CACHE_SIZE = 1000
MAX_DEDUP_CACHE_AGE_SECONDS = 24 * 60 * 60  # 24 hours


class EventDedupCache:
    """Bounded cache for event_id deduplication.

    Per WEBSOCKET_CONTRACT.md §6.4:
    - Max 1000 event_ids
    - Max 24 hours
    - FIFO eviction when size limit reached
    """

    def __init__(self, max_size: int = MAX_DEDUP_CACHE_SIZE) -> None:
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._max_size = max_size

    def seen(self, event_id: str) -> bool:
        """Check if an event_id has been seen."""
        return event_id in self._cache

    def add(self, event_id: str) -> None:
        """Add an event_id to the cache."""
        if event_id in self._cache:
            # Move to end (most recently seen)
            self._cache.move_to_end(event_id)
            return

        self._cache[event_id] = 0.0  # timestamp not tracked in MVP
        if len(self._cache) > self._max_size:
            # FIFO eviction
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()


class ConnectionInfo:
    """Per-connection state."""

    def __init__(self, connection_id: str, user: User, websocket: WebSocket) -> None:
        self.connection_id = connection_id
        self.user = user
        self.websocket = websocket
        self.sequence = 0
        self.subscriptions: set[UUID] = set()  # conversation_ids
        self.dedup_cache = EventDedupCache()

    def next_sequence(self) -> int:
        """Get the next sequence number for this connection."""
        self.sequence += 1
        return self.sequence


class ConnectionManager:
    """Manages WebSocket connections and event delivery."""

    def __init__(self, pubsub: PubSubBackend | None = None) -> None:
        self._connections: dict[str, ConnectionInfo] = {}
        self._pubsub = pubsub or default_pubsub

    async def connect(
        self, websocket: WebSocket, user: User
    ) -> ConnectionInfo:
        """Accept a WebSocket connection and send connection.established.

        Returns the ConnectionInfo for this connection.
        """
        connection_id = f"conn_{secrets.token_hex(12)}"
        await websocket.accept()

        info = ConnectionInfo(connection_id, user, websocket)
        self._connections[connection_id] = info

        # Send connection.established (sequence=1)
        event = build_connection_established(
            connection_id=connection_id,
            sequence=info.next_sequence(),
        )
        await websocket.send_text(serialize_event(event))

        logger.info(
            "ws.connection.established",
            extra={
                "connection_id": connection_id,
                "user_id": str(user.id),
            },
        )

        return info

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect and clean up a connection."""
        info = self._connections.pop(connection_id, None)
        if info is None:
            return

        # Unsubscribe from all pubsub channels
        for conv_id in info.subscriptions:
            channel = f"conversation:{conv_id}"
            self._pubsub.unsubscribe(channel, self._make_handler(connection_id))

        logger.info(
            "ws.connection.closed",
            extra={
                "connection_id": connection_id,
                "user_id": str(info.user.id),
            },
        )

    async def handle_subscribe(
        self,
        info: ConnectionInfo,
        conversation_id: UUID,
        request_id: str,
        db_session: Any,
    ) -> bool:
        """Handle a conversation.subscribe command.

        Returns True on success, False on failure.
        """
        # Resource-level authorization: check if user is an active participant
        conv_repo = ConversationRepository(db_session)
        conv = conv_repo.get_active_by_id(conversation_id)
        if conv is None:
            await self._send_error(
                info,
                "CONVERSATION_NOT_FOUND",
                "会话不存在",
                request_id,
            )
            return False

        participant = ConversationParticipantRepository(db_session).get_active_by_conversation_user(
            conversation_id, info.user.id
        )
        if not permission_service.can_subscribe(conv, info.user, participant):
            await self._send_error(
                info,
                "CONVERSATION_PERMISSION_DENIED",
                "无权订阅此会话",
                request_id,
            )
            return False

        # Subscribe to pubsub channel
        channel = f"conversation:{conversation_id}"
        handler = self._make_handler(info.connection_id)
        self._pubsub.subscribe(channel, handler)
        info.subscriptions.add(conversation_id)

        # Send conversation.subscribed confirmation
        event = build_conversation_subscribed(
            conversation_id=conversation_id,
            sequence=info.next_sequence(),
            request_id=request_id,
        )
        await info.websocket.send_text(serialize_event(event))

        logger.info(
            "ws.conversation.subscribed",
            extra={
                "connection_id": info.connection_id,
                "conversation_id": str(conversation_id),
                "user_id": str(info.user.id),
            },
        )
        return True

    async def handle_unsubscribe(
        self,
        info: ConnectionInfo,
        conversation_id: UUID,
        request_id: str,
    ) -> bool:
        """Handle a conversation.unsubscribe command."""
        channel = f"conversation:{conversation_id}"
        handler = self._make_handler(info.connection_id)
        self._pubsub.unsubscribe(channel, handler)
        info.subscriptions.discard(conversation_id)

        event = build_conversation_unsubscribed(
            conversation_id=conversation_id,
            sequence=info.next_sequence(),
            request_id=request_id,
        )
        await info.websocket.send_text(serialize_event(event))
        return True

    async def handle_ping(
        self, info: ConnectionInfo, request_id: str
    ) -> None:
        """Handle a ping command."""
        event = build_pong(
            sequence=info.next_sequence(),
            request_id=request_id,
        )
        await info.websocket.send_text(serialize_event(event))

    async def broadcast_to_conversation(
        self,
        conversation_id: UUID,
        event: dict[str, Any],
    ) -> None:
        """Broadcast an event to all connections subscribed to a conversation.

        This is called by pubsub handlers when a message is created.
        """
        channel = f"conversation:{conversation_id}"
        self._pubsub.publish(channel, event)

    async def send_event_to_connection(
        self,
        connection_id: str,
        event: dict[str, Any],
    ) -> None:
        """Send an event to a specific connection.

        Uses dedup cache to skip duplicate event_ids.
        """
        info = self._connections.get(connection_id)
        if info is None:
            return

        event_id = event.get("event_id")
        if event_id and info.dedup_cache.seen(event_id):
            return  # Skip duplicate

        if event_id:
            info.dedup_cache.add(event_id)

        # Assign per-connection sequence
        event["sequence"] = info.next_sequence()

        try:
            await info.websocket.send_text(serialize_event(event))
        except Exception:
            # Connection may be broken — clean up
            await self.disconnect(connection_id)

    def _make_handler(self, connection_id: str):
        """Create a pubsub handler for a connection."""
        async def _handler(channel: str, message: dict[str, Any]) -> None:
            await self.send_event_to_connection(connection_id, message)
        return _handler

    async def _send_error(
        self,
        info: ConnectionInfo,
        code: str,
        message: str,
        request_id: str | None = None,
    ) -> None:
        """Send an error event to a connection."""
        event = build_error_event(
            error_code=code,
            message=message,
            sequence=info.next_sequence(),
            request_id=request_id,
        )
        await info.websocket.send_text(serialize_event(event))

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)


# Singleton instance
connection_manager = ConnectionManager()
