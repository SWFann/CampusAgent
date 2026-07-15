"""
Configuration management for CampusAgent API
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "CampusAgent API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/campus_agent"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Security
    APP_SECRET: str = "dev-secret-key-change-in-production"
    FIELD_ENCRYPTION_KEY: str = "dev-encryption-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_PROMPT_CONTENT: bool = False

    # Feature Flags
    ENABLE_EXTERNAL_MODEL: bool = False
    PRIVATE_SCENE_TTL_HOURS: int = 24


# Global settings instance
settings = Settings()
