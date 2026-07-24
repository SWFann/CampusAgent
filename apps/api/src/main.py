"""
FastAPI application factory
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache.redis import create_redis_client, ping_redis
from .config import AppEnv, Settings, settings
from .db.session import (
    check_database_connection,
    create_engine_from_settings,
    create_sessionmaker,
)
from .middleware.env_validation import validate_production_env
from .middleware.request_context import RequestContextMiddleware
from .schemas.envelope import error as envelope_error
from .schemas.envelope import error_code_for_status
from .schemas.envelope import internal_error as internal_error_envelope
from .utils.errors import AppError
from .utils.logging import configure_logging
from .utils.metrics import MetricsMiddleware, RequestMetrics, register_metrics_endpoint

# Environment validation will be called in lifespan, not at module level


def create_lifespan(app_settings: Settings) -> Any:
    """Create a lifespan handler bound to one application configuration."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.correlation_id = None
        validate_production_env(
            {
                "APP_ENV": str(app_settings.APP_ENV),
                "APP_SECRET": app_settings.APP_SECRET.get_secret_value(),
                "DATABASE_URL": app_settings.DATABASE_URL,
                "REDIS_URL": app_settings.REDIS_URL,
                "FIELD_ENCRYPTION_KEY": app_settings.FIELD_ENCRYPTION_KEY.get_secret_value(),
            }
        )

        # Initialise database engine and sessionmaker.
        # Engine creation does NOT connect — pool_pre_ping defers the
        # first connection to checkout time.
        engine = create_engine_from_settings(app_settings)
        application.state.db_engine = engine
        application.state.db_sessionmaker = create_sessionmaker(engine)

        # Initialise Redis client.
        # Client creation does NOT connect — connection is lazy.
        redis_client = create_redis_client(app_settings)
        application.state.redis_client = redis_client

        # Register domain event handlers
        from .modules.agents.handlers import register_personal_agent_handler

        register_personal_agent_handler()

        # Register scene plugins (P9)
        from .modules.scenes.plugins import DormDinnerPlugin, campus_structured_plugins
        from .modules.scenes.registry import get_scene_registry

        scene_registry = get_scene_registry()
        # Plugin may already be registered in hot-reload scenarios.
        with suppress(Exception):
            scene_registry.register(DormDinnerPlugin())
        for plugin in campus_structured_plugins():
            with suppress(Exception):
                scene_registry.register(plugin)

        yield

        # Dispose engine and close Redis on shutdown
        engine.dispose()
        redis_client.close()

    return lifespan


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application"""

    current_settings = app_settings or settings

    application = FastAPI(
        title=current_settings.APP_NAME,
        version=current_settings.APP_VERSION,
        debug=current_settings.DEBUG,
        lifespan=create_lifespan(current_settings),
        description="CampusAgent API — a campus-oriented AI agent platform.",
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints."},
        ],
    )

    # Configure structured logging
    configure_logging(current_settings.LOG_LEVEL)

    if current_settings.APP_ENV != AppEnv.PRODUCTION:
        application.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Initialise metrics
    metrics = RequestMetrics()
    application.state.metrics = metrics

    # Middleware
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(MetricsMiddleware, metrics=metrics)

    # Exception handlers
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Handle known application errors with stable envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope_error(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "correlation_id", None),
            ),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Map Pydantic validation errors to a stable error code.

        Error details may contain non-JSON-serializable values (e.g. bytes
        from form-encoded bodies). We coerce them to safe strings so the
        envelope can always be serialized (P12-04 hardening).
        """

        def _coerce(obj: Any) -> Any:
            if isinstance(obj, bytes):
                try:
                    return obj.decode("utf-8")
                except UnicodeDecodeError:
                    return f"<{len(obj)} bytes>"
            if isinstance(obj, BaseException):
                return str(obj)
            if isinstance(obj, dict):
                return {
                    key: "<redacted>" if key == "input" else _coerce(value)
                    for key, value in obj.items()
                }
            if isinstance(obj, list):
                return [_coerce(v) for v in obj]
            if isinstance(obj, tuple):
                return [_coerce(v) for v in obj]
            return obj

        return JSONResponse(
            status_code=422,
            content=envelope_error(
                code=error_code_for_status(422),
                message="Request validation failed.",
                details={"errors": _coerce(exc.errors())},
                request_id=getattr(request.state, "correlation_id", None),
            ),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Map Starlette HTTP exceptions to stable error envelope."""
        return JSONResponse(
            status_code=exc.status_code,
            content=envelope_error(
                code=error_code_for_status(exc.status_code),
                message=str(exc.detail),
                request_id=getattr(request.state, "correlation_id", None),
            ),
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions.

        Returns a generic INTERNAL_ERROR without leaking internal details.
        """
        return JSONResponse(
            status_code=500,
            content=internal_error_envelope(
                request_id=getattr(request.state, "correlation_id", None),
            ),
        )

    # Health check routes
    @application.get("/health/live", tags=["health"])
    async def health_live() -> dict[str, str]:
        """Liveness probe - check if process is alive."""
        return {"status": "ok", "service": current_settings.APP_NAME}

    @application.get("/health/ready", tags=["health"])
    async def health_ready() -> dict[str, Any]:
        """Readiness probe - check if dependencies are ready."""
        # Database check — use the engine stored in app state.
        # If the engine hasn't been initialised (e.g. before lifespan),
        # return "not_configured" rather than crashing.
        engine = getattr(application.state, "db_engine", None)
        if engine is not None:
            db_status = check_database_connection(engine)
            db_state = db_status["status"]
        else:
            db_state = "not_configured"

        # Redis check — use the client stored in app state.
        redis_client = getattr(application.state, "redis_client", None)
        if redis_client is not None:
            redis_result = ping_redis(redis_client)
            redis_state = redis_result["status"]
        else:
            redis_state = "not_configured"

        all_ok = db_state == "ok" and redis_state == "ok"
        return {
            "status": "ready" if all_ok else "degraded",
            "service": current_settings.APP_NAME,
            "checks": {
                "database": db_state,
                "redis": redis_state,
            },
        }

    # API routes
    from .modules.agents.api import router as agents_router
    from .modules.audit.api import router as audit_router
    from .modules.auth.api import router as auth_router
    from .modules.contacts.api import router as contacts_router
    from .modules.conversations.api import router as conversations_router
    from .modules.directory.api import router as directory_router
    from .modules.memories.api import router as memories_router
    from .modules.model_gateway.api import router as model_gateway_router
    from .modules.nodes.api import router as nodes_admin_router
    from .modules.organizations.api import router as organizations_router
    from .modules.scenes.api import router as scenes_router
    from .modules.users.api import router as users_router

    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(organizations_router)
    application.include_router(directory_router)
    application.include_router(conversations_router)
    application.include_router(contacts_router)
    application.include_router(agents_router)
    application.include_router(memories_router)
    application.include_router(audit_router)
    application.include_router(nodes_admin_router)
    application.include_router(model_gateway_router)
    application.include_router(scenes_router)

    # WebSocket routes
    from .realtime.api import router as realtime_router

    application.include_router(realtime_router)

    # P11: Demo internal routes — only in development/test.
    from .demo.routes import get_demo_router

    demo_router = get_demo_router(current_settings)
    if demo_router is not None:
        application.include_router(demo_router)

    # Register model gateway metrics endpoint
    from .modules.model_gateway.metrics import get_model_gateway_metrics

    model_gateway_metrics = get_model_gateway_metrics()

    @application.get("/metrics/model-gateway", include_in_schema=False)
    async def model_gateway_metrics_endpoint() -> Any:
        """Model gateway metrics (Prometheus-style, no sensitive labels)."""
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(
            content=model_gateway_metrics.to_prometheus_text(),
            media_type="text/plain; version=0.0.4",
        )

    # Register metrics endpoint
    register_metrics_endpoint(application, metrics)

    return application


# Create app instance
app = create_app()
