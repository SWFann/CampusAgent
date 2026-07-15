"""
Environment variable validation middleware

Validates required environment variables on application startup.
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

    In production, these variables MUST be set:
    - APP_SECRET (must be strong)
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

        # Validate APP_SECRET strength
        secret = values.get("APP_SECRET", "")
        if len(secret) < 32:
            raise ValueError("APP_SECRET must be at least 32 characters in production")

        # Validate ENCRYPTION_KEY strength
        encryption_key = values.get("FIELD_ENCRYPTION_KEY", "")
        if len(encryption_key) < 32:
            raise ValueError("FIELD_ENCRYPTION_KEY must be at least 32 characters in production")


def check_env() -> None:
    """Validate process environment without terminating the interpreter."""
    validate_production_env()
    validate_required_env_vars(["APP_ENV", "DATABASE_URL", "REDIS_URL"])
