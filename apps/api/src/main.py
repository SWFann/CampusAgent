"""
FastAPI application factory
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings
from .utils.errors import AppError
from ..middleware.env_validation import check_env

# Validate environment variables on startup
check_env()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan manager"""
    # Startup
    application.state.correlation_id = None
    yield
    # Shutdown
    pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
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
        return {"status": "ok", "service": settings.APP_NAME}

    @application.get("/health/ready")
    async def health_ready():
        """Readiness probe - check if dependencies are ready"""
        # TODO: Add database, redis checks
        return {"status": "ready", "service": settings.APP_NAME}

    # API routes will be registered here
    # from .routers import auth, users, ...
    # application.include_router(auth.router, prefix=settings.API_V1_PREFIX)

    return application


# Create app instance
app = create_app()
