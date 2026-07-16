"""
Repository and Unit of Work base patterns for CampusAgent API.

This module provides:
- ``BaseRepository``: generic CRUD repository bound to a SQLAlchemy session.
- ``UnitOfWork``: UoW pattern that manages a session and event publishing.

Design principles:
- The repository does NOT own the session — it receives it from the caller.
- The UoW manages session lifecycle: create, commit, rollback, close.
- Events are published AFTER a successful commit.
- No business models are defined here — this is the infrastructure base.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Session

from ..events.bus import DomainEvent, EventBus

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """Generic repository for a SQLAlchemy ORM model.

    The repository is session-scoped: it receives a session from the
    caller (typically the Unit of Work) and delegates all operations
    to that session.
    """

    def __init__(self, session: Session, model: type[T]) -> None:
        self._session = session
        self._model = model

    def get_by_id(self, id_: Any) -> T | None:
        """Get a single record by primary key."""
        return self._session.get(self._model, id_)

    def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List records with pagination."""
        stmt = select(self._model).limit(limit).offset(offset)
        result = self._session.execute(stmt)
        return list(result.scalars().all())

    def add(self, entity: T) -> None:
        """Add a new entity to the session."""
        self._session.add(entity)

    def delete(self, entity: T) -> None:
        """Mark an entity for deletion."""
        self._session.delete(entity)


class UnitOfWork:
    """Unit of Work pattern for managing session and event publishing.

    Usage:
        with UnitOfWork(session_factory, event_bus) as uow:
            user = uow.users.get_by_id(user_id)
            user.name = "new name"
            uow.events.append(UserUpdated(user_id))
            # commit happens on context exit

    The session is committed on successful exit, rolled back on exception.
    Events are published AFTER a successful commit.
    """

    def __init__(
        self,
        session_factory: Any,
        event_bus: EventBus | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus or EventBus()
        self._session: Session | None = None
        self._pending_events: list[DomainEvent] = []

    def __enter__(self) -> UnitOfWork:
        self._session = self._session_factory()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self._session is not None
        try:
            if exc_type is None:
                self._session.commit()
                # Publish events only after successful commit.
                for event in self._pending_events:
                    self._event_bus.publish(event)
            else:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None
            self._pending_events.clear()

    @property
    def session(self) -> Session:
        """Access the current session (raises if outside context)."""
        if self._session is None:
            raise RuntimeError("UnitOfWork session not initialised — use 'with'")
        return self._session

    def add_event(self, event: DomainEvent) -> None:
        """Queue a domain event for publishing after commit."""
        self._pending_events.append(event)

    @property
    def events(self) -> list[DomainEvent]:
        """Return the list of pending events."""
        return self._pending_events
