"""
Unit tests for Redis client infrastructure (P2-05).

These tests verify:
- Redis client factory does not connect at creation time.
- Namespace key helper is correct.
- TTL validation works.
- ping success path (monkeypatched).
- ping failure returns ``unavailable``.
- ``/health/ready`` Redis check does not raise.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.cache.redis import (
    create_redis_client,
    namespaced_key,
    ping_redis,
    validate_ttl,
)
from src.config import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STRONG_SECRET = "x" * 48
_STRONG_ENC_KEY = "y" * 48


def _make_settings(**overrides: str) -> Settings:
    """Create Settings without reading a .env file, applying env overrides."""
    env_vars = {
        "APP_ENV": "test",
        "APP_SECRET": "test-secret-key",
        "FIELD_ENCRYPTION_KEY": "test-encryption-key",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
    }
    env_vars.update(overrides)
    old_values: dict[str, str | None] = {}
    for key, val in env_vars.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = val
    try:
        return Settings(_env_file=None)  # type: ignore[call-arg]
    finally:
        for key, old_val in old_values.items():
            if old_val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_val


# ---------------------------------------------------------------------------
# 1. Redis client factory
# ---------------------------------------------------------------------------


class TestRedisClientFactory:
    def test_client_created_without_connecting(self) -> None:
        """Client creation should NOT connect to Redis."""
        s = _make_settings()
        client = create_redis_client(s)
        assert client is not None
        # The client should not have an active connection pool connection.
        # We just verify it was created without raising.
        client.close()

    def test_client_uses_settings_url(self) -> None:
        """Client should use the URL from Settings."""
        s = _make_settings(REDIS_URL="redis://localhost:6380/2")
        client = create_redis_client(s)
        # The connection pool should have the correct host/port/db.
        pool = client.connection_pool
        conn_kwargs = pool.connection_kwargs
        assert conn_kwargs.get("host") == "localhost"
        assert conn_kwargs.get("port") == 6380
        client.close()

    def test_client_decode_responses_true(self) -> None:
        """Client should have decode_responses=True."""
        s = _make_settings()
        client = create_redis_client(s)
        assert client.get_encoder().decode_responses is True
        client.close()


# ---------------------------------------------------------------------------
# 2. Namespace key helper
# ---------------------------------------------------------------------------


class TestNamespacedKey:
    def test_default_namespace_prefix(self) -> None:
        s = _make_settings()
        key = namespaced_key(s, "mykey")
        assert key == "campus_agent:mykey"

    def test_custom_namespace_prefix(self) -> None:
        s = _make_settings(REDIS_NAMESPACE="custom_ns")
        key = namespaced_key(s, "mykey")
        assert key == "custom_ns:mykey"

    def test_empty_key(self) -> None:
        s = _make_settings()
        key = namespaced_key(s, "")
        assert key == "campus_agent:"

    def test_namespace_stripped(self) -> None:
        """Namespace with whitespace should be stripped."""
        s = _make_settings(REDIS_NAMESPACE="  spaced  ")
        key = namespaced_key(s, "mykey")
        assert key == "spaced:mykey"


# ---------------------------------------------------------------------------
# 3. TTL validation
# ---------------------------------------------------------------------------


class TestValidateTtl:
    def test_default_ttl_when_none(self) -> None:
        s = _make_settings()
        ttl = validate_ttl(s, None)
        assert ttl == s.DEFAULT_CACHE_TTL_SECONDS

    def test_default_ttl_when_zero(self) -> None:
        s = _make_settings()
        ttl = validate_ttl(s, 0)
        assert ttl == s.DEFAULT_CACHE_TTL_SECONDS

    def test_default_ttl_when_negative(self) -> None:
        s = _make_settings()
        ttl = validate_ttl(s, -1)
        assert ttl == s.DEFAULT_CACHE_TTL_SECONDS

    def test_explicit_valid_ttl(self) -> None:
        s = _make_settings()
        ttl = validate_ttl(s, 600)
        assert ttl == 600

    def test_invalid_default_ttl_raises(self) -> None:
        # Settings validates DEFAULT_CACHE_TTL_SECONDS > 0, so we create
        # a mock settings object with DEFAULT_CACHE_TTL_SECONDS = 0.
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.DEFAULT_CACHE_TTL_SECONDS = 0
        with pytest.raises(ValueError, match="TTL"):
            validate_ttl(mock_settings, None)


# ---------------------------------------------------------------------------
# 4. Ping health check
# ---------------------------------------------------------------------------


class TestPingRedis:
    def test_ping_success_monkeypatched(self) -> None:
        """ping should return ok when client.ping() returns True."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        result = ping_redis(mock_client)
        assert result["status"] == "ok"

    def test_ping_failure_returns_unavailable(self) -> None:
        """ping should return unavailable when client.ping() raises."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("refused")
        result = ping_redis(mock_client)
        assert result["status"] == "unavailable"
        assert "refused" in result["error"]

    def test_ping_none_client_returns_unavailable(self) -> None:
        """ping should return unavailable when client is None."""
        result = ping_redis(None)
        assert result["status"] == "unavailable"

    def test_ping_false_response_returns_unavailable(self) -> None:
        """ping should return unavailable when client.ping() returns False."""
        mock_client = MagicMock()
        mock_client.ping.return_value = False
        result = ping_redis(mock_client)
        assert result["status"] == "unavailable"


# ---------------------------------------------------------------------------
# 5. Health readiness integration
# ---------------------------------------------------------------------------


class TestHealthReadyRedis:
    """Test that /health/ready Redis check does not raise."""

    @pytest.fixture(autouse=True)
    def _setup(self) -> Iterator[None]:
        self.settings = _make_settings()
        yield

    def test_health_ready_redis_unavailable(self) -> None:
        """/health/ready should return redis=unavailable when Redis is down."""
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/health/ready")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["redis"] == "unavailable"

    def test_health_ready_redis_ok_with_mock(self) -> None:
        """/health/ready should return redis=ok when ping succeeds."""
        from src.main import create_app

        app = create_app(self.settings)
        # Enter the lifespan context first so redis_client is set,
        # then patch the ping method to return True.
        with TestClient(app) as client, patch.object(
            app.state.redis_client, "ping", return_value=True
        ):
            resp = client.get("/health/ready")
            assert resp.status_code == 200
            body = resp.json()
            assert body["checks"]["redis"] == "ok"
