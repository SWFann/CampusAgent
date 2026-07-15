"""
FastAPI application factory
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Settings, settings
from .middleware.env_validation import validate_production_env
from .utils.errors import AppError

# Environment validation will be called in lifespan, not at module level


def create_lifespan(app_settings: Settings):
    """Create a lifespan handler bound to one application configuration."""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.correlation_id = None
        validate_production_env(
            {
                "APP_ENV": app_settings.APP_ENV,
                "APP_SECRET": app_settings.APP_SECRET,
                "DATABASE_URL": app_settings.DATABASE_URL,
                "REDIS_URL": app_settings.REDIS_URL,
                "FIELD_ENCRYPTION_KEY": app_settings.FIELD_ENCRYPTION_KEY,
            }
        )
        yield

    return lifespan


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application"""

    current_settings = app_settings or settings

    application = FastAPI(
        title=current_settings.APP_NAME,
        version=current_settings.APP_VERSION,
        debug=current_settings.DEBUG,
        lifespan=create_lifespan(current_settings),
    )

    # Middleware
    @application.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        """Add correlation ID to each request"""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    # Exception handlers
    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "request_id": getattr(request.state, "correlation_id", None),
            },
        )

    # Health check routes
    @application.get("/health/live")
    async def health_live():
        """Liveness probe - check if process is alive"""
        return {"status": "ok", "service": current_settings.APP_NAME}

    @application.get("/health/ready")
    async def health_ready():
        """Readiness probe - check if dependencies are ready"""
        return {
            "status": "ready",
            "service": current_settings.APP_NAME,
            "checks": {"database": "not_configured", "redis": "not_configured"},
        }

    # API routes will be registered here
    # from .routers import auth, users, ...
    # application.include_router(auth.router, prefix=settings.API_V1_PREFIX)

    return application


# Create app instance
app = create_app()
