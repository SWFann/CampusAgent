"""P7-12: Model Gateway privacy leakage tests.

End-to-end privacy verification for the model gateway. These tests are the
"red team" of the P7 phase — they actively try to leak sensitive data and
assert that the gateway prevents every leak vector.

Covers (P7 guide §10–11, §15):
- Prompt content never appears in response, metrics, logs, or errors.
- Response content never appears in metrics, AgentRun, or errors.
- P4 data forces local-only routing (requires_local=True).
- P3/P4 data cannot route to an external provider.
- Missing privacy_context → fail-closed rejection.
- AgentRun records only hashes — never prompt/response content.
- Structured-output validation errors never include the invalid raw output.
- OpenAI-compatible provider never leaks api_key in repr or error details.
- Metrics labels never carry prompt, response, user email, or raw endpoint.
- RoutingDecision never includes sensitive fields.
"""
from __future__ import annotations

import hashlib
import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from src.modules.agents.models import Agent, AgentRun, AgentRunStatus, AgentType, DelegationLevel
from src.modules.model_gateway.exceptions import (
    PrivacyContextMissingError,
    PrivacyContextSensitiveExternalBlockedError,
    StructuredOutputValidationError,
)
from src.modules.model_gateway.metrics import ModelGatewayMetrics
from src.modules.model_gateway.mock_provider import MockProvider
from src.modules.model_gateway.openai_compatible import OpenAICompatibleProvider
from src.modules.model_gateway.providers import ProviderType
from src.modules.model_gateway.router import ProviderCandidate, RoutingPolicy
from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    PrivacyContext,
    RoutingDecision,
)
from src.modules.model_gateway.service import ModelGatewayService
from src.modules.users.models import User, UserStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(session):
    user = User(
        email="privacy-test@example.edu",
        password_hash="hash",
        display_name="Privacy Test",
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
        name="Privacy Agent",
        delegation_level=DelegationLevel.L0.value,
        status="ACTIVE",
    )
    session.add(agent)
    session.flush()
    return agent


def _make_request(
    *,
    content="secret-prompt-do-not-leak",
    classification=DataClassification.P2,
    allow_external=False,
    requires_local=False,
    schema=None,
):
    return ChatRequest(
        messages=[ChatMessage(role="user", content=content)],
        privacy_context=PrivacyContext(
            data_classification=classification,
            purpose="privacy_test",
            allow_external=allow_external,
            requires_local=requires_local,
        ),
        purpose="privacy_test",
        response_schema=schema,
    )


class _FakeExternalProvider:
    """Fake external provider for testing routing privacy gates."""

    def __init__(self, *, name="external-leak-test"):
        self.name = name
        self.provider_type = ProviderType.OPENAI_COMPATIBLE
        self.is_external = True

    def chat(self, request):
        from src.modules.model_gateway.schemas import (
            CallMetadata,
            ChatResponse,
            ResponseContent,
        )
        return ChatResponse(
            status="completed",
            response=ResponseContent(type="TEXT", content="external-response"),
            metadata=CallMetadata(latency_ms=10, provider=self.name),
        )

    def embedding(self, request):
        from src.modules.model_gateway.schemas import CallMetadata, EmbeddingResponse
        return EmbeddingResponse(
            status="completed",
            embedding=[0.0],
            dimension=1,
            metadata=CallMetadata(latency_ms=10, provider=self.name),
        )

    def health(self):
        from src.modules.model_gateway.schemas import ProviderHealth, ProviderHealthStatus
        return ProviderHealth(
            provider_name=self.name,
            healthy=True,
            status=ProviderHealthStatus.ONLINE,
        )


# ---------------------------------------------------------------------------
# P4 forces local-only
# ---------------------------------------------------------------------------


class TestP4ForcesLocal:
    def test_p4_sets_requires_local(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P4,
            purpose="test",
            requires_local=False,  # even if caller sets False
        )
        assert ctx.requires_local is True

    def test_p4_blocks_external(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P4,
            purpose="test",
            allow_external=True,  # even if caller sets True
        )
        assert ctx.allow_external is False

    def test_p3_blocks_external(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P3,
            purpose="test",
            allow_external=True,
        )
        assert ctx.allow_external is False

    def test_p4_is_external_blocked_property(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P4,
            purpose="test",
        )
        assert ctx.is_external_blocked is True

    def test_p0_allow_external_not_blocked(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P0,
            purpose="test",
            allow_external=True,
        )
        assert ctx.is_external_blocked is False


