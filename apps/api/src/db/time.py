"""
UTC time utilities.

All database timestamp fields in CampusAgent MUST use timezone-aware UTC
datetimes produced by ``utc_now()``. This ensures consistency across
PostgreSQL, application logic, and API responses.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns:
        A ``datetime`` with ``tzinfo=UTC``.

    Use this everywhere a database timestamp is needed instead of
    ``datetime.utcnow()`` (which returns a naive datetime).
    """
    return datetime.now(UTC)
