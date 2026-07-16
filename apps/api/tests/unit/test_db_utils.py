"""
Unit tests for database utility functions (UTC time, UUID).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.db.time import utc_now
from src.db.types import new_uuid, uuid_to_str  # noqa: I001

# ---------------------------------------------------------------------------
# UTC time
# ---------------------------------------------------------------------------


class TestUtcNow:
    def test_returns_datetime(self) -> None:
        result = utc_now()
        assert isinstance(result, datetime)

    def test_is_timezone_aware(self) -> None:
        result = utc_now()
        assert result.tzinfo is not None

    def test_tz_is_utc(self) -> None:
        result = utc_now()
        assert result.tzinfo == UTC

    def test_utc_offset_is_zero(self) -> None:
        result = utc_now()
        offset = result.utcoffset()
        assert offset is not None
        assert offset.total_seconds() == 0


# ---------------------------------------------------------------------------
# UUID
# ---------------------------------------------------------------------------


class TestNewUuid:
    def test_returns_uuid_instance(self) -> None:
        result = new_uuid()
        assert isinstance(result, UUID)

    def test_is_version_4(self) -> None:
        result = new_uuid()
        assert result.version == 4

    def test_generates_unique_values(self) -> None:
        a = new_uuid()
        b = new_uuid()
        assert a != b


class TestUuidToStr:
    def test_returns_string(self) -> None:
        u = new_uuid()
        assert isinstance(uuid_to_str(u), str)

    def test_string_matches_str_uuid(self) -> None:
        u = new_uuid()
        assert uuid_to_str(u) == str(u)

    def test_string_is_lowercase(self) -> None:
        u = new_uuid()
        assert uuid_to_str(u) == uuid_to_str(u).lower()
