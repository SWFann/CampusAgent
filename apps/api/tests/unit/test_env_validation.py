"""Tests for startup environment validation."""

from __future__ import annotations

import pytest

from src.middleware.env_validation import EnvValidationError, validate_production_env


def production_env(**overrides: str) -> dict[str, str]:
    values = {
        "APP_ENV": "production",
        "APP_SECRET": "a" * 32,
        "DATABASE_URL": "postgresql://db.example/campus_agent",
        "REDIS_URL": "redis://cache.example/0",
        "FIELD_ENCRYPTION_KEY": "b" * 32,
    }
    values.update(overrides)
    return values


def test_non_production_environment_does_not_require_secrets() -> None:
    validate_production_env({"APP_ENV": "test"})


def test_production_environment_reports_all_missing_values() -> None:
    with pytest.raises(EnvValidationError) as error:
        validate_production_env({"APP_ENV": "production"})

    assert set(error.value.missing_vars) == {
        "APP_SECRET",
        "DATABASE_URL",
        "REDIS_URL",
        "FIELD_ENCRYPTION_KEY",
    }


def test_production_environment_rejects_empty_keys() -> None:
    """Empty (but not necessarily short) values should be caught as missing."""
    with pytest.raises(EnvValidationError) as error:
        validate_production_env(production_env(APP_SECRET="   "))

    assert "APP_SECRET" in error.value.missing_vars


def test_valid_production_environment_passes() -> None:
    validate_production_env(production_env())
