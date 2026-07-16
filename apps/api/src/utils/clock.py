"""
Injectable time and UUID utilities for deterministic testing.

This module provides:
- ``Clock`` protocol: injectable clock interface for getting the current time.
- ``DefaultClock``: production implementation using ``utc_now()``.
- ``FrozenClock``: test implementation that returns a fixed time.
- ``UuidFactory`` protocol: injectable UUID generation interface.
- ``DefaultUuidFactory``: production implementation using ``uuid4()``.
- ``FrozenUuidFactory``: test implementation that returns fixed UUIDs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from ..db.time import utc_now
from ..db.types import new_uuid


@runtime_checkable
class Clock(Protocol):
    """Protocol for injectable time sources."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""
        ...


class DefaultClock:
    """Production clock — delegates to ``utc_now()``."""

    def now(self) -> datetime:
        return utc_now()


class FrozenClock:
    """Test clock that always returns the same time.

    The time can be advanced via ``advance()`` for sequential assertions.
    """

    def __init__(self, fixed_time: datetime) -> None:
        self._time = fixed_time

    def now(self) -> datetime:
        return self._time

    def advance(self, delta: datetime) -> None:
        """Advance the frozen time by adding a datetime delta.

        Args:
            delta: A timezone-aware datetime to add.
        """
        self._time = self._time + (delta - self._time)


@runtime_checkable
class UuidFactory(Protocol):
    """Protocol for injectable UUID generation."""

    def new_uuid(self) -> UUID:
        """Generate a new UUID."""
        ...


class DefaultUuidFactory:
    """Production UUID factory — delegates to ``uuid4()``."""

    def new_uuid(self) -> UUID:
        return new_uuid()


class FrozenUuidFactory:
    """Test UUID factory that returns pre-determined UUIDs.

    UUIDs are yielded from a queue. If the queue is exhausted, a new
    UUID is generated.
    """

    def __init__(self, uuids: list[UUID] | None = None) -> None:
        self._uuids = list(uuids) if uuids else []
        self._index = 0

    def new_uuid(self) -> UUID:
        if self._index < len(self._uuids):
            uuid_val = self._uuids[self._index]
            self._index += 1
            return uuid_val
        return uuid4()
