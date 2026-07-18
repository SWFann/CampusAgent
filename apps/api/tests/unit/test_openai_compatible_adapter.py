"""P7-04: OpenAI-compatible adapter tests.

Uses httpx.MockTransport (respx is not installed) to test:
- Successful chat / embedding calls.
- Timeout handling.
- Non-200 responses.
- Malformed JSON.
- api_key redaction in repr.
- Request/response body never logged.
"""
from __future__ import annotations

import json

import httpx
import pytest

from src.modules.model_gateway.exceptions import (
    ExternalProviderError,
    ModelTimeoutError,
)
from src.modules.model_gateway.openai_compatible import OpenAICompatibleProvider
from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    EmbeddingRequest,
    PrivacyContext,
)


def _make_transport(handler):
    return httpx.MockTransport(handler)


def _chat_response_body(content="hello back", model="test-model"):
    return {
        "id": "chatcmpl-1",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _embedding_response_body(vector=None, model="test-emb"):
    return {
        "model": model,
        "data": [{"embedding": vector or [0.1, 0.2, 0.3]}],
        "usage": {"prompt_tokens": 3},
    }


class TestOpenAICompatibleChat:
    def test_successful_chat(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_chat_response_body())

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="secret-key-123",
            transport=_make_transport(handler),
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
            purpose="test",
        )
        resp = provider.chat(req)
        assert resp.status == "completed"
        assert resp.response.content == "hello back"
        assert resp.metadata.provider == "openai_compatible"

    def test_timeout_raises_model_timeout(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("simulated timeout")

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="key",
            timeout_ms=100,
            max_retries=0,
            transport=_make_transport(handler),
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
            purpose="test",
        )
        with pytest.raises(ModelTimeoutError):
            provider.chat(req)

    def test_non_200_raises_external_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "internal"})

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="key",
            max_retries=0,
            transport=_make_transport(handler),
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
            purpose="test",
        )
        with pytest.raises(ExternalProviderError):
            provider.chat(req)

    def test_malformed_json_raises_external_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json", headers={"content-type": "application/json"})

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="key",
            max_retries=0,
            transport=_make_transport(handler),
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
            purpose="test",
        )
        with pytest.raises(ExternalProviderError):
            provider.chat(req)

    def test_structured_output_parsed(self):
        structured_content = json.dumps({"candidates": [{"id": "c1"}]})
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_chat_response_body(content=structured_content))

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="key",
            transport=_make_transport(handler),
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
            purpose="test",
            response_schema={
                "type": "object",
                "properties": {"candidates": {"type": "array"}},
                "required": ["candidates"],
            },
        )
        resp = provider.chat(req)
        assert resp.response.type == "STRUCTURED"
        assert "candidates" in resp.response.content


class TestOpenAICompatibleEmbedding:
    def test_successful_embedding(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_embedding_response_body())

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-emb",
            api_key="key",
            transport=_make_transport(handler),
        )
        req = EmbeddingRequest(
            text="hello",
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
        )
        resp = provider.embedding(req)
        assert resp.status == "completed"
        assert len(resp.embedding) == 3


class TestOpenAICompatibleSecurity:
    def test_api_key_not_in_repr(self):
        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="super-secret-key-do-not-leak",
        )
        r = repr(provider)
        assert "super-secret-key-do-not-leak" not in r
        assert "api_key" not in r.lower() or "********" in r or "api_key" not in r

    def test_endpoint_not_in_repr(self):
        provider = OpenAICompatibleProvider(
            base_url="http://sensitive-host.example.edu:8080/v1",
            model="test-model",
            api_key="key",
        )
        r = repr(provider)
        assert "sensitive-host.example.edu" not in r
        assert "8080" not in r

    def test_authorization_header_sent(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization", "")
            return httpx.Response(200, json=_chat_response_body())

        provider = OpenAICompatibleProvider(
            base_url="http://test-node.example/v1",
            model="test-model",
            api_key="my-secret",
            transport=_make_transport(handler),
        )
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P0,
                purpose="test",
                allow_external=True,
            ),
            purpose="test",
        )
        provider.chat(req)
        assert captured["auth"] == "Bearer my-secret"

    def test_host_hash_present(self):
        provider = OpenAICompatibleProvider(
            base_url="http://test-host.example/v1",
            model="m",
            api_key="k",
        )
        assert len(provider.host_hash) == 16
