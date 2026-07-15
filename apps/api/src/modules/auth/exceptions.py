"""Module-owned exceptions for the auth module."""

from __future__ import annotations


class ModuleError(Exception):
    """Base exception that must be translated at the API boundary."""
