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
        s = _make_settings(
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/campus_agent",
        )
        app = create_app(s)
        with TestClient(app) as client:
            resp = client.get("/health/live")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"

    def test_lifespan_postgresql_health_ready_degraded(self) -> None:
        """``/health/ready`` must return degraded when Postgres is unreachable."""
        s = _make_settings(
            DATABASE_URL="postgresql://postgres:postgres@localhost:5432/campus_agent",
        )
        app = create_app(s)
        with TestClient(app) as client:
            resp = client.get("/health/ready")
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["database"] == "unavailable"

    def test_lifespan_default_postgresql_url(self) -> None:
        """The default Settings DATABASE_URL is postgresql:// and must not crash."""
        # Use the default Settings instance — which has a postgresql:// URL.
        s = _make_settings()
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
