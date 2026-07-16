"""
Unit tests for auth rate limiting (P3-10).

Tests verify:
- Rate limiter allows requests up to the limit.
- Rate limiter blocks after the limit is reached.
- Rate limiter resets after the window expires.
- Rate limiter is per-IP per-endpoint.
"""

from __future__ import annotations

import time

from src.modules.auth.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_up_to_limit(self):
        """Limiter allows up to max_requests."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("register", "127.0.0.1") is True

    def test_blocks_after_limit(self):
        """Limiter blocks after max_requests."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("register", "127.0.0.1") is True
        assert limiter.is_allowed("register", "127.0.0.1") is True
        assert limiter.is_allowed("register", "127.0.0.1") is False

    def test_per_ip_isolation(self):
        """Different IPs have separate limits."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("register", "127.0.0.1") is True
        assert limiter.is_allowed("register", "127.0.0.1") is False
        # Different IP — should be allowed
        assert limiter.is_allowed("register", "192.168.1.1") is True

    def test_per_endpoint_isolation(self):
        """Different endpoints have separate limits."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("register", "127.0.0.1") is True
        # Same IP, different endpoint — should be allowed
        assert limiter.is_allowed("login", "127.0.0.1") is True

    def test_window_expiry(self):
        """Limit resets after the window expires."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        assert limiter.is_allowed("register", "127.0.0.1") is True
        assert limiter.is_allowed("register", "127.0.0.1") is False
        # Wait for window to expire
        time.sleep(1.1)
        assert limiter.is_allowed("register", "127.0.0.1") is True

    def test_reset_clears_all(self):
        """Reset clears all stored timestamps."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("register", "127.0.0.1") is True
        assert limiter.is_allowed("register", "127.0.0.1") is False
        limiter.reset()
        assert limiter.is_allowed("register", "127.0.0.1") is True
