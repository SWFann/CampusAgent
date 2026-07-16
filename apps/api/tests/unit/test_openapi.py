"""Tests for OpenAPI schema generation (P2-13)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.config import Settings


def _make_settings() -> Settings:
    env_vars = {
        "APP_ENV": "test",
        "APP_SECRET": "test-secret-key",
        "FIELD_ENCRYPTION_KEY": "test-encryption-key",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
    }
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


class TestOpenApiGeneration:
    @pytest.fixture(autouse=True)
    def _setup(self) -> Iterator[None]:
        self.settings = _make_settings()
        yield

    def test_openapi_schema_generated(self) -> None:
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/openapi.json")
            assert resp.status_code == 200
            schema = resp.json()
            assert schema["info"]["title"] == self.settings.APP_NAME
            assert "/health/live" in schema["paths"]
            assert "/health/ready" in schema["paths"]

    def test_docs_endpoint(self) -> None:
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/docs")
            assert resp.status_code == 200

    def test_redoc_endpoint(self) -> None:
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/redoc")
            assert resp.status_code == 200

    def test_openapi_has_health_tag(self) -> None:
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/openapi.json")
            schema = resp.json()
            tags = [t["name"] for t in schema.get("tags", [])]
            assert "health" in tags
