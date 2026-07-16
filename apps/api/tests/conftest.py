"""
Pytest configuration and fixtures.

P2-12: Test database fixtures.

Provides:
- ``test_engine``: SQLite in-memory engine for each test.
- ``test_session_factory``: sessionmaker bound to the test engine.
- ``test_db_session``: a Session yielded per test (auto-rollback).
- ``test_client``: FastAPI TestClient with test settings.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment BEFORE any application imports.
os.environ["APP_ENV"] = "test"
os.environ["APP_DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["APP_SECRET"] = "test-secret-key"
os.environ["FIELD_ENCRYPTION_KEY"] = "test-encryption-key"

from src.db.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Database fixtures (P2-12)
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_engine():
    """Create a fresh SQLite in-memory engine for each test.

    All tables are created before the test and dropped after.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def test_session_factory(test_engine):
    """Create a sessionmaker bound to the test engine."""
    return sessionmaker(bind=test_engine, expire_on_commit=False, class_=Session)


@pytest.fixture()
def test_db_session(test_session_factory) -> Iterator[Session]:
    """Yield a database session for a single test.

    The session is rolled back and closed after the test to ensure
    isolation between tests.
    """
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """AsyncClient fixture for testing."""
    from src.main import create_app

    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
