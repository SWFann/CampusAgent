"""
FastAPI application factory
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .cache.redis import create_redis_client, ping_redis
from .config import Settings, settings
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


def create_lifespan(app_settings: Settings):
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

    # Initialise metrics
    metrics = RequestMetrics()
    application.state.metrics = metrics

    # Middleware
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(MetricsMiddleware, metrics=metrics)

    # Exception handlers
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
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
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Map Pydantic validation errors to a stable error code."""
        return JSONResponse(
            status_code=422,
            content=envelope_error(
                code=error_code_for_status(422),
                message="Request validation failed.",
                details={"errors": exc.errors()},
                request_id=getattr(request.state, "correlation_id", None),
            ),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
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
    async def generic_exception_handler(request: Request, exc: Exception):
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
    async def health_live():
        """Liveness probe - check if process is alive."""
        return {"status": "ok", "service": current_settings.APP_NAME}

    @application.get("/health/ready", tags=["health"])
    async def health_ready():
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
    from .modules.auth.api import router as auth_router
    from .modules.directory.api import router as directory_router
    from .modules.organizations.api import router as organizations_router
    from .modules.users.api import router as users_router

    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(organizations_router)
    application.include_router(directory_router)

    # Register metrics endpoint
    register_metrics_endpoint(application, metrics)

    return application


# Create app instance
app = create_app()
