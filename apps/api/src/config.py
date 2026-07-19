"""
Configuration management for CampusAgent API.

This module is the single source of truth for application configuration.
It provides:
- AppEnv enum for validated environment selection
- SecretStr for sensitive fields (APP_SECRET, FIELD_ENCRYPTION_KEY, MODEL_GATEWAY_API_KEY)
- Production fail-closed validation via model_validator
- safe_model_dump() for logging/debugging without leaking secrets
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known development default values that must never be used in production
_DEV_APP_SECRET = "dev-secret-key-change-in-production"
_DEV_ENCRYPTION_KEY = "dev-encryption-key-change-in-production"


class AppEnv(StrEnum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings — single source of truth for configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
    APP_NAME: str = "CampusAgent API"
    APP_VERSION: str = "0.1.0"
    # Read from APP_DEBUG (not the generic DEBUG env var) to avoid
    # host/IDE/shell pollution (e.g. DEBUG=release).
    DEBUG: bool = Field(default=False, validation_alias="APP_DEBUG")

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/campus_agent"
    # Connection pool settings (applied to PostgreSQL; SQLite uses StaticPool)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: int = 30
    DB_POOL_RECYCLE_SECONDS: int = 1800
    DB_ECHO_SQL: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_NAMESPACE: str = "campus_agent"
    REDIS_SOCKET_TIMEOUT_SECONDS: float = 5.0
    REDIS_CONNECT_TIMEOUT_SECONDS: float = 5.0
    DEFAULT_CACHE_TTL_SECONDS: int = 300

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Security — SecretStr prevents accidental leakage in repr/logs
    APP_SECRET: SecretStr = SecretStr(_DEV_APP_SECRET)
    FIELD_ENCRYPTION_KEY: SecretStr = SecretStr(_DEV_ENCRYPTION_KEY)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Model Gateway
    MODEL_GATEWAY_BASE_URL: str = "http://localhost:8001"
    MODEL_GATEWAY_MODEL: str = "step-3.7-flash"
    MODEL_GATEWAY_TIMEOUT_MS: int = 60000
    MODEL_GATEWAY_IS_EXTERNAL: bool = True
    MODEL_GATEWAY_API_KEY: SecretStr = SecretStr("")

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_PROMPT_CONTENT: bool = False

    # Feature Flags
    ENABLE_EXTERNAL_MODEL: bool = False
    PRIVATE_SCENE_TTL_HOURS: int = 24

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_security(self) -> Settings:
        """Fail-closed validation for application security.

        Applies to ALL environments:
        - If ENABLE_EXTERNAL_MODEL is True, MODEL_GATEWAY_API_KEY must be non-empty

        Production-only (fail-closed):
        - APP_SECRET must not be the development default and must be >= 32 chars
        - FIELD_ENCRYPTION_KEY must not be the development default and must be >= 32 chars
        - LOG_PROMPT_CONTENT must be False
        """
        # --- External model API key (all environments) ---
        if self.ENABLE_EXTERNAL_MODEL:
            api_key_val = self.MODEL_GATEWAY_API_KEY.get_secret_value()
            if not api_key_val or api_key_val.strip() == "":
                raise ValueError(
                    "MODEL_GATEWAY_API_KEY must be non-empty when "
                    "ENABLE_EXTERNAL_MODEL is True"
                )
            if not self.MODEL_GATEWAY_BASE_URL.strip():
                raise ValueError(
                    "MODEL_GATEWAY_BASE_URL must be non-empty when "
                    "ENABLE_EXTERNAL_MODEL is True"
                )
            if not self.MODEL_GATEWAY_MODEL.strip():
                raise ValueError(
                    "MODEL_GATEWAY_MODEL must be non-empty when "
                    "ENABLE_EXTERNAL_MODEL is True"
                )
            if self.MODEL_GATEWAY_TIMEOUT_MS <= 0:
                raise ValueError("MODEL_GATEWAY_TIMEOUT_MS must be positive")

        # --- Production-only checks ---
        if self.APP_ENV != AppEnv.PRODUCTION:
            return self

        # --- APP_SECRET ---
        app_secret_val = self.APP_SECRET.get_secret_value()
        if app_secret_val == _DEV_APP_SECRET:
            raise ValueError(
                "APP_SECRET must not be the development default in production"
            )
        if len(app_secret_val) < 32:
            raise ValueError(
                "APP_SECRET must be at least 32 characters in production"
            )

        # --- FIELD_ENCRYPTION_KEY ---
        enc_key_val = self.FIELD_ENCRYPTION_KEY.get_secret_value()
        if enc_key_val == _DEV_ENCRYPTION_KEY:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY must not be the development default in production"
            )
        if len(enc_key_val) < 32:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY must be at least 32 characters in production"
            )

        # --- LOG_PROMPT_CONTENT ---
        if self.LOG_PROMPT_CONTENT:
            raise ValueError(
                "LOG_PROMPT_CONTENT must be False in production"
            )

        # --- DB_ECHO_SQL ---
        if self.DB_ECHO_SQL:
            raise ValueError(
                "DB_ECHO_SQL must be False in production"
            )

        return self

    @model_validator(mode="after")
    def _validate_db_pool(self) -> Settings:
        """Validate connection pool parameters for all environments."""
        if self.DB_POOL_SIZE < 1:
            raise ValueError("DB_POOL_SIZE must be at least 1")
        if self.DB_MAX_OVERFLOW < 0:
            raise ValueError("DB_MAX_OVERFLOW must be non-negative")
        if self.DB_POOL_TIMEOUT_SECONDS <= 0:
            raise ValueError("DB_POOL_TIMEOUT_SECONDS must be positive")
        if self.DB_POOL_RECYCLE_SECONDS <= 0:
            raise ValueError("DB_POOL_RECYCLE_SECONDS must be positive")
        return self

    @model_validator(mode="after")
    def _validate_redis(self) -> Settings:
        """Validate Redis configuration parameters for all environments."""
        if self.REDIS_SOCKET_TIMEOUT_SECONDS <= 0:
            raise ValueError("REDIS_SOCKET_TIMEOUT_SECONDS must be positive")
        if self.REDIS_CONNECT_TIMEOUT_SECONDS <= 0:
            raise ValueError("REDIS_CONNECT_TIMEOUT_SECONDS must be positive")
        if self.DEFAULT_CACHE_TTL_SECONDS <= 0:
            raise ValueError("DEFAULT_CACHE_TTL_SECONDS must be positive")
        if not self.REDIS_NAMESPACE.strip():
            raise ValueError("REDIS_NAMESPACE must not be empty")
        return self

    # ------------------------------------------------------------------
    # Safe dump for logging / debugging
    # ------------------------------------------------------------------

    def safe_model_dump(self) -> dict[str, Any]:
        """Return a dict with secret values masked as ``**********``.

        Use this for logging, error reporting, or debugging.
        Never use ``model_dump()`` directly for these purposes.
        """
        data = self.model_dump()
        secret_fields = (
            "APP_SECRET",
            "FIELD_ENCRYPTION_KEY",
            "MODEL_GATEWAY_API_KEY",
            "MODEL_GATEWAY_MODEL",
            "MODEL_GATEWAY_TIMEOUT_MS",
            "MODEL_GATEWAY_IS_EXTERNAL",
        )
        for field in secret_fields:
            if field in data:
                data[field] = "**********"
        return data


# Global settings instance
settings = Settings()
