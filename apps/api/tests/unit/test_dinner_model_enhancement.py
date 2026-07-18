"""P9-11: Model enhancement tests.

Tests cover (per P9 guide §13):
- Model prompt only contains safe data (restaurant name, score, reasons, tags).
- Model prompt does NOT contain raw preferences, capsules, evaluations, notes.
- Model failure falls back to rule text.
- Structured output validation.
- check_reason_for_leaks on model output.
- The scenario works completely offline (no model calls needed).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from src.modules.scenes.plugins.dorm_dinner.model_enhancement import (
    build_model_prompt,
    build_safe_response_schema,
    enhance_public_summary,
)


class TestBuildModelPrompt:
    """Tests for build_model_prompt — privacy boundary enforcement."""

    def test_prompt_contains_restaurant_names(self) -> None:
        """The prompt includes restaurant names (public data)."""
        ranked = [
            {"candidate_key": "r001", "score": 0.85, "public_reason": "Good choice"},
        ]
        messages = build_model_prompt(ranked)
        user_msg = messages[-1]["content"]
        assert "r001" in user_msg

    def test_prompt_contains_scores(self) -> None:
        """The prompt includes aggregate scores (public data)."""
        ranked = [
            {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
        ]
        messages = build_model_prompt(ranked)
        user_msg = messages[-1]["content"]
        assert "0.85" in user_msg

    def test_prompt_contains_reasons(self) -> None:
        """The prompt includes allowlisted reason codes (public data)."""
        ranked = [
            {"candidate_key": "r001", "score": 0.85, "public_reason": "Fits budget"},
        ]
        messages = build_model_prompt(ranked)
        user_msg = messages[-1]["content"]
        assert "Fits budget" in user_msg

    def test_prompt_does_not_contain_notes(self) -> None:
        """The prompt must NOT contain notes."""
        ranked = [
            {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
        ]
        messages = build_model_prompt(ranked)
        full_prompt = " ".join(m["content"] for m in messages)
        assert "notes" not in full_prompt.lower()

    def test_prompt_does_not_contain_raw_preferences(self) -> None:
        """The prompt must NOT contain raw preferences."""
        ranked = [
            {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
        ]
        messages = build_model_prompt(ranked)
        full_prompt = " ".join(m["content"] for m in messages)
        # Must not contain private field names.
        for forbidden in ["budget_min", "budget_max", "dietary_restrictions",
                          "cuisine_preferences", "available_time", "distance_preference"]:
            assert forbidden not in full_prompt.lower(), (
                f"Prompt contains forbidden field '{forbidden}'"
            )

    def test_prompt_does_not_contain_user_ids(self) -> None:
        """The prompt must NOT contain user identifiers."""
        ranked = [
            {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
        ]
        messages = build_model_prompt(ranked)
        full_prompt = " ".join(m["content"] for m in messages)
        for forbidden in ["user_id", "email", "student_no", "display_name"]:
            assert forbidden not in full_prompt.lower()

    def test_prompt_limits_to_top_3(self) -> None:
        """The prompt only includes the top 3 candidates."""
        ranked = [
            {"candidate_key": f"r00{i}", "score": 0.9 - i * 0.1, "public_reason": "Good"}
            for i in range(5)
        ]
        messages = build_model_prompt(ranked)
        user_msg = messages[-1]["content"]
        assert "r000" in user_msg
        assert "r001" in user_msg
        assert "r002" in user_msg
        assert "r003" not in user_msg  # 5th candidate (index 4) excluded
        assert "r004" not in user_msg

    def test_system_prompt_instructs_no_private_data(self) -> None:
        """The system prompt instructs the model not to mention private data."""
        ranked = [{"candidate_key": "r001", "score": 0.85, "public_reason": "Good"}]
        messages = build_model_prompt(ranked)
        system_msg = messages[0]["content"]
        assert "individual" in system_msg.lower() or "preferences" in system_msg.lower()


class TestBuildSafeResponseSchema:
    """Tests for build_safe_response_schema."""

    def test_schema_has_summary_field(self) -> None:
        """The schema requires a 'summary' field."""
        schema = build_safe_response_schema()
        assert "summary" in schema["properties"]
        assert "summary" in schema["required"]

    def test_schema_max_length_200(self) -> None:
        """The summary field has a maxLength of 200."""
        schema = build_safe_response_schema()
        assert schema["properties"]["summary"]["maxLength"] == 200

    def test_schema_no_additional_properties(self) -> None:
        """The schema forbids additional properties."""
        schema = build_safe_response_schema()
        assert schema["additionalProperties"] is False


class TestEnhancePublicSummary:
    """Tests for enhance_public_summary."""

    def test_model_success_returns_enhanced(self) -> None:
        """When the model succeeds, the enhanced summary is returned."""
        facade = MagicMock()
        facade.model_chat.return_value = {"content": {"summary": "推荐蜀香居，符合大家口味！"}}

        ranked_result = {
            "public_summary": "Recommended: r001. Good choice",
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == "推荐蜀香居，符合大家口味！"

    def test_model_failure_falls_back_to_rule_text(self) -> None:
        """When the model fails, the rule-based summary is used."""
        facade = MagicMock()
        facade.model_chat.side_effect = Exception("Model unavailable")

        original = "Recommended: r001. Good choice"
        ranked_result = {
            "public_summary": original,
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == original

    def test_empty_candidates_returns_original(self) -> None:
        """Empty ranked_candidates returns the original summary."""
        facade = MagicMock()
        original = "No candidates available."
        ranked_result = {
            "public_summary": original,
            "ranked_candidates": [],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == original
        facade.model_chat.assert_not_called()

    def test_model_returns_leaky_text_falls_back(self) -> None:
        """If the model returns text with forbidden patterns, fall back."""
        facade = MagicMock()
        facade.model_chat.return_value = {
            "content": {"summary": "Because user Zhang San has budget_low"}
        }

        original = "Recommended: r001. Good choice"
        ranked_result = {
            "public_summary": original,
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == original

    def test_model_returns_string_content(self) -> None:
        """When the model returns a string, it's parsed as JSON or used directly."""
        facade = MagicMock()
        facade.model_chat.return_value = {"content": '{"summary": "好推荐！"}'}

        ranked_result = {
            "public_summary": "Original",
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == "好推荐！"

    def test_model_returns_too_long_text_falls_back(self) -> None:
        """If the model returns text over 200 chars, fall back."""
        facade = MagicMock()
        long_text = "a" * 201
        facade.model_chat.return_value = {"content": {"summary": long_text}}

        original = "Recommended: r001. Good choice"
        ranked_result = {
            "public_summary": original,
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == original

    def test_model_returns_empty_string_falls_back(self) -> None:
        """If the model returns an empty string, fall back."""
        facade = MagicMock()
        facade.model_chat.return_value = {"content": {"summary": ""}}

        original = "Recommended: r001. Good choice"
        ranked_result = {
            "public_summary": original,
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        result = enhance_public_summary(ranked_result, facade)
        assert result == original

    def test_model_chat_called_with_p0_classification(self) -> None:
        """The model is called with data_classification='P0' (public only)."""
        facade = MagicMock()
        facade.model_chat.return_value = {"content": {"summary": "好推荐"}}

        ranked_result = {
            "public_summary": "Original",
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        enhance_public_summary(ranked_result, facade)
        call_kwargs = facade.model_chat.call_args.kwargs
        assert call_kwargs["data_classification"] == "P0"

    def test_model_chat_called_with_response_schema(self) -> None:
        """The model is called with a structured response schema."""
        facade = MagicMock()
        facade.model_chat.return_value = {"content": {"summary": "好推荐"}}

        ranked_result = {
            "public_summary": "Original",
            "ranked_candidates": [
                {"candidate_key": "r001", "score": 0.85, "public_reason": "Good"},
            ],
        }
        enhance_public_summary(ranked_result, facade)
        call_kwargs = facade.model_chat.call_args.kwargs
        assert "response_schema" in call_kwargs
        assert call_kwargs["response_schema"]["properties"]["summary"]
