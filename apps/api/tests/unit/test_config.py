"""
Unit tests for application configuration (Settings).

Covers:
- Default Settings loading
- AppEnv enum validation
- SecretStr non-leakage (repr, str, safe_model_dump)
- Explicit secret value access
- Production fail-closed rules
- .env.example alignment
- App factory integration with SecretStr
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from src.config import AppEnv, Settings  # noqa: I001

# pydantic-settings accepts ``_env_file`` at runtime but the type stubs
# do not expose it, so we centralise the call with a type-ignore.

_SETTINGS_ENV_VARS = [
    "APP_ENV", "APP_NAME", "APP_VERSION", "APP_DEBUG",
    "DATABASE_URL", "REDIS_URL", "API_V1_PREFIX",
    "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT_SECONDS",
    "DB_POOL_RECYCLE_SECONDS", "DB_ECHO_SQL",
    "REDIS_NAMESPACE", "REDIS_SOCKET_TIMEOUT_SECONDS",
    "REDIS_CONNECT_TIMEOUT_SECONDS", "DEFAULT_CACHE_TTL_SECONDS",
    "APP_SECRET", "FIELD_ENCRYPTION_KEY",
    "ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS",
    "MODEL_GATEWAY_BASE_URL", "MODEL_GATEWAY_MODEL",
    "MODEL_GATEWAY_TIMEOUT_MS", "MODEL_GATEWAY_IS_EXTERNAL",
    "MODEL_GATEWAY_API_KEY",
    "LOG_LEVEL", "LOG_PROMPT_CONTENT",
    "ENABLE_EXTERNAL_MODEL", "PRIVATE_SCENE_TTL_HOURS",
]


def _settings_no_env() -> Settings:
    """Create Settings with dev defaults (no env vars, no .env file)."""
    old: dict[str, str | None] = {}
    for var in _SETTINGS_ENV_VARS:
        old[var] = os.environ.pop(var, None)
    try:
        return Settings(_env_file=None)  # type: ignore[call-arg]
    finally:
        for var, val in old.items():
            if val is not None:
                os.environ[var] = val

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Strong secrets for production tests (>= 32 chars, not dev defaults)
_STRONG_SECRET = "x" * 48
_STRONG_ENC_KEY = "y" * 48


def _make_settings(**overrides: str) -> Settings:
    """Create Settings without reading a .env file, applying env overrides."""
    env_vars = {
        "APP_ENV": "test",
        "APP_SECRET": "test-secret-key",
        "FIELD_ENCRYPTION_KEY": "test-encryption-key",
        "DATABASE_URL": "sqlite:///./test.db",
        "REDIS_URL": "redis://localhost:6379/1",
    }
    env_vars.update(overrides)
    # Temporarily set env vars for BaseSettings to pick up
    old_values: dict[str, str | None] = {}
    for key, val in env_vars.items():
        old_values[key] = os.environ.get(key)
        os.environ[key] = val
    try:
        return Settings(_env_file=None)  # type: ignore[call-arg]
    finally:
        for key, old_val in old_values.items():
            if old_val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_val


# ---------------------------------------------------------------------------
# 1. Default Settings can load
# ---------------------------------------------------------------------------


class TestDefaultSettings:
    def test_settings_loads_with_defaults(self) -> None:
        """Settings can be instantiated with test env."""
        s = _make_settings()
        assert s.APP_NAME == "CampusAgent API"
        assert s.APP_VERSION == "0.1.0"

    def test_app_env_defaults_to_development(self) -> None:
        """When no APP_ENV is set, it defaults to development."""
        old = os.environ.pop("APP_ENV", None)
        try:
            s = _settings_no_env()
            assert s.APP_ENV == AppEnv.DEVELOPMENT
        finally:
            if old is not None:
                os.environ["APP_ENV"] = old

    def test_debug_is_bool(self) -> None:
        s = _make_settings()
        assert isinstance(s.DEBUG, bool)

    def test_url_fields_exist(self) -> None:
        s = _make_settings()
        assert s.DATABASE_URL
        assert s.REDIS_URL


# ---------------------------------------------------------------------------
# 2. AppEnv enum validation
# ---------------------------------------------------------------------------


class TestAppEnvValidation:
    @pytest.mark.parametrize("env", ["development", "test", "production"])
    def test_valid_app_env_values(self, env: str) -> None:
        if env == "production":
            s = _make_settings(
                APP_ENV=env,
                APP_SECRET=_STRONG_SECRET,
                FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
            )
        else:
            s = _make_settings(APP_ENV=env)
        assert s.APP_ENV.value == env

    def test_invalid_app_env_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_settings(APP_ENV="staging")


# ---------------------------------------------------------------------------
# 3. Secret fields don't leak
# ---------------------------------------------------------------------------


class TestSecretNonLeakage:
    def test_repr_does_not_contain_dev_secret(self) -> None:
        s = _settings_no_env()  # Uses dev defaults
        rep = repr(s)
        assert "dev-secret-key-change-in-production" not in rep

    def test_repr_does_not_contain_dev_encryption_key(self) -> None:
        s = _settings_no_env()
        rep = repr(s)
        assert "dev-encryption-key-change-in-production" not in rep

    def test_str_of_secret_field_does_not_leak(self) -> None:
        s = _settings_no_env()
        # str(SecretStr(...)) returns masked form
        assert "dev-secret-key-change-in-production" not in str(s.APP_SECRET)

    def test_safe_model_dump_does_not_leak(self) -> None:
        s = _settings_no_env()
        safe = s.safe_model_dump()
        safe_str = str(safe)
        assert "dev-secret-key-change-in-production" not in safe_str
        assert "dev-encryption-key-change-in-production" not in safe_str
        assert safe["APP_SECRET"] == "**********"
        assert safe["FIELD_ENCRYPTION_KEY"] == "**********"
        assert safe["MODEL_GATEWAY_API_KEY"] == "**********"


# ---------------------------------------------------------------------------
# 4. Explicit secret value access
# ---------------------------------------------------------------------------


class TestSecretValueAccess:
    def test_get_secret_value_returns_app_secret(self) -> None:
        s = _settings_no_env()
        assert s.APP_SECRET.get_secret_value() == "dev-secret-key-change-in-production"

    def test_get_secret_value_returns_encryption_key(self) -> None:
        s = _settings_no_env()
        assert (
            s.FIELD_ENCRYPTION_KEY.get_secret_value()
            == "dev-encryption-key-change-in-production"
        )

    def test_secret_fields_are_secret_str_type(self) -> None:
        s = _settings_no_env()
        assert isinstance(s.APP_SECRET, SecretStr)
        assert isinstance(s.FIELD_ENCRYPTION_KEY, SecretStr)
        assert isinstance(s.MODEL_GATEWAY_API_KEY, SecretStr)


# ---------------------------------------------------------------------------
# 5. Production rejects default dev secrets
# ---------------------------------------------------------------------------


class TestProductionSecretDefaults:
    def test_production_with_default_app_secret_fails(self) -> None:
        with pytest.raises(ValidationError, match="APP_SECRET"):
            _make_settings(
                APP_ENV="production",
                APP_SECRET="dev-secret-key-change-in-production",
                FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
            )

    def test_production_with_default_encryption_key_fails(self) -> None:
        with pytest.raises(ValidationError, match="FIELD_ENCRYPTION_KEY"):
            _make_settings(
                APP_ENV="production",
                APP_SECRET=_STRONG_SECRET,
                FIELD_ENCRYPTION_KEY="dev-encryption-key-change-in-production",
            )

    def test_production_with_short_app_secret_fails(self) -> None:
        with pytest.raises(ValidationError, match="APP_SECRET"):
            _make_settings(
                APP_ENV="production",
                APP_SECRET="short",
                FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
            )

    def test_production_with_short_encryption_key_fails(self) -> None:
        with pytest.raises(ValidationError, match="FIELD_ENCRYPTION_KEY"):
            _make_settings(
                APP_ENV="production",
                APP_SECRET=_STRONG_SECRET,
                FIELD_ENCRYPTION_KEY="short",
            )

    def test_production_with_strong_secrets_succeeds(self) -> None:
        s = _make_settings(
            APP_ENV="production",
            APP_SECRET=_STRONG_SECRET,
            FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
        )
        assert s.APP_ENV == AppEnv.PRODUCTION


# ---------------------------------------------------------------------------
# 6. Production rejects LOG_PROMPT_CONTENT=true
# ---------------------------------------------------------------------------


class TestProductionLogPromptContent:
    def test_production_with_log_prompt_content_true_fails(self) -> None:
        with pytest.raises(ValidationError, match="LOG_PROMPT_CONTENT"):
            _make_settings(
                APP_ENV="production",
                APP_SECRET=_STRONG_SECRET,
                FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
                LOG_PROMPT_CONTENT="true",
            )

    def test_production_with_log_prompt_content_false_succeeds(self) -> None:
        s = _make_settings(
            APP_ENV="production",
            APP_SECRET=_STRONG_SECRET,
            FIELD_ENCRYPTION_KEY=_STRONG_ENC_KEY,
            LOG_PROMPT_CONTENT="false",
        )
        assert s.LOG_PROMPT_CONTENT is False


# ---------------------------------------------------------------------------
# 7. ENABLE_EXTERNAL_MODEL requires API key
# ---------------------------------------------------------------------------


class TestExternalModelApiKey:
    def test_external_model_true_with_empty_key_fails(self) -> None:
        with pytest.raises(ValidationError, match="MODEL_GATEWAY_API_KEY"):
            _make_settings(
                APP_ENV="test",
                ENABLE_EXTERNAL_MODEL="true",
                MODEL_GATEWAY_API_KEY="",
            )

    def test_external_model_true_with_nonempty_key_succeeds(self) -> None:
        s = _make_settings(
            APP_ENV="test",
            ENABLE_EXTERNAL_MODEL="true",
            MODEL_GATEWAY_API_KEY="some-api-key",
            MODEL_GATEWAY_BASE_URL="https://api.stepfun.com/v1",
            MODEL_GATEWAY_MODEL="step-3.7-flash",
        )
        assert s.ENABLE_EXTERNAL_MODEL is True
        assert s.MODEL_GATEWAY_API_KEY.get_secret_value() == "some-api-key"
        assert s.MODEL_GATEWAY_MODEL == "step-3.7-flash"

    def test_external_model_true_with_empty_model_fails(self) -> None:
        with pytest.raises(ValidationError, match="MODEL_GATEWAY_MODEL"):
            _make_settings(
                APP_ENV="test",
                ENABLE_EXTERNAL_MODEL="true",
                MODEL_GATEWAY_API_KEY="some-api-key",
                MODEL_GATEWAY_MODEL="",
            )

    def test_external_model_false_with_empty_key_succeeds(self) -> None:
        s = _make_settings(
            APP_ENV="test",
            ENABLE_EXTERNAL_MODEL="false",
            MODEL_GATEWAY_API_KEY="",
        )
        assert s.ENABLE_EXTERNAL_MODEL is False


# ---------------------------------------------------------------------------
# 8. .env.example alignment
# ---------------------------------------------------------------------------


class TestEnvExampleAlignment:
    @pytest.fixture
    def env_example_content(self) -> str:
        path = Path(__file__).resolve().parents[4] / ".env.example"
        return path.read_text()

    @pytest.mark.parametrize(
        "field",
        [
            "APP_ENV",
            "APP_NAME",
            "APP_VERSION",
            "APP_DEBUG",
            "DATABASE_URL",
            "DB_POOL_SIZE",
            "DB_MAX_OVERFLOW",
            "DB_POOL_TIMEOUT_SECONDS",
            "DB_POOL_RECYCLE_SECONDS",
            "DB_ECHO_SQL",
            "REDIS_URL",
            "APP_SECRET",
            "FIELD_ENCRYPTION_KEY",
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "REFRESH_TOKEN_EXPIRE_DAYS",
            "API_V1_PREFIX",
            "NEXT_PUBLIC_API_URL",
            "MODEL_GATEWAY_BASE_URL",
            "MODEL_GATEWAY_MODEL",
            "MODEL_GATEWAY_TIMEOUT_MS",
            "MODEL_GATEWAY_IS_EXTERNAL",
            "MODEL_GATEWAY_API_KEY",
            "LOG_LEVEL",
            "LOG_PROMPT_CONTENT",
            "ENABLE_EXTERNAL_MODEL",
            "PRIVATE_SCENE_TTL_HOURS",
        ],
    )
    def test_env_example_contains_field(
        self, env_example_content: str, field: str
    ) -> None:
        assert field in env_example_content, (
            f".env.example is missing field: {field}"
        )


# ---------------------------------------------------------------------------
# 9. App factory integration
# ---------------------------------------------------------------------------


class TestAppFactoryIntegration:
    def test_create_app_with_secret_str_settings(self) -> None:
        """create_app should work with SecretStr-typed Settings."""
        from src.main import create_app

        s = _make_settings()
        app = create_app(s)
        assert app.title == "CampusAgent API"
        assert app.version == "0.1.0"

    def test_create_app_default_settings_works(self) -> None:
        """create_app() with no args should work (uses global settings)."""
        from src.main import create_app

        app = create_app()
        assert app.title == "CampusAgent API"


# ---------------------------------------------------------------------------
# 10. DEBUG env var pollution — APP_DEBUG isolation
# ---------------------------------------------------------------------------


class TestDebugEnvPollution:
    """Settings.DEBUG must read from APP_DEBUG, not the generic DEBUG env var.

    Host shells often set DEBUG=release or similar non-bool values.
    Settings must be immune to such ambient pollution.
    """

    def test_ambient_debug_release_does_not_break_settings(self) -> None:
        """DEBUG=release in env should not cause ValidationError."""
        old_debug = os.environ.get("DEBUG")
        os.environ["DEBUG"] = "release"
        try:
            s = _settings_no_env()
            assert s.DEBUG is False
        finally:
            if old_debug is None:
                os.environ.pop("DEBUG", None)
            else:
                os.environ["DEBUG"] = old_debug

    def test_app_debug_true_sets_debug_true(self) -> None:
        """APP_DEBUG=true should set Settings.DEBUG = True."""
        s = _make_settings(APP_DEBUG="true")
        assert s.DEBUG is True

    def test_app_debug_invalid_value_raises(self) -> None:
        """APP_DEBUG=not-bool should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_settings(APP_DEBUG="not-bool")

    def test_api_import_survives_debug_release(self) -> None:
        """Importing src.main should succeed even with DEBUG=release in env.

        This is a regression test for the Codex audit finding where
        ambient DEBUG=release caused API import to fail.
        """
        import importlib

        old_debug = os.environ.get("DEBUG")
        os.environ["DEBUG"] = "release"
        try:
            # Force re-import to simulate fresh process
            if "src.main" in sys.modules:
                importlib.reload(sys.modules["src.config"])
                importlib.reload(sys.modules["src.main"])
            import src.main  # noqa: F401
            assert src.main.app is not None
        finally:
            if old_debug is None:
                os.environ.pop("DEBUG", None)
            else:
                os.environ["DEBUG"] = old_debug


# ---------------------------------------------------------------------------
# 11. .env.example key uniqueness
# ---------------------------------------------------------------------------


class TestEnvExampleKeyUniqueness:
    """Ensure critical keys appear exactly once as actual assignments."""

    @pytest.fixture
    def env_example_assignments(self) -> dict[str, int]:
        from collections import Counter

        path = Path(__file__).resolve().parents[4] / ".env.example"
        keys: list[str] = []
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            keys.append(stripped.split("=", 1)[0])
        return Counter(keys)

    def test_app_env_appears_once(self, env_example_assignments: dict[str, int]) -> None:
        assert env_example_assignments.get("APP_ENV", 0) == 1

    def test_app_debug_appears_once(self, env_example_assignments: dict[str, int]) -> None:
        assert env_example_assignments.get("APP_DEBUG", 0) == 1

    def test_debug_does_not_appear(self, env_example_assignments: dict[str, int]) -> None:
        assert env_example_assignments.get("DEBUG", 0) == 0