# ---------------------------------------------------------------------------
# Fail-closed on missing privacy context
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_missing_privacy_context_raises(self):
        """A request without privacy_context must be rejected before any call."""
        service = ModelGatewayService()
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="test"
            ),
            purpose="test",
        )
        # Simulate missing context by setting to None at the service layer.
        # The service validates presence before routing.
        req.privacy_context = None  # type: ignore[assignment]
        with pytest.raises(PrivacyContextMissingError):
            service.chat(req)

    def test_fail_closed_before_provider_call(self):
        """The privacy gate runs BEFORE any provider is selected."""
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        service = ModelGatewayService(routing_policy=policy)
        req = _make_request(classification=DataClassification.P4)
        # The request should route to mock (local), never to external.
        resp = service.chat(req)
        # External provider must NOT have been called.
        # (If it was called, it would return "external-response".)
        # The mock returns its fixed output, which is different.
        assert "external-response" not in str(resp.response.content)


# ---------------------------------------------------------------------------
# P3/P4 cannot route to external
# ---------------------------------------------------------------------------


class TestSensitiveExternalBlocked:
    def test_p4_external_only_raises(self):
        external = _FakeExternalProvider()
        policy = RoutingPolicy([ProviderCandidate(provider=external, priority=10)])
        req = _make_request(classification=DataClassification.P4)
        with pytest.raises(PrivacyContextSensitiveExternalBlockedError):
            policy.select(req)

    def test_p3_external_only_raises(self):
        external = _FakeExternalProvider()
        policy = RoutingPolicy([ProviderCandidate(provider=external, priority=10)])
        req = _make_request(classification=DataClassification.P3)
        with pytest.raises(PrivacyContextSensitiveExternalBlockedError):
            policy.select(req)

    def test_p4_with_external_and_mock_routes_to_mock(self):
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        req = _make_request(classification=DataClassification.P4)
        provider, decision = policy.select(req)
        assert provider.name == "mock"
        assert decision.privacy_blocked_external is True

    def test_fallback_never_uses_external(self):
        """select_for_fallback must never return an external provider."""
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        req = _make_request(
            classification=DataClassification.P0, allow_external=True
        )
        fallback = policy.select_for_fallback(req)
        assert fallback is not None
        assert fallback.is_external is False


# ---------------------------------------------------------------------------
# Prompt content never leaks
# ---------------------------------------------------------------------------


