"""P6-02: Auto-create personal agent on user registration.

Tests:
- UserRegistered event handler subscribed on event bus.
- Handler ignores non-UserRegistered events.
- Handler failure doesn't break registration (non-existent user).
- create_personal_agent is idempotent (tested in test_agent_models.py).
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.modules.agents.handlers import (
    PersonalAgentAutoCreateHandler,
    register_personal_agent_handler,
)
from src.modules.agents.models import Agent, AgentType
from src.modules.agents.repository import AgentRepository
from src.modules.agents.service import create_personal_agent
from src.modules.users.events import UserRegistered
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="auto@example.com",
        password_hash="fake-hash",
        display_name="Auto User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.commit()
    return user


class TestPersonalAgentAutoCreate:
    """Test the PersonalAgentAutoCreateHandler.

    Note: The handler creates its own DB session from settings, so direct
    DB creation tests use create_personal_agent instead. Handler tests
    focus on event filtering, error handling, and bus subscription.
    """

    def test_handler_ignores_non_user_registered(self) -> None:
        """Handler ignores events that are not UserRegistered."""
        from src.events.bus import DomainEvent

        handler = PersonalAgentAutoCreateHandler()
        base_event = DomainEvent()
        handler.handle(base_event)

    def test_handler_failure_does_not_raise(self) -> None:
        """Handler failure is caught and logged, does not raise."""
        handler = PersonalAgentAutoCreateHandler()
        bad_event = UserRegistered(
            event_id="bad-event",
            user_id=uuid4(),  # Non-existent user
            email_hash=hashlib.sha256(b"nonexistent@example.com").hexdigest(),
            occurred_at=datetime.now(UTC),
        )
        # Should not raise
        handler.handle(bad_event)

    def test_register_handler_subscribes_to_event_bus(self) -> None:
        """register_personal_agent_handler subscribes to UserRegistered."""
        from src.events.bus import default_event_bus

        before = default_event_bus.handler_count(UserRegistered)
        register_personal_agent_handler()
        after = default_event_bus.handler_count(UserRegistered)
        assert after > before

    def test_create_personal_agent_idempotent(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Calling create_personal_agent twice returns same agent."""
        result1 = create_personal_agent(test_user, test_db_session)
        result2 = create_personal_agent(test_user, test_db_session)
        assert result1["id"] == result2["id"]

        agents = (
            test_db_session.query(Agent)
            .filter(Agent.owner_user_id == test_user.id)
            .all()
        )
        assert len(agents) == 1

    def test_create_personal_agent_type(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """Created agent is PERSONAL type."""
        result = create_personal_agent(test_user, test_db_session)
        assert result["type"] == AgentType.PERSONAL.value

        repo = AgentRepository(test_db_session)
        agent = repo.get_personal_agent(test_user.id)
        assert agent is not None
        assert agent.owner_user_id == test_user.id
