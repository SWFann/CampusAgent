"""
In-process rate limiter for auth endpoints (P3-10).

This module provides a simple sliding-window rate limiter that works
without Redis (in-process). For production, Redis-based rate limiting
should be used, but for MVP the in-process limiter is sufficient.

Design principles:
- Limits per-IP per-endpoint.
- Uses a sliding window (default 60 seconds).
- Returns True if allowed, False if rate-limited.
- Thread-safe via a simple lock.
- Does NOT leak account existence (same rate-limit response for all failures).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict


class RateLimiter:
    """In-process sliding-window rate limiter.

    Usage:
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        if not limiter.is_allowed("register", "127.0.0.1"):
            raise RateLimitError()
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, endpoint: str, client_ip: str) -> bool:
        """Check if a request is allowed under the rate limit.

        Args:
            endpoint: The endpoint identifier (e.g. "register", "login").
            client_ip: The client IP address.

        Returns:
            True if the request is allowed, False if rate-limited.
        """
        key = f"{endpoint}:{client_ip}"
        now = time.monotonic()

        with self._lock:
            # Remove expired timestamps
            timestamps = self._timestamps[key]
            cutoff = now - self._window_seconds
            self._timestamps[key] = [t for t in timestamps if t > cutoff]

            if len(self._timestamps[key]) >= self._max_requests:
                return False

            self._timestamps[key].append(now)
            return True

    def reset(self) -> None:
        """Clear all stored timestamps (for testing)."""
        with self._lock:
            self._timestamps.clear()


# Singleton instance for auth endpoints
_auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)


def get_auth_rate_limiter() -> RateLimiter:
    """Get the shared auth rate limiter instance."""
    return _auth_rate_limiter
