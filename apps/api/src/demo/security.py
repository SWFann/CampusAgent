"""P11-04: Environment guards for demo operations.

Demo seed/reset are powerful operations that must NEVER run in
production. This module centralises the environment check so that
both the service layer and the HTTP routes share one guard.

Fail-closed: if APP_ENV is not development or test, or is unset,
the guard raises ``DemoResetForbiddenError``.
"""

from __future__ import annotations

from ..config import AppEnv, Settings
from ..utils.errors import AppError


class DemoResetForbiddenError(AppError):
    """Raised when a demo operation is attempted in a forbidden environment."""

    def __init__(self, *, env: str | None = None) -> None:
        env_label = env or "<unset>"
        super().__init__(
            code="DEMO_RESET_FORBIDDEN",
            message="Demo reset is only allowed in development/test environments.",
            status_code=403,
            details={"app_env": env_label},
        )


def assert_demo_env(settings: Settings) -> None:
    """Raise if the current environment is not development or test.

    This is the single guard used by reset, seed CLI, and the internal
    HTTP routes. Production (and any unknown value) must fail-closed.
    """
    env = settings.APP_ENV
    if env not in (AppEnv.DEVELOPMENT, AppEnv.TEST):
        raise DemoResetForbiddenError(env=str(env))
