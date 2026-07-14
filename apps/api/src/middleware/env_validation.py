"""
Environment variable validation middleware

Validates required environment variables on application startup.
"""

from __future__ import annotations

import os
import sys


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


def validate_production_env() -> None:
    """
    Validate environment variables for production deployment.

    In production, these variables MUST be set:
    - SECRET_KEY (must be strong)
    - DATABASE_URL
    - REDIS_URL
    - FIELD_ENCRYPTION_KEY
    """
    env = os.getenv("APP_ENV", "development")

    if env == "production":
        required = [
            "APP_SECRET",
            "DATABASE_URL",
            "REDIS_URL",
            "FIELD_ENCRYPTION_KEY",
        ]

        missing = []
        for var in required:
            value = os.getenv(var)
            if not value or value.strip() == "":
                missing.append(var)

        if missing:
            raise EnvValidationError(missing)

        # Validate SECRET_KEY strength
        secret = os.getenv("APP_SECRET", "")
        if len(secret) < 32:
            raise ValueError("APP_SECRET must be at least 32 characters in production")

        # Validate ENCRYPTION_KEY strength
        encryption_key = os.getenv("FIELD_ENCRYPTION_KEY", "")
        if len(encryption_key) < 32:
            raise ValueError("FIELD_ENCRYPTION_KEY must be at least 32 characters in production")


def check_env() -> None:
    """
    Main entry point for environment validation.

    Call this at application startup.
    """
    try:
        # Validate test/prod environment
        validate_production_env()

        # Basic required vars (all environments)
        required = [
            "APP_ENV",
            "DATABASE_URL",
            "REDIS_URL",
        ]

        validate_required_env_vars(required)

        print("✓ Environment variables validated successfully")
    except EnvValidationError as e:
        print(f"✗ Environment validation failed: {e}", file=sys.stderr)
        print("\nPlease set the following environment variables:", file=sys.stderr)
        for var in e.missing_vars:
            print(f"  - {var}", file=sys.stderr)
        print("\nSee .env.example for reference.", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Environment validation failed: {e}", file=sys.stderr)
        sys.exit(1)
