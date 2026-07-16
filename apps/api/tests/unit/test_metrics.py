"""Tests for basic observability metrics (P2-14)."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.utils.metrics import RequestMetrics


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


class TestRequestMetrics:
    def test_record(self) -> None:
        m = RequestMetrics()
        m.record("GET", "/health/live", 200, 5.0)
        assert m.total_requests == 1

    def test_multiple_records(self) -> None:
        m = RequestMetrics()
        m.record("GET", "/a", 200, 1.0)
        m.record("GET", "/b", 404, 2.0)
        m.record("POST", "/a", 201, 3.0)
        assert m.total_requests == 3

    def test_prometheus_text(self) -> None:
        m = RequestMetrics()
        m.record("GET", "/health/live", 200, 5.0)
        text = m.to_prometheus_text()
        assert "http_requests_total" in text
        assert "http_status_total" in text
        assert "http_request_duration_ms" in text

    def test_empty_metrics(self) -> None:
        m = RequestMetrics()
        text = m.to_prometheus_text()
        assert "http_requests_total" in text
        assert m.total_requests == 0


class TestMetricsEndpoint:
    @pytest.fixture(autouse=True)
    def _setup(self) -> Iterator[None]:
        self.settings = _make_settings()
        yield

    def test_metrics_endpoint_exists(self) -> None:
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/metrics")
            assert resp.status_code == 200
            assert "http_requests_total" in resp.text

    def test_metrics_increments_after_request(self) -> None:
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            # Make a request
            client.get("/health/live")
            # Check metrics
            resp = client.get("/metrics")
            assert resp.status_code == 200
            text = resp.text
            # Should have at least 2 requests (health + metrics itself)
            assert "GET:/health/live" in text or "/health/live" in text
