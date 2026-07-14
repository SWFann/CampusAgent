"""
Dependency injection container
"""

from __future__ import annotations

from typing import Generator

from .config import settings


def get_settings() -> Settings:
    """Get application settings"""
    return settings


# Add more dependencies as needed:
# - Database session
# - Redis client
# - Repositories
# - Services
