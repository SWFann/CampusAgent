"""
Environment variable validation middleware.

Provides a lightweight startup-time guard that complements the fail-closed
validation already performed by ``Settings`` (see ``config.py``).

The ``Settings`` model_validator handles:
- APP_SECRET / FIELD_ENCRYPTION_KEY must not be dev defaults in production
- Secret strength (>= 32 chars) in production
- LOG_PROMPT_CONTENT must be False in production
- MODEL_GATEWAY_API_KEY required when ENABLE_EXTERNAL_MODEL is True

This module's ``validate_production_env`` serves as defence-in-depth: it
verifies that critical variables are non-empty at application startup.
"""

from __future__ import annotations

import os
from collections.abc import Mapping


class EnvValidationError(Exception):
    """Raised when required environment variables are missing"""

    def __init__(self, missing_vars: list[str]):
        self.missing_vars = missing_vars
        super().__init__(f"Missing required environment variables: {', '.join(missing_vars)}")


def validate_required_env_vars(required_vars: list[str]) -> None:
    """
    Validate that required environment variables are set.

    Args:
        required_vars: List of required environment variable names

    Raises:
        EnvValidationError: If any required variables are missing
    """
    missing = []

    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip() == "":
            missing.append(var)

    if missing:
        raise EnvValidationError(missing)


def validate_production_env(environment: Mapping[str, str] | None = None) -> None:
    """
    Validate environment variables for production deployment.

    This is a lightweight startup guard. The primary production security
    validation is performed by ``Settings._validate_production_security``.

    In production, these variables MUST be set and non-empty:
    - APP_SECRET
    - DATABASE_URL
    - REDIS_URL
    - FIELD_ENCRYPTION_KEY
    """
    values = environment if environment is not None else os.environ
    env = values.get("APP_ENV", "development")

    if env == "production":
        required = [
            "APP_SECRET",
            "DATABASE_URL",
            "REDIS_URL",
            "FIELD_ENCRYPTION_KEY",
        ]

        missing = []
        for var in required:
            value = values.get(var)
            if not value or value.strip() == "":
                missing.append(var)

        if missing:
            raise EnvValidationError(missing)


def check_env() -> None:
    """Validate process environment without terminating the interpreter."""
    validate_production_env()
    validate_required_env_vars(["APP_ENV", "DATABASE_URL", "REDIS_URL"])
