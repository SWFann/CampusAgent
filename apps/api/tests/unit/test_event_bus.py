"""Tests for domain event bus (P2-10)."""

from __future__ import annotations

from src.events.bus import DomainEvent, EventBus


class UserCreated(DomainEvent):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


class UserDeleted(DomainEvent):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


class CaptureHandler:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


class FailingHandler:
    def handle(self, event: DomainEvent) -> None:
        raise RuntimeError("handler failed")


class TestEventBus:
    def test_subscribe_and_publish(self) -> None:
        bus = EventBus()
        handler = CaptureHandler()
        bus.subscribe(UserCreated, handler)

        event = UserCreated("user-1")
        bus.publish(event)

        assert len(handler.events) == 1
        assert handler.events[0] is event

    def test_multiple_handlers(self) -> None:
        bus = EventBus()
        h1 = CaptureHandler()
        h2 = CaptureHandler()
        bus.subscribe(UserCreated, h1)
        bus.subscribe(UserCreated, h2)

        bus.publish(UserCreated("user-1"))

        assert len(h1.events) == 1
        assert len(h2.events) == 1

    def test_different_event_types_isolated(self) -> None:
        bus = EventBus()
        created_handler = CaptureHandler()
        deleted_handler = CaptureHandler()
        bus.subscribe(UserCreated, created_handler)
        bus.subscribe(UserDeleted, deleted_handler)

        bus.publish(UserCreated("user-1"))
        bus.publish(UserDeleted("user-2"))

        assert len(created_handler.events) == 1
        assert len(deleted_handler.events) == 1

    def test_no_handlers_does_not_raise(self) -> None:
        bus = EventBus()
        bus.publish(UserCreated("user-1"))  # No handlers, no raise

    def test_failing_handler_does_not_block_others(self) -> None:
        bus = EventBus()
        failing = FailingHandler()
        capture = CaptureHandler()
        bus.subscribe(UserCreated, failing)
        bus.subscribe(UserCreated, capture)

        bus.publish(UserCreated("user-1"))

        assert len(capture.events) == 1

    def test_clear(self) -> None:
        bus = EventBus()
        bus.subscribe(UserCreated, CaptureHandler())
        assert bus.handler_count() == 1
        bus.clear()
        assert bus.handler_count() == 0

    def test_handler_count_by_type(self) -> None:
        bus = EventBus()
        bus.subscribe(UserCreated, CaptureHandler())
        bus.subscribe(UserCreated, CaptureHandler())
        bus.subscribe(UserDeleted, CaptureHandler())
        assert bus.handler_count(UserCreated) == 2
        assert bus.handler_count(UserDeleted) == 1
        assert bus.handler_count() == 3
