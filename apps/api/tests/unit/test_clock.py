"""Tests for injectable Clock and UUID factory (P2-09)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.utils.clock import (
    DefaultClock,
    DefaultUuidFactory,
    FrozenClock,
    FrozenUuidFactory,
)


class TestDefaultClock:
    def test_now_returns_datetime(self) -> None:
        clock = DefaultClock()
        result = clock.now()
        assert isinstance(result, datetime)

    def test_now_is_timezone_aware(self) -> None:
        clock = DefaultClock()
        result = clock.now()
        assert result.tzinfo is not None

    def test_now_is_utc(self) -> None:
        clock = DefaultClock()
        result = clock.now()
        assert result.tzinfo == UTC


class TestFrozenClock:
    def test_returns_fixed_time(self) -> None:
        fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        clock = FrozenClock(fixed)
        assert clock.now() == fixed

    def test_advance(self) -> None:
        fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        target = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
        clock = FrozenClock(fixed)
        clock.advance(target)
        assert clock.now() == target


class TestDefaultUuidFactory:
    def test_returns_uuid(self) -> None:
        factory = DefaultUuidFactory()
        result = factory.new_uuid()
        assert isinstance(result, UUID)

    def test_unique(self) -> None:
        factory = DefaultUuidFactory()
        a = factory.new_uuid()
        b = factory.new_uuid()
        assert a != b


class TestFrozenUuidFactory:
    def test_returns_predefined(self) -> None:
        u1 = UUID("550e8400-e29b-41d4-a716-446655440000")
        u2 = UUID("660e8400-e29b-41d4-a716-446655440001")
        factory = FrozenUuidFactory([u1, u2])
        assert factory.new_uuid() == u1
        assert factory.new_uuid() == u2

    def test_falls_back_to_random(self) -> None:
        factory = FrozenUuidFactory([])
        result = factory.new_uuid()
        assert isinstance(result, UUID)
