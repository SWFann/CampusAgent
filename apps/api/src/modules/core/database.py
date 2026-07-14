"""
Database connection management
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import core_settings

# TODO: Implement async engine and session factory
# engine = create_async_engine(core_settings.DATABASE_URL, ...)
# async_session_factory = async_sessionmaker(engine, ...)


async def get_db_session() -> AsyncSession:
    """Get database session (dependency injection)"""
    # TODO: Implement session management
    raise NotImplementedError
