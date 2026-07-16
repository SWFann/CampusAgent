"""
Dependency injection container
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings, settings


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def get_db_session(request: Request) -> Iterator[Session]:
    """FastAPI dependency that yields a database session.

    The sessionmaker is retrieved from ``request.app.state.db_sessionmaker``,
    which is initialised in the application lifespan.

    Transaction boundary:
    - The session is NOT auto-committed. Callers must explicitly call
      ``session.commit()`` when they want to persist changes.
    - On exception, the session is rolled back.
    - The session is always closed.
    """
    session_factory: sessionmaker[Session] | None = getattr(
        request.app.state, "db_sessionmaker", None
    )
    if session_factory is None:
        raise RuntimeError(
            "Database sessionmaker not initialised. "
            "The application lifespan must set app.state.db_sessionmaker."
        )

    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Convenience re-export for type-checking
__all__ = ["get_settings", "get_db_session", "Depends"]
