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
from starlette.testclient import TestClient

# Set test environment BEFORE any application imports.
os.environ["APP_ENV"] = "test"
os.environ["APP_DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["APP_SECRET"] = "test-secret-key-at-least-32-chars-long"
os.environ["FIELD_ENCRYPTION_KEY"] = "test-encryption-key"

from src.db.base import Base  # noqa: E402
from src.modules.agents.models import Agent, AgentRun  # noqa: E402, F401
from src.modules.audit.models import AuditLog  # noqa: E402, F401

# Import all ORM models so that Base.metadata.create_all() registers them.
# This must come after importing Base and before any fixture uses it.
from src.modules.auth.models import AuthSession, RefreshToken  # noqa: E402, F401
from src.modules.contacts.models import ContactRelationship  # noqa: E402, F401
from src.modules.conversations.models import (  # noqa: E402, F401
    Conversation,
    ConversationParticipant,
    Message,
)
from src.modules.memories.models import ConsentRecord, MemoryItem  # noqa: E402, F401
from src.modules.model_gateway.models import ModelDefinition  # noqa: E402, F401
from src.modules.nodes.models import ModelDeployment, ModelNode  # noqa: E402, F401
from src.modules.organizations.models import (  # noqa: E402, F401
    Organization,
    OrganizationMembership,
)
from src.modules.scenes.models import (  # noqa: E402, F401
    PrivateSubmission,
    SceneCandidate,
    SceneDefinition,
    SceneInstance,
    SceneParticipant,
    SceneResult,
    SceneVote,
)
from src.modules.users.models import StudentProfile, User  # noqa: E402, F401


@pytest.fixture(autouse=True)
def clear_default_event_bus():
    """Keep singleton event-bus subscriptions isolated between tests."""
    from src.events.bus import default_event_bus

    default_event_bus.clear()
    yield
    default_event_bus.clear()

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


# ---------------------------------------------------------------------------
# Database-backed HTTP client fixtures (P3)
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_client(test_engine) -> Iterator[TestClient]:
    """Synchronous TestClient backed by an in-memory SQLite database.

    The database tables are created on the same engine used by the app's
    sessionmaker, so API endpoints can read and write real data.

    The lifespan is NOT started (we set app.state manually), so the
    health/ready endpoints will report "not_configured" — that's fine
    for auth API tests.
    """
    from fastapi.testclient import TestClient

    from src.db.session import create_sessionmaker
    from src.main import create_app

    session_factory = create_sessionmaker(test_engine)
    application = create_app()
    # Set the sessionmaker so get_db_session dependency works
    application.state.db_engine = test_engine
    application.state.db_sessionmaker = session_factory
    # Set a dummy redis client so health checks don't crash
    application.state.redis_client = None  # type: ignore[assignment]

    client = TestClient(application)
    yield client
