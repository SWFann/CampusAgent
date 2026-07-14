"""Domain event boundary for the admin module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Minimal immutable event envelope owned by this module."""

    name: str
    aggregate_id: str
