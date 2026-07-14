"""
Core configuration (moved from src/config.py)

This module contains core configuration that is shared across all modules.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Core application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
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
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


# Global settings instance
core_settings = CoreSettings()
