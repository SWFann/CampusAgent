"""
Pytest configuration
"""

from __future__ import annotations

import asyncio
import os

import pytest
from httpx import AsyncClient, ASGITransport

# Set test environment
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test-secret-key"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """AsyncClient fixture for testing"""
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
