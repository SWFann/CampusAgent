"""P7-01: Model Gateway contract tests.

Verifies:
- ChatRequest schema is serialisable.
- privacy_context is mandatory.
- P4 defaults to requires_local.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    PrivacyContext,
)


class TestPrivacyContext:
    """PrivacyContext validation."""

    def test_privacy_context_required_fields(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P2,
            purpose="meal_planning",
        )
        assert ctx.data_classification == DataClassification.P2
        assert ctx.allow_external is False
        assert ctx.requires_local is False

    def test_p4_forces_requires_local(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P4,
            purpose="meal_planning",
            allow_external=True,
            requires_local=False,
        )
        assert ctx.requires_local is True
        assert ctx.allow_external is False

    def test_p3_blocks_external(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P3,
            purpose="agent_chat",
            allow_external=True,
        )
        assert ctx.allow_external is False

    def test_p0_allows_external_if_requested(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P0,
            purpose="agent_chat",
            allow_external=True,
        )
        assert ctx.allow_external is True

    def test_purpose_required(self):
        with pytest.raises(ValidationError):
            PrivacyContext(data_classification=DataClassification.P1)  # type: ignore[call-arg]

    def test_is_external_blocked_for_p4(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P4,
            purpose="meal_planning",
        )
        assert ctx.is_external_blocked is True

    def test_is_external_blocked_for_p3(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P3,
            purpose="agent_chat",
        )
        assert ctx.is_external_blocked is True

    def test_is_external_allowed_for_p0_with_flag(self):
        ctx = PrivacyContext(
            data_classification=DataClassification.P0,
            purpose="agent_chat",
            allow_external=True,
        )
        assert ctx.is_external_blocked is False

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            PrivacyContext(
                data_classification=DataClassification.P1,
                purpose="test",
                secret_field="leak",  # type: ignore[call-arg]
            )


class TestChatRequest:
    """ChatRequest schema tests."""

    def _make_ctx(self, classification=DataClassification.P2):
        return PrivacyContext(
            data_classification=classification,
            purpose="meal_planning",
        )

    def test_chat_request_serialisable(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="hello")],
            privacy_context=self._make_ctx(),
            purpose="meal_planning",
        )
        dumped = req.model_dump()
        assert "messages" in dumped
        assert "privacy_context" in dumped
        # Round-trip
        restored = ChatRequest(**dumped)
        assert restored.privacy_context.purpose == "meal_planning"

    def test_privacy_context_mandatory(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role="user", content="hello")],
                purpose="meal_planning",
            )  # type: ignore[call-arg]

    def test_messages_must_be_nonempty(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[],
                privacy_context=self._make_ctx(),
                purpose="meal_planning",
            )

    def test_timeout_bounds(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role="user", content="hi")],
                privacy_context=self._make_ctx(),
                purpose="meal_planning",
                timeout_ms=50,  # below minimum
            )

    def test_p4_request_has_requires_local(self):
        req = ChatRequest(
            messages=[ChatMessage(role="user", content="private data")],
            privacy_context=self._make_ctx(DataClassification.P4),
            purpose="meal_planning",
        )
        assert req.privacy_context.requires_local is True
        assert req.privacy_context.allow_external is False

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            ChatRequest(
                messages=[ChatMessage(role="user", content="hi")],
                privacy_context=self._make_ctx(),
                purpose="meal_planning",
                secret="leak",  # type: ignore[call-arg]
            )
