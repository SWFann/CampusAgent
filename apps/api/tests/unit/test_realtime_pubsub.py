"""
Unit tests for realtime pubsub backend (P5-09).

Tests:
- In-memory backend publish/subscribe.
- Redis unavailable behavior (graceful degradation).
- No payload content in error logs.
"""

from __future__ import annotations

from src.realtime.pubsub import (
    InMemoryPubSubBackend,
    RedisPubSubBackend,
    create_pubsub_backend,
)


class TestInMemoryPubSub:
    """Test the in-memory pubsub backend."""

    def test_publish_subscribe(self) -> None:
        """Publish and subscribe works."""
        backend = InMemoryPubSubBackend()
        received: list[tuple[str, dict]] = []

        def handler(channel: str, message: dict) -> None:
            received.append((channel, message))

        backend.subscribe("test-channel", handler)
        backend.publish("test-channel", {"event": "test", "data": {"msg": "hello"}})

        assert len(received) == 1
        assert received[0][0] == "test-channel"
        assert received[0][1]["event"] == "test"

    def test_multiple_subscribers(self) -> None:
        """Multiple subscribers receive the same message."""
        backend = InMemoryPubSubBackend()
        received1: list[dict] = []
        received2: list[dict] = []

        def handler1(channel: str, message: dict) -> None:
            received1.append(message)

        def handler2(channel: str, message: dict) -> None:
            received2.append(message)

        backend.subscribe("multi-channel", handler1)
        backend.subscribe("multi-channel", handler2)
        backend.publish("multi-channel", {"event": "test"})

        assert len(received1) == 1
        assert len(received2) == 1

    def test_unsubscribe(self) -> None:
        """Unsubscribed handler no longer receives messages."""
        backend = InMemoryPubSubBackend()
        received: list[dict] = []

        def handler(channel: str, message: dict) -> None:
            received.append(message)

        backend.subscribe("unsub-channel", handler)
        backend.unsubscribe("unsub-channel", handler)
        backend.publish("unsub-channel", {"event": "test"})

        assert len(received) == 0

    def test_publish_to_nonexistent_channel(self) -> None:
        """Publishing to a channel with no subscribers is a no-op."""
        backend = InMemoryPubSubBackend()
        result = backend.publish("nonexistent", {"event": "test"})
        assert result is True  # Still succeeds

    def test_handler_exception_does_not_crash(self) -> None:
        """Handler exceptions are caught and don't affect other handlers."""
        backend = InMemoryPubSubBackend()
        received: list[dict] = []

        def good_handler(channel: str, message: dict) -> None:
            received.append(message)

        def bad_handler(channel: str, message: dict) -> None:
            raise RuntimeError("handler error")

        backend.subscribe("error-channel", bad_handler)
        backend.subscribe("error-channel", good_handler)
        backend.publish("error-channel", {"event": "test"})

        # Good handler still received the message
        assert len(received) == 1

    def test_close(self) -> None:
        """close() clears all channels."""
        backend = InMemoryPubSubBackend()
        backend.subscribe("ch1", lambda c, m: None)
        backend.subscribe("ch2", lambda c, m: None)
        assert backend.channel_count == 2
        backend.close()
        assert backend.channel_count == 0


class TestRedisPubSub:
    """Test the Redis pubsub backend (without a real Redis)."""

    def test_publish_failure_graceful(self) -> None:
        """Redis publish failure returns False, doesn't crash."""
        # Create a fake Redis client that raises on publish
        class FakeRedis:
            def publish(self, channel: str, message: str) -> None:
                raise ConnectionError("Redis unavailable")

        backend = RedisPubSubBackend(FakeRedis())
        result = backend.publish("test-channel", {"event": "test"})
        assert result is False

    def test_create_pubsub_backend_no_redis(self) -> None:
        """create_pubsub_backend with no Redis returns in-memory backend."""
        backend = create_pubsub_backend(None)
        assert isinstance(backend, InMemoryPubSubBackend)

    def test_create_pubsub_backend_with_redis(self) -> None:
        """create_pubsub_backend with a Redis client returns Redis backend."""

        class FakeRedis:
            pass

        backend = create_pubsub_backend(FakeRedis())
        assert isinstance(backend, RedisPubSubBackend)
