"""
PubSub backend for realtime message delivery.

Provides two backends:
- ``RedisPubSubBackend``: uses Redis Pub/Sub for cross-process delivery.
- ``InMemoryPubSubBackend``: uses in-memory channels for tests and dev.

Both backends implement the same interface:
- ``publish(channel, message)``: publish a message to a channel.
- ``subscribe(channel, handler)``: subscribe to a channel.
- ``unsubscribe(channel, handler)``: unsubscribe from a channel.

Design principles:
- Does NOT log message content or payload — only channel names and sizes.
- Redis unavailability is handled gracefully — returns False on publish failure.
- The in-memory backend is fully synchronous for test determinism.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from typing import Any, Protocol

logger = logging.getLogger("campus_agent.realtime.pubsub")


class PubSubHandler(Protocol):
    """Protocol for pubsub message handlers."""

    def __call(self, channel: str, message: dict[str, Any]) -> None:
        """Handle a pubsub message."""
        ...


class PubSubBackend(Protocol):
    """Protocol for pubsub backends."""

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        """Publish a message to a channel.

        Returns True on success, False on failure.
        """
        ...

    def subscribe(self, channel: str, handler: Callable[[str, dict[str, Any]], None]) -> None:
        """Subscribe to a channel."""
        ...

    def unsubscribe(self, channel: str, handler: Callable[[str, dict[str, Any]], None]) -> None:
        """Unsubscribe from a channel."""
        ...

    def close(self) -> None:
        """Clean up resources."""
        ...


class InMemoryPubSubBackend:
    """In-memory pubsub backend for tests and development.

    All operations are synchronous. No external dependencies.
    """

    def __init__(self) -> None:
        self._channels: dict[str, list[Callable[[str, dict[str, Any]], None]]] = {}

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        """Publish a message to a channel synchronously."""
        handlers = self._channels.get(channel, [])
        for handler in handlers:
            try:
                handler(channel, message)
            except Exception as exc:
                logger.error(
                    "pubsub.handler.error",
                    extra={
                        "channel": channel,
                        "handler": type(handler).__name__,
                        "error": str(exc),
                        "payload_size": len(str(message)),
                    },
                )
        return True

    def subscribe(
        self, channel: str, handler: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Subscribe to a channel."""
        if channel not in self._channels:
            self._channels[channel] = []
        self._channels[channel].append(handler)

    def unsubscribe(
        self, channel: str, handler: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Unsubscribe from a channel."""
        if channel in self._channels:
            with contextlib.suppress(ValueError):
                self._channels[channel].remove(handler)

    def close(self) -> None:
        """Clean up all subscriptions."""
        self._channels.clear()

    @property
    def channel_count(self) -> int:
        """Number of active channels."""
        return len(self._channels)


class RedisPubSubBackend:
    """Redis-backed pubsub for cross-process message delivery.

    Uses Redis Pub/Sub. If Redis is unavailable, publish returns False
    and the backend continues to function (degraded mode).
    """

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client
        self._pubsub: Any = None
        self._handlers: dict[str, list[Callable[[str, dict[str, Any]], None]]] = {}

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        """Publish a message to a Redis channel.

        Returns True on success, False on failure (Redis unavailable).
        """
        import json

        try:
            self._redis.publish(channel, json.dumps(message, default=str))
            return True
        except Exception as exc:
            logger.error(
                "pubsub.redis.publish_failed",
                extra={
                    "channel": channel,
                    "error": str(exc),
                    "payload_size": len(str(message)),
                },
            )
            return False

    def subscribe(
        self, channel: str, handler: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Subscribe to a Redis channel.

        NOTE: In P5 MVP, Redis subscriptions use a background thread.
        For tests, use InMemoryPubSubBackend instead.
        """
        import json
        import threading

        if channel not in self._handlers:
            self._handlers[channel] = []

        self._handlers[channel].append(handler)

        if self._pubsub is None:
            self._pubsub = self._redis.pubsub()

        def _listener(ch: str) -> None:
            for message in self._pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        for h in self._handlers.get(ch, []):
                            try:
                                h(ch, data)
                            except Exception as exc:
                                logger.error(
                                    "pubsub.redis.handler.error",
                                    extra={
                                        "channel": ch,
                                        "error": str(exc),
                                        "payload_size": len(str(data)),
                                    },
                                )
                    except Exception:
                        pass

        self._pubsub.subscribe(channel)
        thread = threading.Thread(target=_listener, args=(channel,), daemon=True)
        thread.start()

    def unsubscribe(
        self, channel: str, handler: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Unsubscribe from a Redis channel."""
        if channel in self._handlers:
            with contextlib.suppress(ValueError):
                self._handlers[channel].remove(handler)

    def close(self) -> None:
        """Clean up Redis pubsub."""
        if self._pubsub is not None:
            with contextlib.suppress(Exception):
                self._pubsub.close()
        self._handlers.clear()


def create_pubsub_backend(redis_client: Any | None = None) -> PubSubBackend:
    """Create a pubsub backend.

    If a Redis client is provided, use RedisPubSubBackend.
    Otherwise, use InMemoryPubSubBackend.
    """
    if redis_client is not None:
        return RedisPubSubBackend(redis_client)
    return InMemoryPubSubBackend()


# Default singleton — replaced at app startup
default_pubsub: PubSubBackend = InMemoryPubSubBackend()
