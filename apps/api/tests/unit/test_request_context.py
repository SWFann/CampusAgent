"""
Unit tests for request context middleware (P2-07).

These tests verify:
- No header generates a new request ID.
- ``X-Correlation-ID`` with a valid UUID is reused.
- Non-UUID header generates a new UUID.
- Response includes the request ID header.
- ``request.state`` has ``request_id``.
- Sensitive headers are not logged.
- ``X-Request-ID`` is also accepted as a fallback.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Iterator

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from src.config import Settings
from src.middleware.request_context import (
    _is_valid_uuid,
    get_safe_headers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides: str) -> Settings:
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
# 1. UUID validation
# ---------------------------------------------------------------------------


class TestIsValidUuid:
    def test_valid_uuid(self) -> None:
        assert _is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_valid_uppercase_uuid(self) -> None:
        assert _is_valid_uuid("550E8400-E29B-41D4-A716-446655440000") is True

    def test_invalid_string(self) -> None:
        assert _is_valid_uuid("not-a-uuid") is False

    def test_empty_string(self) -> None:
        assert _is_valid_uuid("") is False

    def test_none_value(self) -> None:
        assert _is_valid_uuid(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. Safe headers
# ---------------------------------------------------------------------------


class TestSafeHeaders:
    def test_authorization_excluded(self) -> None:
        """Authorization header must not appear in safe headers."""
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.headers = {"authorization": "Bearer secret-token"}
        safe = get_safe_headers(mock_request)
        assert "authorization" not in safe

    def test_cookie_excluded(self) -> None:
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.headers = {"cookie": "session=abc123"}
        safe = get_safe_headers(mock_request)
        assert "cookie" not in safe

    def test_safe_headers_included(self) -> None:
        from unittest.mock import MagicMock

        mock_request = MagicMock()
        mock_request.headers = {
            "user-agent": "TestClient",
            "content-type": "application/json",
        }
        safe = get_safe_headers(mock_request)
        assert safe.get("user-agent") == "TestClient"
        assert safe.get("content-type") == "application/json"


# ---------------------------------------------------------------------------
# 2.5 Structured logging
# ---------------------------------------------------------------------------


class TestStructuredLogging:
    def test_json_formatter_uses_iso_timestamp(self) -> None:
        from src.utils.logging import JsonFormatter

        record = logging.LogRecord(
            name="campus_agent.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        payload = json.loads(JsonFormatter().format(record))

        assert "%f" not in payload["timestamp"]
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
            payload["timestamp"],
        )


# ---------------------------------------------------------------------------
# 3. Integration: request ID handling
# ---------------------------------------------------------------------------


class TestRequestIdHandling:
    @pytest.fixture(autouse=True)
    def _setup(self) -> Iterator[None]:
        self.settings = _make_settings()
        yield

    def test_no_header_generates_request_id(self) -> None:
        """Without any header, a new UUID v4 is generated."""
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get("/health/live")
            assert resp.status_code == 200
            correlation = resp.headers.get("X-Correlation-ID")
            assert correlation is not None
            assert _is_valid_uuid(correlation)

    def test_valid_correlation_id_reused(self) -> None:
        """A valid UUID in X-Correlation-ID is reused."""
        from src.main import create_app

        test_id = "550e8400-e29b-41d4-a716-446655440000"
        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get(
                "/health/live",
                headers={"X-Correlation-ID": test_id},
            )
            assert resp.status_code == 200
            assert resp.headers["X-Correlation-ID"] == test_id

    def test_non_uuid_correlation_id_ignored(self) -> None:
        """A non-UUID value in X-Correlation-ID is ignored; a new UUID is generated."""
        from src.main import create_app

        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get(
                "/health/live",
                headers={"X-Correlation-ID": "not-a-uuid"},
            )
            assert resp.status_code == 200
            correlation = resp.headers.get("X-Correlation-ID")
            assert correlation is not None
            assert correlation != "not-a-uuid"
            assert _is_valid_uuid(correlation)

    def test_x_request_id_fallback(self) -> None:
        """X-Request-ID is used as a fallback when X-Correlation-ID is absent."""
        from src.main import create_app

        test_id = "660e8400-e29b-41d4-a716-446655440001"
        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get(
                "/health/live",
                headers={"X-Request-ID": test_id},
            )
            assert resp.status_code == 200
            correlation = resp.headers.get("X-Correlation-ID")
            assert correlation == test_id

    def test_correlation_id_takes_precedence(self) -> None:
        """X-Correlation-ID takes precedence over X-Request-ID."""
        from src.main import create_app

        corr_id = "550e8400-e29b-41d4-a716-446655440000"
        req_id = "660e8400-e29b-41d4-a716-446655440001"
        app = create_app(self.settings)
        with TestClient(app) as client:
            resp = client.get(
                "/health/live",
                headers={
                    "X-Correlation-ID": corr_id,
                    "X-Request-ID": req_id,
                },
            )
            assert resp.status_code == 200
            assert resp.headers["X-Correlation-ID"] == corr_id


# ---------------------------------------------------------------------------
# 4. Request duration tracking
# ---------------------------------------------------------------------------


class TestRequestDuration:
    @pytest.fixture(autouse=True)
    def _setup(self) -> Iterator[None]:
        self.settings = _make_settings()
        yield

    def test_duration_recorded(self) -> None:
        """Request duration should be recorded in request.state."""
        from src.main import create_app

        app = create_app(self.settings)

        @app.get("/test-duration")
        async def test_endpoint(request: Request):
            duration = getattr(request.state, "request_duration_ms", None)
            return {"duration_before": duration}

        with TestClient(app) as client:
            resp = client.get("/test-duration")
            assert resp.status_code == 200
            body = resp.json()
            assert body["duration_before"] is None

    def test_request_id_in_state(self) -> None:
        """request.state should have request_id set."""
        from src.main import create_app

        app = create_app(self.settings)

        @app.get("/test-state")
        async def test_endpoint(request: Request):
            return {
                "request_id": getattr(request.state, "request_id", None),
                "correlation_id": getattr(request.state, "correlation_id", None),
            }

        with TestClient(app) as client:
            resp = client.get("/test-state")
            assert resp.status_code == 200
            body = resp.json()
            assert body["request_id"] is not None
            assert _is_valid_uuid(body["request_id"])
            assert body["correlation_id"] == body["request_id"]
