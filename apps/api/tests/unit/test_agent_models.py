"""P6-01: Agent model tests.

Tests:
- personal agent creation succeeds.
- owner_user_id is required.
- delegation L0-L3 valid.
- L4 rejected.
- private_config_encrypted does not appear in repr.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.modules.agents.exceptions import InvalidDelegationLevelError
from src.modules.agents.models import (
    Agent,
    AgentRun,
    AgentRunStatus,
    AgentStatus,
    AgentType,
    DelegationLevel,
)
from src.modules.agents.service import _validate_delegation_level, create_personal_agent
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash="fake-hash",
        display_name="Test User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


class TestAgentModel:
    """Test Agent ORM model."""

    def test_personal_agent_creation(self, test_db_session: Session, test_user: User) -> None:
        """Personal agent can be created with correct defaults."""
        agent = Agent(
            owner_user_id=test_user.id,
            type=AgentType.PERSONAL.value,
            name="Test Agent",
            delegation_level=DelegationLevel.L0.value,
            status=AgentStatus.ACTIVE.value,
        )
        test_db_session.add(agent)
        test_db_session.flush()

        assert agent.id is not None
        assert agent.type == "PERSONAL"
        assert agent.delegation_level == "L0"
        assert agent.status == "ACTIVE"
        assert agent.created_at is not None
        assert agent.updated_at is not None

    def test_owner_required(self) -> None:
        """Agent requires owner_user_id (enforced at DB level, checked here at model level)."""
        # The model's owner_user_id is nullable=False, so we just verify
        # that the column definition doesn't allow None.
        col = Agent.__table__.c.owner_user_id
        assert not col.nullable

    @pytest.mark.parametrize("level", ["L0", "L1", "L2", "L3"])
    def test_delegation_levels_valid(self, level: str) -> None:
        """L0-L3 are valid delegation levels."""
        _validate_delegation_level(level)  # Should not raise

    def test_l4_rejected(self) -> None:
        """L4 delegation level is rejected in P6."""
        with pytest.raises(InvalidDelegationLevelError):
            _validate_delegation_level("L4")

    def test_private_config_not_in_repr(self, test_db_session: Session, test_user: User) -> None:
        """private_config_encrypted must not appear in __repr__."""
        agent = Agent(
            owner_user_id=test_user.id,
            type=AgentType.PERSONAL.value,
            name="Secret Agent",
            private_config_encrypted="super-secret-config-value",
            delegation_level=DelegationLevel.L0.value,
            status=AgentStatus.ACTIVE.value,
        )
        repr_str = repr(agent)
        assert "super-secret-config-value" not in repr_str
        assert "private_config" not in repr_str.lower()

    def test_agent_status_enum(self) -> None:
        """AgentStatus has correct values."""
        assert AgentStatus.ACTIVE == "ACTIVE"
        assert AgentStatus.DISABLED == "DISABLED"
        assert AgentStatus.DELETED == "DELETED"

    def test_agent_type_enum(self) -> None:
        """AgentType has correct values."""
        assert AgentType.PERSONAL == "PERSONAL"
        assert AgentType.GROUP == "GROUP"
        assert AgentType.ORG == "ORG"

    def test_delegation_level_enum(self) -> None:
        """DelegationLevel has L0-L3, no L4."""
        assert DelegationLevel.L0 == "L0"
        assert DelegationLevel.L1 == "L1"
        assert DelegationLevel.L2 == "L2"
        assert DelegationLevel.L3 == "L3"
        assert not hasattr(DelegationLevel, "L4")


class TestAgentRunModel:
    """Test AgentRun ORM model."""

    def test_agent_run_creation(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """AgentRun can be created with metadata only (no prompt/response)."""
        agent = Agent(
            owner_user_id=test_user.id,
            type=AgentType.PERSONAL.value,
            name="Test Agent",
            delegation_level=DelegationLevel.L0.value,
            status=AgentStatus.ACTIVE.value,
        )
        test_db_session.add(agent)
        test_db_session.flush()

        run = AgentRun(
            agent_id=agent.id,
            actor_user_id=test_user.id,
            purpose="chat_reply",
            input_hash="abc123",
            output_hash="def456",
            model_name="mock-model",
            token_count=100,
            latency_ms=50,
            status=AgentRunStatus.SUCCESS.value,
        )
        test_db_session.add(run)
        test_db_session.flush()

        assert run.id is not None
        assert run.agent_id == agent.id
        assert run.purpose == "chat_reply"
        assert run.status == "SUCCESS"

    def test_agent_run_repr_no_content(
        self, test_db_session: Session, test_user: User
    ) -> None:
        """AgentRun repr must not contain input/output hashes or content."""
        agent = Agent(
            owner_user_id=test_user.id,
            type=AgentType.PERSONAL.value,
            name="Test Agent",
            delegation_level=DelegationLevel.L0.value,
            status=AgentStatus.ACTIVE.value,
        )
        test_db_session.add(agent)
        test_db_session.flush()

        run = AgentRun(
            agent_id=agent.id,
            actor_user_id=test_user.id,
            purpose="chat_reply",
            input_hash="secret-hash",
            output_hash="secret-output",
            status=AgentRunStatus.SUCCESS.value,
        )
        repr_str = repr(run)
        assert "secret-hash" not in repr_str
        assert "secret-output" not in repr_str

    def test_agent_run_status_enum(self) -> None:
        """AgentRunStatus has correct values."""
        assert AgentRunStatus.SUCCESS == "SUCCESS"
        assert AgentRunStatus.FAILED == "FAILED"
        assert AgentRunStatus.TIMEOUT == "TIMEOUT"
        assert AgentRunStatus.CANCELLED == "CANCELLED"


class TestCreatePersonalAgent:
    """Test the create_personal_agent service function."""

    def test_create_via_service(self, test_db_session: Session, test_user: User) -> None:
        """create_personal_agent creates a valid agent."""
        result = create_personal_agent(test_user, test_db_session)
        assert result["type"] == "PERSONAL"
        assert result["delegation_level"] == "L0"
        assert result["status"] == "ACTIVE"
        assert "private_config" not in result  # private config value not returned
        assert result["has_private_config"] is False