class TestPromptNoLeak:
    def test_prompt_not_in_response_content(self):
        service = ModelGatewayService()
        secret = "MY_SECRET_PROMPT_12345"
        req = _make_request(content=secret)
        resp = service.chat(req)
        assert secret not in str(resp.response.content)
        assert secret not in str(resp.model_dump())

    def test_prompt_not_in_metrics(self):
        metrics = ModelGatewayMetrics()
        service = ModelGatewayService()
        service._metrics = metrics
        secret = "secret_prompt_for_metrics_check"
        req = _make_request(content=secret)
        service.chat(req)
        snap = metrics.snapshot()
        prom = metrics.to_prometheus_text()
        combined = str(snap) + prom
        assert secret not in combined

    def test_prompt_not_in_agent_run(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()
        secret = "do_not_store_this_prompt_anywhere"
        req = _make_request(content=secret)
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
        # Check every field of the AgentRun for the secret prompt.
        run_str = str(run.__dict__) + repr(run)
        assert secret not in run_str
        assert run.input_hash != secret
        assert run.output_hash != secret

    def test_prompt_not_in_routing_decision(self):
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        secret = "routing_secret_prompt"
        req = _make_request(content=secret)
        _, decision = policy.select(req)
        # RoutingDecision fields: provider_type, provider_name, reason,
        # privacy_blocked_external — none should contain the prompt.
        decision_str = decision.model_dump_json()
        assert secret not in decision_str


# ---------------------------------------------------------------------------
# Response content never leaks into metrics/AgentRun
# ---------------------------------------------------------------------------


class TestResponseNoLeak:
    def test_response_not_in_metrics(self):
        metrics = ModelGatewayMetrics()
        service = ModelGatewayService()
        service._metrics = metrics
        req = _make_request()
        resp = service.chat(req)
        # The response content should not appear in any metric label.
        snap = metrics.snapshot()
        prom = metrics.to_prometheus_text()
        combined = str(snap) + prom
        content_str = str(resp.response.content)
        # Only check non-trivial content.
        if content_str and len(content_str) > 3:
            assert content_str not in combined

    def test_response_not_in_agent_run(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()
        req = _make_request()
        resp = service.chat(
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
        content_str = str(resp.response.content)
        run_str = str(run.__dict__) + repr(run)
        if content_str and len(content_str) > 3:
            assert content_str not in run_str


# ---------------------------------------------------------------------------
# Hash integrity (content discarded, hash retained)
# ---------------------------------------------------------------------------


class TestHashIntegrity:
    def test_input_hash_is_sha256(self):
        service = ModelGatewayService()
        req = _make_request(content="hashable content")
        resp = service.chat(req)
        assert resp.input_hash is not None
        # SHA-256 hex digest = 64 chars.
        assert len(resp.input_hash) == 64
        # Must be valid hex.
        int(resp.input_hash, 16)

    def test_output_hash_is_sha256(self):
        service = ModelGatewayService()
        req = _make_request()
        resp = service.chat(req)
        assert resp.output_hash is not None
        assert len(resp.output_hash) == 64
        int(resp.output_hash, 16)

    def test_same_input_same_hash(self):
        service = ModelGatewayService()
        req1 = _make_request(content="identical content")
        req2 = _make_request(content="identical content")
        r1 = service.chat(req1)
        r2 = service.chat(req2)
        assert r1.input_hash == r2.input_hash

    def test_different_input_different_hash(self):
        service = ModelGatewayService()
        r1 = service.chat(_make_request(content="content A"))
        r2 = service.chat(_make_request(content="content B"))
        assert r1.input_hash != r2.input_hash

    def test_hash_not_equal_to_content(self):
        service = ModelGatewayService()
        secret = "plaintext_secret"
        req = _make_request(content=secret)
        resp = service.chat(req)
        assert resp.input_hash != secret
        # The hash should not be reversible to the content.
        assert secret not in resp.input_hash


# ---------------------------------------------------------------------------
# Structured-output validation errors never include raw output
# ---------------------------------------------------------------------------


class TestStructuredOutputNoLeak:
    def test_validation_error_excludes_raw_content(self):
        from src.modules.model_gateway.service import _validate_structured_output

        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        raw_with_secret = {"secret_field": "leak_this_if_you_can"}
        try:
            _validate_structured_output(raw_with_secret, schema)
        except StructuredOutputValidationError as exc:
            assert "leak_this_if_you_can" not in str(exc)
            assert "leak_this_if_you_can" not in str(exc.details)
            assert "secret_field" not in str(exc.details)

    def test_invalid_json_error_excludes_raw(self):
        from src.modules.model_gateway.service import _validate_structured_output

        schema = {"type": "object", "properties": {}}
        secret_json = '{"secret": "do_not_leak_this_value"}'
        try:
            _validate_structured_output(secret_json, schema)
        except StructuredOutputValidationError as exc:
            assert "do_not_leak_this_value" not in str(exc)
            assert "do_not_leak_this_value" not in str(exc.details)


# ---------------------------------------------------------------------------
# OpenAI-compatible provider never leaks api_key
# ---------------------------------------------------------------------------


class TestOpenAICompatibleNoLeak:
    def test_repr_excludes_api_key(self):
        secret_key = "sk-super-secret-api-key-12345"
        provider = OpenAICompatibleProvider(
            base_url="http://vllm.example.edu:8000/v1",
            model="test-model",
            api_key=secret_key,
        )
        r = repr(provider)
        assert secret_key not in r
        assert "api_key" not in r.lower() or "sk-" not in r

    def test_secretstr_not_in_repr(self):
        secret = SecretStr("sk-another-secret-key")
        provider = OpenAICompatibleProvider(
            base_url="http://vllm.example.edu:8000/v1",
            model="test-model",
            api_key=secret,
        )
        r = repr(provider)
        assert secret.get_secret_value() not in r

    def test_error_details_exclude_api_key(self):
        """When the provider errors, the api_key must not appear in details."""
        secret_key = "sk-leak-test-key-99999"

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        provider = OpenAICompatibleProvider(
            base_url="http://unreachable.example.edu:8000/v1",
            model="test-model",
            api_key=secret_key,
            max_retries=0,
            transport=httpx.MockTransport(handler),
        )
        from src.modules.model_gateway.exceptions import ExternalProviderError
        from src.modules.model_gateway.schemas import (
            EmbeddingRequest,
        )

        ctx = PrivacyContext(
            data_classification=DataClassification.P0, purpose="test"
        )
        req = EmbeddingRequest(text="test", privacy_context=ctx)
        with pytest.raises(ExternalProviderError) as exc_info:
            provider.embedding(req)
        error_str = str(exc_info.value) + str(exc_info.value.details)
        assert secret_key not in error_str

    def test_host_hash_not_reversible(self):
        provider = OpenAICompatibleProvider(
            base_url="http://vllm.inference.svc.cluster.local:8000/v1",
            model="test-model",
        )
        hh = provider.host_hash
        # Host hash should be a short hex string, not the hostname.
        assert "vllm.inference.svc" not in hh
        assert "cluster.local" not in hh
        assert len(hh) <= 16

    def test_request_body_not_logged(self, caplog):
        """The provider must never log the request body (prompt content)."""
        import logging

        secret_prompt = "DO_NOT_LOG_THIS_PROMPT"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "model": "test-model",
                    "choices": [{"message": {"content": "response"}}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 1},
                },
            )

        provider = OpenAICompatibleProvider(
            base_url="http://vllm.example.edu:8000/v1",
            model="test-model",
            api_key="sk-test",
            max_retries=0,
            transport=httpx.MockTransport(handler),
        )
        ctx = PrivacyContext(
            data_classification=DataClassification.P0,
            purpose="test",
            allow_external=True,
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content=secret_prompt)],
            privacy_context=ctx,
            purpose="test",
        )
        with caplog.at_level(logging.DEBUG, logger="campus_agent.model_gateway.openai_compatible"):
            provider.chat(req)
        # The secret prompt must not appear in any log record.
        for record in caplog.records:
            assert secret_prompt not in record.getMessage()
            if record.args:
                assert secret_prompt not in str(record.args)


