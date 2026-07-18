"""P7-07: Model call metadata recording tests.

Verifies:
- AgentRun is created with correct fields.
- Hash lengths are correct (SHA-256 = 64 hex chars).
- Metadata contains no prompt/response content.
"""
from __future__ import annotations

from src.modules.agents.models import Agent, AgentRun, AgentRunStatus, AgentType, DelegationLevel
from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    PrivacyContext,
)
from src.modules.model_gateway.service import ModelGatewayService
from src.modules.users.models import User, UserStatus


def _make_user(session):
    user = User(
        email="test@example.edu",
        password_hash="hash",
        display_name="Test",
        global_role="STUDENT",
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()
    return user


def _make_agent(session, user):
    agent = Agent(
        owner_user_id=user.id,
        type=AgentType.PERSONAL.value,
        name="Test Agent",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    session.add(agent)
    session.flush()
    return agent


class TestMetadataRecording:
    def test_agent_run_created(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="private prompt content")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="meal_planning"
            ),
            purpose="meal_planning",
        )
        service.chat(
            req,
            session=test_db_session,
            agent_id=agent.id,
            actor_user_id=user.id,
        )
        test_db_session.flush()

        runs = (
            test_db_session.query(AgentRun)
            .filter(AgentRun.agent_id == agent.id)
            .all()
        )
        assert len(runs) == 1
        run = runs[0]
        assert run.status == AgentRunStatus.SUCCESS.value
        assert run.purpose == "meal_planning"
        assert run.model_name is not None

    def test_hash_length_correct(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="content for hashing")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="test"
            ),
            purpose="test",
        )
        resp = service.chat(
            req,
            session=test_db_session,
            agent_id=agent.id,
            actor_user_id=user.id,
        )
        # SHA-256 hex digest = 64 characters.
        assert resp.input_hash is not None
        assert len(resp.input_hash) == 64
        assert resp.output_hash is not None
        assert len(resp.output_hash) == 64

    def test_metadata_no_prompt_content(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()

        secret_prompt = "this_is_a_secret_prompt_do_not_leak"
        req = ChatRequest(
            messages=[ChatMessage(role="user", content=secret_prompt)],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="test"
            ),
            purpose="test",
        )
        service.chat(
            req,
            session=test_db_session,
            agent_id=agent.id,
            actor_user_id=user.id,
        )
        test_db_session.flush()

        run = (
            test_db_session.query(AgentRun)
            .filter(AgentRun.agent_id == agent.id)
            .first()
        )
        assert run is not None
        # The AgentRun record must NOT contain the prompt text.
        assert secret_prompt not in str(run.input_hash)
        assert secret_prompt not in str(run.output_hash)
        assert secret_prompt not in repr(run)
        # input_hash is a hash, not the content.
        assert run.input_hash != secret_prompt

    def test_token_count_recorded(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="count my tokens")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="test"
            ),
            purpose="test",
        )
        service.chat(
            req,
            session=test_db_session,
            agent_id=agent.id,
            actor_user_id=user.id,
        )
        test_db_session.flush()
        run = (
            test_db_session.query(AgentRun)
            .filter(AgentRun.agent_id == agent.id)
            .first()
        )
        assert run is not None
        assert run.token_count is not None
        assert run.token_count > 0
        assert run.latency_ms is not None
        assert run.latency_ms >= 0
