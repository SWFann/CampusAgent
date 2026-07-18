"""P7-03: Rule Provider tests.

Verifies:
- Deterministic output.
- Hard constraints are enforced.
- No model dependency (pure rules).
"""
from __future__ import annotations

import json

from src.modules.model_gateway.rule_provider import RuleProvider
from src.modules.model_gateway.schemas import (
    ChatMessage,
    ChatRequest,
    DataClassification,
    PrivacyContext,
)


def _make_rule_request(candidates, capsule):
    return ChatRequest(
        messages=[ChatMessage(role="user", content=json.dumps(candidates))],
        privacy_context=PrivacyContext(
            data_classification=DataClassification.P2, purpose="meal_planning"
        ),
        purpose="meal_planning",
        preference_capsule=capsule,
    )


class TestRuleProviderDeterminism:
    def test_same_input_same_output(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "Restaurant A", "cuisines": ["粤菜"], "distance_km": 2, "price_tier": "medium"}
        ]
        capsule = {
            "budget_tier": "medium",
            "cuisine_preferences": ["粤菜"],
            "excluded_cuisines": [],
            "distance_limit_km": 5,
            "environment_preference": "quiet",
        }
        req = _make_rule_request(candidates, capsule)
        r1 = provider.chat(req)
        r2 = provider.chat(req)
        assert r1.response.content == r2.response.content

    def test_output_is_structured(self):
        provider = RuleProvider()
        req = _make_rule_request(
            [{"id": "r1", "name": "A", "cuisines": ["粤菜"], "distance_km": 2, "price_tier": "medium"}],
            {"budget_tier": "medium", "cuisine_preferences": ["粤菜"], "distance_limit_km": 5},
        )
        resp = provider.chat(req)
        assert resp.response.type == "STRUCTURED"
        assert "candidates" in resp.response.content
        assert resp.response.content["engine"] == "rule"


class TestRuleProviderHardConstraints:
    def test_budget_violation_rejected(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "Expensive", "cuisines": ["粤菜"], "distance_km": 1, "price_tier": "high"},
        ]
        capsule = {"budget_tier": "low", "cuisine_preferences": [], "distance_limit_km": 10}
        req = _make_rule_request(candidates, capsule)
        resp = provider.chat(req)
        result = resp.response.content["candidates"][0]
        assert result["passes_hard"] is False
        assert result["score"] == 0.0

    def test_excluded_cuisine_rejected(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "X", "cuisines": ["川菜"], "distance_km": 1, "price_tier": "low"},
        ]
        capsule = {
            "budget_tier": "low",
            "cuisine_preferences": [],
            "excluded_cuisines": ["川菜"],
            "distance_limit_km": 10,
        }
        req = _make_rule_request(candidates, capsule)
        resp = provider.chat(req)
        result = resp.response.content["candidates"][0]
        assert result["passes_hard"] is False

    def test_distance_violation_rejected(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "Far", "cuisines": ["粤菜"], "distance_km": 10, "price_tier": "low"},
        ]
        capsule = {"budget_tier": "low", "cuisine_preferences": [], "distance_limit_km": 3}
        req = _make_rule_request(candidates, capsule)
        resp = provider.chat(req)
        result = resp.response.content["candidates"][0]
        assert result["passes_hard"] is False

    def test_passing_candidate_has_positive_score(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "Good", "cuisines": ["粤菜"], "distance_km": 1, "price_tier": "medium", "environment": "quiet"},
        ]
        capsule = {
            "budget_tier": "medium",
            "cuisine_preferences": ["粤菜"],
            "distance_limit_km": 5,
            "environment_preference": "quiet",
        }
        req = _make_rule_request(candidates, capsule)
        resp = provider.chat(req)
        result = resp.response.content["candidates"][0]
        assert result["passes_hard"] is True
        assert result["score"] > 0.0


class TestRuleProviderNoModelDependency:
    def test_safe_public_summary_no_private_data(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "A", "cuisines": ["粤菜"], "distance_km": 2, "price_tier": "medium"},
        ]
        capsule = {"budget_tier": "medium", "cuisine_preferences": ["粤菜"], "distance_limit_km": 5}
        req = _make_rule_request(candidates, capsule)
        resp = provider.chat(req)
        summary = resp.response.content["candidates"][0]["safe_public_summary"]
        # Summary must not contain raw preference data or member info.
        assert "budget_tier" not in summary
        assert "medium" not in summary

    def test_reason_codes_filtered(self):
        provider = RuleProvider()
        candidates = [
            {"id": "r1", "name": "A", "cuisines": ["粤菜"], "distance_km": 2, "price_tier": "medium"},
        ]
        capsule = {"budget_tier": "medium", "cuisine_preferences": ["粤菜"], "distance_limit_km": 5}
        req = _make_rule_request(candidates, capsule)
        resp = provider.chat(req)
        codes = resp.response.content["candidates"][0]["reason_codes"]
        allowed = {
            "within_budget", "cuisine_match", "within_distance",
            "environment_match", "hard_constraint_violation", "no_match",
        }
        for c in codes:
            assert c in allowed

    def test_empty_candidates(self):
        provider = RuleProvider()
        req = _make_rule_request([], {"budget_tier": "low"})
        resp = provider.chat(req)
        assert resp.response.content["count"] == 0
        assert "no_match" in resp.response.content.get("reason_codes", [])

    def test_health_always_online(self):
        provider = RuleProvider()
        h = provider.health()
        assert h.healthy is True
        assert h.status.value == "ONLINE"
