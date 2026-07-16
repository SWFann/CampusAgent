"""
In-process domain event bus for CampusAgent API.

This module provides:
- ``DomainEvent``: base class for domain events.
- ``EventHandler``: protocol for event handlers.
- ``EventBus``: in-process publish/subscribe event bus.

Design principles:
- Events are published synchronously in-process (no external broker).
- Handlers are called immediately when an event is published.
- Handler failures are logged but do NOT prevent other handlers from running.
- The bus does NOT participate in database transactions.
  Callers should publish events AFTER a successful commit.
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger("campus_agent.events")


class DomainEvent:
    """Base class for all domain events.

    Subclasses should define specific event data as attributes.
    """

    pass


@runtime_checkable
class EventHandler(Protocol):
    """Protocol for event handlers."""

    def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""
        ...


class EventBus:
    """In-process event bus for domain events.

    Handlers are registered per event type. When an event is published,
    all handlers registered for that event type are called synchronously.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    def subscribe(
        self, event_type: type[DomainEvent], handler: EventHandler
    ) -> None:
        """Register a handler for an event type.

        Multiple handlers can be registered for the same event type.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers.

        Handler failures are logged but do NOT prevent other handlers
        from running.
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as exc:
                logger.error(
                    "event.handler.error",
                    extra={
                        "event_type": event_type.__name__,
                        "handler": type(handler).__name__,
                        "error": str(exc),
                    },
                )

    def clear(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()

    def handler_count(self, event_type: type[DomainEvent] | None = None) -> int:
        """Return the number of registered handlers.

        Args:
            event_type: If provided, count handlers for that type only.
                If None, count all handlers.
        """
        if event_type is not None:
            return len(self._handlers.get(event_type, []))
        return sum(len(handlers) for handlers in self._handlers.values())


default_event_bus = EventBus()
