"""P7-05: Routing policy tests.

Verifies:
- P4 + external only → blocked (PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED).
- P1 + allow_external → external allowed.
- Local unhealthy → fallback to mock.
- All failed → MODEL_ROUTING_FAILED.
"""
from __future__ import annotations

import pytest

from src.modules.model_gateway.exceptions import (
    ModelRoutingFailedError,
    PrivacyContextSensitiveExternalBlockedError,
)
from src.modules.model_gateway.mock_provider import MockProvider
from src.modules.model_gateway.providers import ProviderType
from src.modules.model_gateway.router import (
    ProviderCandidate,
    RoutingPolicy,
    build_default_candidates,
)
from src.modules.model_gateway.rule_provider import RuleProvider
from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    PrivacyContext,
)


class _FakeExternalProvider:
    """Fake external provider for testing routing."""

    def __init__(self, *, name="external", healthy=True):
        self.name = name
        self.provider_type = ProviderType.OPENAI_COMPATIBLE
        self.is_external = True
        self._healthy = healthy

    def chat(self, request):
        from src.modules.model_gateway.schemas import CallMetadata, ChatResponse, ResponseContent
        return ChatResponse(
            status="completed",
            response=ResponseContent(type="TEXT", content="external"),
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
        status = ProviderHealthStatus.ONLINE if self._healthy else ProviderHealthStatus.OFFLINE
        return ProviderHealth(
            provider_name=self.name, healthy=self._healthy, status=status
        )


class _FakeLocalProvider:
    """Fake local provider that can be made unhealthy."""

    def __init__(self, *, name="local", healthy=True):
        self.name = name
        self.provider_type = ProviderType.OPENAI_COMPATIBLE
        self.is_external = False
        self._healthy = healthy

    def chat(self, request):
        from src.modules.model_gateway.schemas import CallMetadata, ChatResponse, ResponseContent
        return ChatResponse(
            status="completed",
            response=ResponseContent(type="TEXT", content="local"),
            metadata=CallMetadata(latency_ms=5, provider=self.name),
        )

    def embedding(self, request):
        from src.modules.model_gateway.schemas import CallMetadata, EmbeddingResponse
        return EmbeddingResponse(
            status="completed",
            embedding=[0.0],
            dimension=1,
            metadata=CallMetadata(latency_ms=5, provider=self.name),
        )

    def health(self):
        from src.modules.model_gateway.schemas import ProviderHealth, ProviderHealthStatus
        status = ProviderHealthStatus.ONLINE if self._healthy else ProviderHealthStatus.OFFLINE
        return ProviderHealth(
            provider_name=self.name, healthy=self._healthy, status=status
        )


def _make_request(classification, *, allow_external=False, requires_local=False):
    return ChatRequest(
        messages=[ChatMessage(role="user", content="test")],
        privacy_context=PrivacyContext(
            data_classification=classification,
            purpose="test",
            allow_external=allow_external,
            requires_local=requires_local,
        ),
        purpose="test",
    )


class TestRoutingPolicy:
    def test_p4_external_only_blocked(self):
        external = _FakeExternalProvider()
        policy = RoutingPolicy([ProviderCandidate(provider=external, priority=10)])
        req = _make_request(DataClassification.P4)
        with pytest.raises(PrivacyContextSensitiveExternalBlockedError):
            policy.select(req)

    def test_p1_allow_external_allows_external(self):
        external = _FakeExternalProvider()
        policy = RoutingPolicy([ProviderCandidate(provider=external, priority=10)])
        req = _make_request(DataClassification.P1, allow_external=True)
        provider, decision = policy.select(req)
        assert provider.name == "external"

    def test_local_unhealthy_fallback_to_mock(self):
        local = _FakeLocalProvider(healthy=False)
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=local, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        req = _make_request(DataClassification.P2)
        provider, _ = policy.select(req)
        assert provider.name == "mock"

    def test_all_failed_raises_routing_failed(self):
        local = _FakeLocalProvider(healthy=False)
        external = _FakeExternalProvider(healthy=False)
        # No mock/rule as fallback.
        policy = RoutingPolicy([
            ProviderCandidate(provider=local, priority=10),
            ProviderCandidate(provider=external, priority=50),
        ])
        req = _make_request(DataClassification.P0, allow_external=True)
        with pytest.raises(ModelRoutingFailedError):
            policy.select(req)

    def test_requires_local_blocks_external(self):
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        req = _make_request(DataClassification.P2, requires_local=True)
        provider, _ = policy.select(req)
        assert provider.name == "mock"

    def test_default_candidates_order(self):
        mock = MockProvider()
        rule = RuleProvider()
        candidates = build_default_candidates(mock, rule)
        # mock and rule should be present.
        names = [c.provider.name for c in candidates]
        assert "mock" in names
        assert "rule" in names

    def test_select_for_fallback_excludes_external(self):
        external = _FakeExternalProvider()
        mock = MockProvider()
        policy = RoutingPolicy([
            ProviderCandidate(provider=external, priority=10),
            ProviderCandidate(provider=mock, priority=90),
        ])
        req = _make_request(DataClassification.P0, allow_external=True)
        fallback = policy.select_for_fallback(req)
        # Fallback should never be external.
        assert fallback is not None
        assert fallback.is_external is False
