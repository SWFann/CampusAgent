"""
Redis client factory and health-check utilities.

Design principles:
- Client creation does NOT connect at construction time.
- ``ping_redis`` returns a structured status dict, never raises.
- Namespace prefix and TTL helpers are provided for future cache usage.
- Redis unavailable must NOT cause application import to fail.
"""

from __future__ import annotations

from typing import Any

import redis

from ..config import Settings


def create_redis_client(settings: Settings) -> redis.Redis:
    """Create a Redis client from application settings.

    This function does NOT connect to Redis at call time. The connection
    is established lazily when the first command is executed.

    Args:
        settings: Application settings containing Redis configuration.

    Returns:
        A ``redis.Redis`` instance configured with the settings' URL,
        socket timeout, and connect timeout.
    """
    return redis.Redis.from_url(
        settings.REDIS_URL,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT_SECONDS,
        decode_responses=True,
    )


def ping_redis(client: redis.Redis | None) -> dict[str, Any]:
    """Perform a lightweight Redis connectivity check.

    Executes ``PING`` and returns a structured status dict.
    This function does NOT raise on connection failure — it returns
    ``{"status": "unavailable", "error": str(e)}`` instead.

    Args:
        client: A Redis client instance, or ``None`` if not configured.

    Returns:
        A dict with keys:
        - ``status``: ``"ok"`` or ``"unavailable"``
        - ``error``: error message if unavailable (omitted when ok)
    """
    if client is None:
        return {"status": "unavailable", "error": "client not configured"}

    try:
        result = client.ping()
        if result:
            return {"status": "ok"}
        return {"status": "unavailable", "error": "ping returned false"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}


def namespaced_key(settings: Settings, key: str) -> str:
    """Build a Redis key with the configured namespace prefix.

    Format: ``{namespace}:{key}``

    Args:
        settings: Application settings containing REDIS_NAMESPACE.
        key: The raw key without namespace.

    Returns:
        The namespaced key string.
    """
    ns = settings.REDIS_NAMESPACE.strip()
    if not ns:
        return key
    return f"{ns}:{key}"


def validate_ttl(settings: Settings, ttl: int | None = None) -> int:
    """Validate and return a TTL value.

    Args:
        settings: Application settings containing DEFAULT_CACHE_TTL_SECONDS.
        ttl: Optional explicit TTL. If ``None`` or ``<= 0``, falls back to
            ``settings.DEFAULT_CACHE_TTL_SECONDS``.

    Returns:
        A positive integer TTL in seconds.

    Raises:
        ValueError: If the resolved TTL is not positive.
    """
    resolved = ttl if ttl is not None and ttl > 0 else settings.DEFAULT_CACHE_TTL_SECONDS
    if resolved <= 0:
        raise ValueError("TTL must be positive")
    return resolved