# ---------------------------------------------------------------------------
# Metrics labels never carry sensitive data
# ---------------------------------------------------------------------------


class TestMetricsNoSensitiveLabels:
    def test_no_prompt_in_metrics(self):
        metrics = ModelGatewayMetrics()
        service = ModelGatewayService()
        service._metrics = metrics
        secret = "prompt_secret_for_metrics"
        req = _make_request(content=secret)
        service.chat(req)
        snap = metrics.snapshot()
        prom = metrics.to_prometheus_text()
        assert secret not in str(snap)
        assert secret not in prom

    def test_no_user_email_in_metrics(self):
        """User email should never be used as a metric label."""
        metrics = ModelGatewayMetrics()
        metrics.record_call(
            provider_type="mock",
            provider_name="mock",
            status="completed",
            latency_ms=10,
        )
        snap = metrics.snapshot()
        prom = metrics.to_prometheus_text()
        # No @ symbol should appear (emails contain @).
        assert "@" not in str(snap)
        assert "@" not in prom

    def test_no_raw_endpoint_in_metrics(self):
        """Raw endpoint URLs with potential tokens must not appear."""
        metrics = ModelGatewayMetrics()
        raw_url = "http://vllm.inference.svc.cluster.local:8000/v1?token=secret"
        metrics.record_call(
            provider_type="openai_compatible",
            provider_name="local-vllm",
            status="completed",
            latency_ms=10,
        )
        snap = metrics.snapshot()
        prom = metrics.to_prometheus_text()
        assert raw_url not in str(snap)
        assert raw_url not in prom


# ---------------------------------------------------------------------------
# RoutingDecision is non-sensitive
# ---------------------------------------------------------------------------


class TestRoutingDecisionNonSensitive:
    def test_decision_fields_are_safe(self):
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        req = _make_request(
            classification=DataClassification.P0, allow_external=True
        )
        _, decision = policy.select(req)
        # RoutingDecision should only have non-sensitive fields.
        dump = decision.model_dump()
        allowed_keys = {"provider_type", "provider_name", "reason", "privacy_blocked_external"}
        assert set(dump.keys()) == allowed_keys

    def test_decision_model_extra_forbidden(self):
        """RoutingDecision must reject extra fields (no injection)."""
        with pytest.raises(ValidationError):
            RoutingDecision(
                provider_type="mock",
                provider_name="mock",
                reason="test",
                prompt="secret",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# AgentRun records only non-sensitive fields
# ---------------------------------------------------------------------------


class TestAgentRunPrivacy:
    def test_agent_run_has_no_content_columns(self, test_db_session):
        """AgentRun should not have prompt_text or response_text columns."""
        # Inspect the ORM model columns.
        column_names = {c.name for c in AgentRun.__table__.columns}
        assert "input_hash" in column_names
        assert "output_hash" in column_names
        # There should be no raw content columns.
        assert "prompt_text" not in column_names
        assert "response_text" not in column_names
        assert "input_text" not in column_names
        assert "output_text" not in column_names
        assert "messages" not in column_names

    def test_agent_run_hashes_are_hashes(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()
        secret = "agent_run_secret_prompt"
        req = _make_request(content=secret)
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
        # input_hash should be a 64-char hex string, not the content.
        assert run.input_hash is not None
        assert len(run.input_hash) == 64
        assert run.input_hash != secret
        # Verify it matches a SHA-256 of the serialised messages.
        blob = json.dumps(
            [{"role": "user", "content": secret}],
            sort_keys=True,
            ensure_ascii=False,
        )
        expected = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        assert run.input_hash == expected

    def test_agent_run_status_recorded(self, test_db_session):
        user = _make_user(test_db_session)
        agent = _make_agent(test_db_session, user)
        service = ModelGatewayService()
        req = _make_request()
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
        assert run.status == AgentRunStatus.SUCCESS.value
