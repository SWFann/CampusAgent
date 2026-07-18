"""P11-04: Internal demo API routes.

These routes are ONLY registered when ``APP_ENV`` is development or
test. In production they are not mounted, so the endpoints do not
exist (defence in depth on top of the service-level env guard).

Routes (tag ``internal-demo``):
- POST /internal/demo/seed   — admin + CSRF + demo env
- POST /internal/demo/reset  — admin + CSRF + demo env
- GET  /internal/demo/status — admin + demo env

Privacy:
- Status returns only counts — no emails, tokens, or private content.
- Reset/seed return only summary counters.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from ..config import AppEnv, Settings
from ..dependencies import get_db_session, get_settings
from ..modules.auth.csrf import require_csrf
from ..modules.auth.dependencies import get_current_user
from ..modules.users.models import GlobalRole, User
from ..schemas.envelope import success
from .reset import get_demo_status, reset_demo
from .security import DemoResetForbiddenError, assert_demo_env
from .seed import seed_demo


def _require_super_admin(user: User) -> None:
    """Require SYSTEM_ADMIN for demo operations."""
    if user.global_role != GlobalRole.SYSTEM_ADMIN.value:
        raise DemoResetForbiddenError(env="user_not_super_admin")


router = APIRouter(prefix="/api/v1/internal/demo", tags=["internal-demo"])


@router.post("/seed", status_code=status.HTTP_200_OK)
def demo_seed_endpoint(
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Seed demo data. SYSTEM_ADMIN + development/test only."""
    assert_demo_env(settings)
    _require_super_admin(current_user)
    summary = seed_demo(db_session)
    db_session.commit()
    return success(
        data=summary,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


@router.post("/reset", status_code=status.HTTP_200_OK)
def demo_reset_endpoint(
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Reset demo data. SYSTEM_ADMIN + development/test only."""
    assert_demo_env(settings)
    _require_super_admin(current_user)
    summary = reset_demo(db_session, settings)
    db_session.commit()
    return success(
        data=summary,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


@router.get("/status", status_code=status.HTTP_200_OK)
def demo_status_endpoint(
    http_request: Request,
    db_session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get demo dataset status. SYSTEM_ADMIN + development/test only."""
    assert_demo_env(settings)
    _require_super_admin(current_user)
    data = get_demo_status(db_session)
    return success(
        data=data,
        request_id=getattr(http_request.state, "correlation_id", None),
    )


def should_register(settings: Settings) -> bool:
    """Return True if the demo router should be mounted."""
    return settings.APP_ENV in (AppEnv.DEVELOPMENT, AppEnv.TEST)


def get_demo_router(settings: Settings | None = None) -> APIRouter | None:
    """Return the demo router, or None if the env forbids it."""
    from ..config import settings as default_settings

    s = settings or default_settings
    if not should_register(s):
        return None
    return router
