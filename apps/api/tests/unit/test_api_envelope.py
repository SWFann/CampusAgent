"""
Unit tests for the unified API envelope (P2-06).

These tests verify:
- Success envelope construction.
- Error envelope construction.
- AppError handler outputs stable envelope.
- request_id is populated from request context.
- Unknown exceptions do NOT leak internal details.
- Validation errors map to stable error codes.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.schemas.envelope import (
    ErrorDetail,
    ErrorEnvelope,
    SuccessEnvelope,
    error,
    error_code_for_status,
    internal_error,
    success,
)
from src.utils.errors import AppError, NotFoundError

# ---------------------------------------------------------------------------
# 1. Envelope construction
# ---------------------------------------------------------------------------


class TestSuccessEnvelope:
    def test_success_with_data(self) -> None:
        result = success(data={"key": "value"}, request_id="req-123")
        assert result["success"] is True
        assert result["data"] == {"key": "value"}
        assert result["request_id"] == "req-123"

    def test_success_no_data(self) -> None:
        result = success()
        assert result["success"] is True
        assert result["data"] is None
        assert result["request_id"] is None

    def test_success_envelope_model(self) -> None:
        env = SuccessEnvelope(data={"x": 1}, request_id="abc")
        assert env.success is True
        assert env.data == {"x": 1}
        assert env.request_id == "abc"


class TestErrorEnvelope:
    def test_error_basic(self) -> None:
        result = error(
            code="NOT_FOUND",
            message="Resource not found",
            request_id="req-456",
        )
        assert result["success"] is False
        assert result["error"]["code"] == "NOT_FOUND"
        assert result["error"]["message"] == "Resource not found"
        assert result["error"]["details"] == {}
        assert result["request_id"] == "req-456"

    def test_error_with_details(self) -> None:
        result = error(
            code="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "email", "reason": "required"},
            request_id="req-789",
        )
        assert result["error"]["details"]["field"] == "email"
        assert result["error"]["details"]["reason"] == "required"

    def test_error_envelope_model(self) -> None:
        detail = ErrorDetail(code="CONFLICT", message="Already exists")
        env = ErrorEnvelope(error=detail, request_id="xyz")
        assert env.success is False
        assert env.error.code == "CONFLICT"
        assert env.request_id == "xyz"


class TestInternalError:
    def test_internal_error_does_not_leak(self) -> None:
        result = internal_error(request_id="req-leak")
        assert result["success"] is False
        assert result["error"]["code"] == "INTERNAL_ERROR"
        assert "internal" in result["error"]["message"].lower()
        assert result["request_id"] == "req-leak"
        # No stack trace or exception type leaked
        assert "traceback" not in str(result).lower()
        assert "exception" not in str(result).lower()


# ---------------------------------------------------------------------------
# 2. Error code mapping
# ---------------------------------------------------------------------------


class TestErrorCodeMapping:
    def test_400_maps_to_validation(self) -> None:
        assert error_code_for_status(400) == "VALIDATION_ERROR"

    def test_401_maps_to_auth(self) -> None:
        assert error_code_for_status(401) == "AUTH_FAILED"

    def test_403_maps_to_authorization(self) -> None:
        assert error_code_for_status(403) == "PERMISSION_DENIED"

    def test_404_maps_to_not_found(self) -> None:
        assert error_code_for_status(404) == "NOT_FOUND"

    def test_422_maps_to_unprocessable(self) -> None:
        assert error_code_for_status(422) == "UNPROCESSABLE_ENTITY"

    def test_500_maps_to_internal(self) -> None:
        assert error_code_for_status(500) == "INTERNAL_ERROR"

    def test_unknown_status_maps_to_internal(self) -> None:
        assert error_code_for_status(999) == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# 3. Integration: AppError handler
# ---------------------------------------------------------------------------


class TestAppErrorHandler:
    def _make_settings(self):
        import os

        from src.config import Settings

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

    def test_app_error_returns_stable_envelope(self) -> None:
        from src.main import create_app

        s = self._make_settings()
        app = create_app(s)
        with TestClient(app) as client:
            # Trigger an AppError by hitting a non-existent route
            # that we can simulate. We'll use a test route.
            @app.get("/test-app-error")
            async def trigger_error():
                raise AppError(
                    code="CUSTOM_ERROR",
                    message="Something went wrong",
                    status_code=400,
                    details={"extra": "info"},
                )

            resp = client.get("/test-app-error")
            assert resp.status_code == 400
            body = resp.json()
            assert body["success"] is False
            assert body["error"]["code"] == "CUSTOM_ERROR"
            assert body["error"]["message"] == "Something went wrong"
            assert body["error"]["details"]["extra"] == "info"
            assert "request_id" in body
            assert body["request_id"] is not None

    def test_not_found_error_handler(self) -> None:
        from src.main import create_app

        s = self._make_settings()
        app = create_app(s)
        with TestClient(app) as client:
            @app.get("/test-not-found")
            async def trigger_not_found():
                raise NotFoundError("Widget")

            resp = client.get("/test-not-found")
            assert resp.status_code == 404
            body = resp.json()
            assert body["success"] is False
            assert body["error"]["code"] == "NOT_FOUND"
            assert "Widget" in body["error"]["message"]

    def test_unknown_exception_does_not_leak(self) -> None:
        from src.main import create_app

        s = self._make_settings()
        app = create_app(s)
        with TestClient(app, raise_server_exceptions=False) as client:
            @app.get("/test-internal-error")
            async def trigger_internal():
                raise RuntimeError("super secret internal stack trace detail")

            resp = client.get("/test-internal-error")
            assert resp.status_code == 500
            body = resp.json()
            assert body["success"] is False
            assert body["error"]["code"] == "INTERNAL_ERROR"
            # Must not contain the internal message
            assert "super secret" not in str(body)
            assert "stack trace" not in str(body)
            assert "RuntimeError" not in str(body)

    def test_404_route_maps_to_not_found(self) -> None:
        from src.main import create_app

        s = self._make_settings()
        app = create_app(s)
        with TestClient(app) as client:
            resp = client.get("/nonexistent-route")
            assert resp.status_code == 404
            body = resp.json()
            assert body["success"] is False
            assert body["error"]["code"] == "NOT_FOUND"

    def test_request_id_propagated(self) -> None:
        from src.main import create_app

        s = self._make_settings()
        app = create_app(s)
        with TestClient(app) as client:
            @app.get("/test-request-id")
            async def trigger_error_with_id():
                raise AppError(code="TEST", message="test", status_code=400)

            test_id = "550e8400-e29b-41d4-a716-446655440000"
            resp = client.get(
                "/test-request-id",
                headers={"X-Correlation-ID": test_id},
            )
            body = resp.json()
            assert body["request_id"] == test_id
            assert resp.headers["X-Correlation-ID"] == test_id

    def test_health_endpoints_not_enveloped(self) -> None:
        """Health endpoints should NOT use the error envelope format."""
        from src.main import create_app

        s = self._make_settings()
        app = create_app(s)
        with TestClient(app) as client:
            live = client.get("/health/live")
            assert live.status_code == 200
            body = live.json()
            assert body["status"] == "ok"
            assert "success" not in body
            assert "error" not in body

            ready = client.get("/health/ready")
            assert ready.status_code == 200
            body = ready.json()
            assert body["status"] == "degraded"
            assert "checks" in body
            assert "success" not in body
