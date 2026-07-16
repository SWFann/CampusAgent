"""
SQLAlchemy engine and session factory.

Provides:
- ``create_engine_from_settings``: build a SQLAlchemy ``Engine`` from ``Settings``
- ``create_sessionmaker``: build a ``sessionmaker`` bound to an engine
- ``get_db_session``: FastAPI dependency that yields a ``Session``
- ``check_database_connection``: lightweight health-check function

Design principles:
- Engine creation does NOT connect at construction time (``pool_pre_ping=True``
  validates connections lazily on checkout).
- SQLite URLs automatically use ``StaticPool`` so in-memory databases work
  in tests.
- Transaction boundary: ``get_db_session`` does NOT auto-commit. The service
  layer or repository is responsible for calling ``session.commit()``.
  On exception, the session is rolled back. The session is always closed.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..config import Settings


def _is_sqlite(url: str) -> bool:
    """Return True if the URL targets SQLite."""
    return url.startswith("sqlite")


def create_engine_from_settings(settings: Settings) -> Engine:
    """Create a SQLAlchemy ``Engine`` from application settings.

    For PostgreSQL URLs, connection pool parameters from Settings are applied.
    For SQLite URLs (used in tests), ``StaticPool`` is used so that
    ``:memory:`` databases share a single connection.

    This function does NOT connect to the database at call time.
    ``pool_pre_ping=True`` ensures stale connections are detected on checkout.
    """
    url = settings.DATABASE_URL

    if _is_sqlite(url):
        # SQLite — use StaticPool for in-memory support
        return create_engine(
            url,
            echo=settings.DB_ECHO_SQL,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL — apply pool configuration
    return create_engine(
        url,
        echo=settings.DB_ECHO_SQL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        pool_pre_ping=True,
    )


def create_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    """Create a ``sessionmaker`` bound to the given engine.

    The sessionmaker is configured with ``expire_on_commit=False`` so that
    objects remain usable after commit (important for service-layer patterns
    where the session is committed before returning results).
    """
    return sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=Session,
    )


def get_db_session(
    session_factory: sessionmaker[Session] | None = None,
) -> Iterator[Session]:
    """FastAPI dependency that yields a database session.

    Transaction boundary:
    - The session is NOT auto-committed. Callers must explicitly call
      ``session.commit()`` when they want to persist changes.
    - If an exception propagates through this generator, the session is
      rolled back.
    - The session is always closed in the ``finally`` block.

    Args:
        session_factory: Optional sessionmaker. If ``None``, the function
            returns a generator that must be parameterised by the caller.
            In practice, FastAPI dependencies use ``Depends(get_db_session)``
            with the factory injected via ``app.state``.

    Yields:
        A SQLAlchemy ``Session`` instance.
    """
    if session_factory is None:
        raise RuntimeError(
            "get_db_session requires a sessionmaker. "
            "Use the FastAPI dependency wrapper in dependencies.py."
        )

    session = session_factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection(engine: Engine) -> dict[str, Any]:
    """Perform a lightweight database connectivity check.

    Executes ``SELECT 1`` and returns a structured status dict.
    This function does NOT raise on connection failure — it returns
    ``{"status": "unavailable", "error": str(e)}`` instead, making it
    safe to call from health endpoints.

    Returns:
        A dict with keys:
        - ``status``: ``"ok"`` or ``"unavailable"``
        - ``error``: error message if unavailable (omitted when ok)
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}
