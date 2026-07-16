"""
Sensitive field redaction utilities for CampusAgent API.

This module provides:
- A denylist of sensitive field names (case-insensitive).
- ``redact()``: recursively redact sensitive values in dict/list/nested structures.
- ``redact_headers()``: redact sensitive HTTP headers.
- The redaction does NOT modify the original object — a new object is returned.
- Sensitive values are replaced with the string ``[REDACTED]``.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Sensitive field denylist
# ---------------------------------------------------------------------------

# All comparisons are case-insensitive.
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        # Authentication / credentials
        "password",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set-cookie",
        "secret",
        "app_secret",
        "field_encryption_key",
        "api_key",
        "model_gateway_api_key",
        # Private / prompt content
        "prompt",
        "private_preference",
        "memory_content",
        "chain_of_thought",
    }
)

# The replacement value for redacted fields.
_REDACTED = "[REDACTED]"


def _is_sensitive(key: str) -> bool:
    """Check if a key name is in the sensitive denylist (case-insensitive)."""
    return key.lower() in SENSITIVE_FIELDS


def redact(obj: Any) -> Any:
    """Recursively redact sensitive values in a nested structure.

    This function walks dicts, lists, and tuples, replacing values whose
    key (in dict context) matches a sensitive field name with ``[REDACTED]``.

    The original object is NOT modified — a deep copy is returned.

    Args:
        obj: Any Python object (dict, list, tuple, scalar, etc.)

    Returns:
        A new object with sensitive values replaced by ``[REDACTED]``.
    """
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if _is_sensitive(str(key)):
                result[key] = _REDACTED
            else:
                result[key] = redact(value)
        return result
    if isinstance(obj, list):
        return [redact(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(redact(item) for item in obj)
    # For non-container types, return as-is (no redaction needed).
    return obj


def redact_headers(headers: dict[str, str] | Any) -> dict[str, str]:
    """Redact sensitive HTTP headers.

    Args:
        headers: A dict of header name → value (or any object with .items()).

    Returns:
        A new dict with sensitive header values replaced by ``[REDACTED]``.
    """
    result: dict[str, str] = {}
    for key, value in dict(headers).items():
        if _is_sensitive(str(key)):
            result[str(key)] = _REDACTED
        else:
            result[str(key)] = str(value)
    return result


def is_sensitive(key: str) -> bool:
    """Public API to check if a field name is sensitive."""
    return _is_sensitive(key)
