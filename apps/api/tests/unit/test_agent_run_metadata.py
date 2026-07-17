"""P6-13: AgentRun metadata tests.

AgentRun only stores:
- hash (input_hash, output_hash)
- model_name
- token_count
- latency_ms
- status

It must NOT store prompt/response content.

Tests:
- AgentRun can be created with metadata only.
- No prompt/response fields exist.
- repr does not contain hashes.
- Multiple runs can be associated with one agent.
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from src.modules.agents.models import (
    Agent,
    AgentRun,
    AgentRunStatus,
    AgentStatus,
    AgentType,
    DelegationLevel,
)
from src.modules.agents.repository import AgentRepository
from src.modules.users.models import GlobalRole, User, UserStatus


@pytest.fixture()
def test_user(test_db_session: Session) -> User:
    user = User(
        email="run@example.com",
        password_hash="fake",
        display_name="Run User",
        global_role=GlobalRole.STUDENT.value,
        status=UserStatus.ACTIVE.value,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture()
def test_agent(test_db_session: Session, test_user: User) -> Agent:
    agent = Agent(
        owner_user_id=test_user.id,
        type=AgentType.PERSONAL.value,
        name="Run Agent",
        delegation_level=DelegationLevel.L0.value,
        status=AgentStatus.ACTIVE.value,
    )
    test_db_session.add(agent)
    test_db_session.flush()
    return agent


class TestAgentRunMetadata:
    """Test AgentRun metadata model."""

    def test_create_run_with_metadata(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """AgentRun can be created with metadata only."""
        run = AgentRun(
            agent_id=test_agent.id,
            actor_user_id=test_user.id,
            purpose="chat_reply",
            input_hash="sha256:abc123",
            output_hash="sha256:def456",
            model_name="mock-model-v1",
            token_count=150,
            latency_ms=42,
            status=AgentRunStatus.SUCCESS.value,
        )
        test_db_session.add(run)
        test_db_session.flush()

        assert run.id is not None
        assert run.input_hash == "sha256:abc123"
        assert run.output_hash == "sha256:def456"
        assert run.model_name == "mock-model-v1"
        assert run.token_count == 150
        assert run.latency_ms == 42
        assert run.status == "SUCCESS"

    def test_no_prompt_response_fields(self) -> None:
        """AgentRun must not have prompt or response fields."""
        col_names = {c.name for c in AgentRun.__table__.columns}
        forbidden = {"prompt", "response", "input_text", "output_text", "input_content", "output_content"}
        assert not forbidden.intersection(col_names), (
            f"Forbidden columns: {forbidden.intersection(col_names)}"
        )

    def test_has_only_hash_metadata_fields(self) -> None:
        """AgentRun has only hash and metadata fields."""
        col_names = {c.name for c in AgentRun.__table__.columns}
        expected = {
            "id", "agent_id", "actor_user_id", "purpose",
            "input_hash", "output_hash", "model_name",
            "token_count", "latency_ms", "status", "created_at",
        }
        assert col_names == expected, f"Unexpected columns: {col_names - expected}"

    def test_repr_no_hashes(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """repr must not contain input/output hashes."""
        run = AgentRun(
            agent_id=test_agent.id,
            actor_user_id=test_user.id,
            purpose="chat_reply",
            input_hash="secret-input-hash-value",
            output_hash="secret-output-hash-value",
            status=AgentRunStatus.SUCCESS.value,
        )
        repr_str = repr(run)
        assert "secret-input-hash-value" not in repr_str
        assert "secret-output-hash-value" not in repr_str

    def test_multiple_runs_per_agent(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """Multiple runs can be associated with one agent."""
        for i in range(3):
            run = AgentRun(
                agent_id=test_agent.id,
                actor_user_id=test_user.id,
                purpose="chat_reply",
                input_hash=f"hash-{i}",
                output_hash=f"out-{i}",
                model_name="mock-model",
                token_count=100 * (i + 1),
                latency_ms=10 * (i + 1),
                status=AgentRunStatus.SUCCESS.value,
            )
            test_db_session.add(run)
        test_db_session.flush()

        repo = AgentRepository(test_db_session)
        agent = repo.get_by_id(test_agent.id)
        assert agent is not None
        assert len(agent.runs) == 3

    def test_run_with_failed_status(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """AgentRun can have FAILED status."""
        run = AgentRun(
            agent_id=test_agent.id,
            actor_user_id=test_user.id,
            purpose="chat_reply",
            status=AgentRunStatus.FAILED.value,
        )
        test_db_session.add(run)
        test_db_session.flush()
        assert run.status == "FAILED"

    def test_run_with_timeout_status(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """AgentRun can have TIMEOUT status."""
        run = AgentRun(
            agent_id=test_agent.id,
            actor_user_id=test_user.id,
            purpose="scene_execution",
            status=AgentRunStatus.TIMEOUT.value,
            latency_ms=30000,
        )
        test_db_session.add(run)
        test_db_session.flush()
        assert run.status == "TIMEOUT"

    def test_run_nullable_fields(
        self, test_db_session: Session, test_user: User, test_agent: Agent
    ) -> None:
        """AgentRun hash, model, token, latency can be null."""
        run = AgentRun(
            agent_id=test_agent.id,
            actor_user_id=test_user.id,
            purpose="chat_reply",
            status=AgentRunStatus.SUCCESS.value,
        )
        test_db_session.add(run)
        test_db_session.flush()
        assert run.input_hash is None
        assert run.output_hash is None
        assert run.model_name is None
        assert run.token_count is None
        assert run.latency_ms is None
