"""P7-02: Mock Provider tests.

Verifies:
- Same input → same output (reproducible).
- Delay injection works.
- Failure injection returns controllable errors.
- Prompt content is never recorded/logged.
"""
from __future__ import annotations

import time

import pytest

from src.modules.model_gateway.exceptions import ModelUnavailableError
from src.modules.model_gateway.mock_provider import MockProvider
from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    EmbeddingRequest,
    PrivacyContext,
)


def _make_request(*, classification=DataClassification.P2, schema=None):
    return ChatRequest(
        messages=[ChatMessage(role="user", content="test prompt")],
        privacy_context=PrivacyContext(
            data_classification=classification, purpose="test"
        ),
        purpose="test",
        response_schema=schema,
    )


class TestMockProviderChat:
    def test_same_input_same_output(self):
        provider = MockProvider()
        req = _make_request()
        r1 = provider.chat(req)
        r2 = provider.chat(req)
        assert r1.response.content == r2.response.content
        assert r1.status == "completed"

    def test_delay_injection(self):
        provider = MockProvider(delay_ms=100)
        req = _make_request()
        start = time.perf_counter()
        provider.chat(req)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed >= 90  # allow small scheduling slack

    def test_failure_injection_raises(self):
        provider = MockProvider(fail_rate=1.0)
        req = _make_request()
        with pytest.raises(ModelUnavailableError):
            provider.chat(req)
        assert provider.error_count >= 1

    def test_no_failure_when_fail_rate_zero(self):
        provider = MockProvider(fail_rate=0.0)
        req = _make_request()
        resp = provider.chat(req)
        assert resp.status == "completed"

    def test_prompt_not_in_response(self):
        provider = MockProvider()
        req = _make_request()
        resp = provider.chat(req)
        # The mock response must never echo the prompt content.
        assert "test prompt" not in str(resp.response.content)

    def test_structured_output_respects_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "candidates": {"type": "array"},
                "summary": {"type": "string"},
            },
            "required": ["candidates"],
        }
        provider = MockProvider()
        req = _make_request(schema=schema)
        resp = provider.chat(req)
        assert resp.response.type == "STRUCTURED"
        assert "candidates" in resp.response.content

    def test_metadata_present(self):
        provider = MockProvider()
        resp = provider.chat(_make_request())
        assert resp.metadata.provider == "mock"
        assert resp.metadata.latency_ms >= 0
        assert resp.metadata.prompt_tokens is not None

    def test_repr_does_not_leak_prompt(self):
        provider = MockProvider()
        provider.chat(_make_request())
        r = repr(provider)
        assert "test prompt" not in r


class TestMockProviderEmbedding:
    def test_embedding_deterministic(self):
        provider = MockProvider()
        ctx = PrivacyContext(
            data_classification=DataClassification.P2, purpose="test"
        )
        req = EmbeddingRequest(text="hello", privacy_context=ctx)
        r1 = provider.embedding(req)
        r2 = provider.embedding(req)
        assert r1.embedding == r2.embedding
        assert r1.dimension == 8

    def test_embedding_custom_dimension(self):
        provider = MockProvider()
        ctx = PrivacyContext(
            data_classification=DataClassification.P2, purpose="test"
        )
        req = EmbeddingRequest(text="hello", privacy_context=ctx, dimension=16)
        resp = provider.embedding(req)
        assert resp.dimension == 16
        assert len(resp.embedding) == 16


class TestMockProviderHealth:
    def test_health_online_by_default(self):
        provider = MockProvider()
        h = provider.health()
        assert h.healthy is True
        assert h.status.value == "ONLINE"

    def test_health_offline_when_always_failing(self):
        provider = MockProvider(fail_rate=1.0)
        h = provider.health()
        assert h.healthy is False
        assert h.status.value == "OFFLINE"
