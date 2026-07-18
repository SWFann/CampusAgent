"""
Unit test for application factory
"""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from src.config import Settings
from src.main import create_app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UNREACHABLE_POSTGRES_URL = "postgresql://postgres:postgres@127.0.0.1:1/campus_agent"


def _make_settings(**overrides: str) -> Settings:
    """Create Settings without reading a .env file, applying env overrides."""
    env_vars = {
        "APP_ENV": "test",
        "APP_SECRET": "test-secret-key",
        "FIELD_ENCRYPTION_KEY": "test-encryption-key",
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/campus_agent",
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


def test_app_factory_creates_multiple_isolated_instances():
    """Test that create_app() creates isolated instances"""
    app1 = create_app()
    app2 = create_app()

    # Verify instances are different objects
    assert id(app1) != id(app2)

    # Verify instance states are independent
    app1.state.test_value = "instance1"
    app2.state.test_value = "instance2"

    assert app1.state.test_value == "instance1"
    assert app2.state.test_value == "instance2"


def test_app_has_required_routes():
    """Test that app has required health check routes"""
    app = create_app()

    # Check health routes exist
    routes = [route.path for route in app.routes if hasattr(route, "path")]

    assert "/health/live" in routes
    assert "/health/ready" in routes


def test_app_title_and_version():
    """Test that app has correct title and version"""
    app = create_app()

    assert app.title == "CampusAgent API"
    assert app.version == "0.1.0"


# ---------------------------------------------------------------------------
# Lifespan with PostgreSQL URL (no real Postgres required)
# ---------------------------------------------------------------------------


class TestLifespanWithPostgresqlUrl:
    """Verify that the app starts and serves health checks even when the
    configured PostgreSQL server is unreachable.

    These tests prove that:
    - psycopg2 DBAPI is installed (engine creation does not raise).
    - The lifespan does not eagerly connect to the database.
    - ``/health/live`` returns 200.
    - ``/health/ready`` returns ``degraded`` with ``database: unavailable``
      rather than raising an exception.
    """

    def test_lifespan_postgresql_health_live_ok(self) -> None:
        """``/health/live`` must return 200 inside the lifespan."""
        s = _make_settings(DATABASE_URL=UNREACHABLE_POSTGRES_URL)
        app = create_app(s)
        with TestClient(app) as client:
            resp = client.get("/health/live")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"

    def test_lifespan_postgresql_health_ready_degraded(self) -> None:
        """``/health/ready`` must return degraded when Postgres is unreachable."""
        s = _make_settings(DATABASE_URL=UNREACHABLE_POSTGRES_URL)
        app = create_app(s)
        with TestClient(app) as client:
            resp = client.get("/health/ready")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["database"] == "unavailable"

    def test_lifespan_unreachable_postgresql_url(self) -> None:
        """An unreachable postgresql:// URL must not crash the lifespan."""
        s = _make_settings(DATABASE_URL=UNREACHABLE_POSTGRES_URL)
        assert s.DATABASE_URL.startswith("postgresql://")
        app = create_app(s)
        with TestClient(app) as client:
            live = client.get("/health/live")
            ready = client.get("/health/ready")
            assert live.status_code == 200
            assert ready.status_code == 200
            ready_body = ready.json()
            assert ready_body["status"] == "degraded"
            assert ready_body["checks"]["database"] == "unavailable"


class TestDevelopmentCors:
    """Browser-based local development must allow the Next.js dev server
    to call the API even when the one-click launcher shifts ports.
    """

    def test_development_allows_localhost_origin_with_credentials(self) -> None:
        s = _make_settings(APP_ENV="development", DATABASE_URL="sqlite:///:memory:")
        app = create_app(s)

        with TestClient(app) as client:
            resp = client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,x-csrf-token",
                },
            )

        assert resp.status_code == 200
        assert resp.headers["access-control-allow-origin"] == "http://localhost:3001"
        assert resp.headers["access-control-allow-credentials"] == "true"

    def test_production_does_not_enable_localhost_cors_by_default(self) -> None:
        s = _make_settings(
            APP_ENV="production",
            APP_SECRET="x" * 48,
            FIELD_ENCRYPTION_KEY="y" * 48,
            DATABASE_URL="sqlite:///:memory:",
        )
        app = create_app(s)

        with TestClient(app) as client:
            resp = client.options(
                "/api/v1/auth/login",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                },
            )

        assert "access-control-allow-origin" not in resp.headers
