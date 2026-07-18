"""P9-09 / P9-16: Deterministic aggregation and algorithm tests.

Tests cover (per P9 guide §11, §18):
- Same inputs → same result (determinism).
- Participant order does not affect the result.
- Ties are broken by candidate_key ascending (stable sort).
- Hard gate: any hard_pass=False → candidate eliminated.
- Mean utility computation.
- Fairness penalty (variance-based).
- Distance bonus.
- Budget bonus.
- Empty evaluations.
- All hard pass.
- Extreme weights.
- Empty candidates.
"""
from __future__ import annotations

from src.modules.scenes.plugins.dorm_dinner.algorithm import (
    aggregate_evaluations,
    build_ranked_result,
)
from src.modules.scenes.plugins.dorm_dinner.restaurants import get_restaurant_by_id
from src.modules.scenes.schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
)


def _make_candidate(restaurant_id: str = "r001") -> CandidateInput:
    r = get_restaurant_by_id(restaurant_id)
    assert r is not None
    return CandidateInput(
        candidate_key=r.id,
        display_name=r.name,
        public_metadata=r.to_candidate_metadata(),
    )


def _make_evaluation(
    candidate_key: str = "r001",
    hard_pass: bool = True,
    utility: float = 0.8,
    objection: bool = False,
    reason_codes: list[str] | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        candidate_key=candidate_key,
        hard_pass=hard_pass,
        utility=utility,
        objection=objection,
        reason_codes=reason_codes or ["within_group_budget"],
    )


class TestAggregationBasic:
    """Basic aggregation tests."""

    def test_returns_aggregate_result(self) -> None:
        """aggregate_evaluations returns an AggregateResult."""
        candidate = _make_candidate()
        evals = [_make_evaluation()]
        result = aggregate_evaluations(candidate, evals)
        assert isinstance(result, AggregateResult)

    def test_has_required_fields(self) -> None:
        """AggregateResult has all required fields."""
        candidate = _make_candidate()
        evals = [_make_evaluation()]
        result = aggregate_evaluations(candidate, evals)
        assert hasattr(result, "candidate_key")
        assert hasattr(result, "aggregate_score")
        assert hasattr(result, "public_reason")
        assert hasattr(result, "rank")
        assert hasattr(result, "hard_gate_passed")

    def test_candidate_key_matches(self) -> None:
        """candidate_key in result matches the candidate."""
        candidate = _make_candidate("r002")
        evals = [_make_evaluation(candidate_key="r002")]
        result = aggregate_evaluations(candidate, evals)
        assert result.candidate_key == "r002"


class TestHardGate:
    """Tests for the hard gate (P9-16)."""

    def test_all_hard_pass(self) -> None:
        """All evaluations pass hard gate → hard_gate_passed=True."""
        candidate = _make_candidate()
        evals = [
            _make_evaluation(hard_pass=True),
            _make_evaluation(hard_pass=True),
            _make_evaluation(hard_pass=True),
        ]
        result = aggregate_evaluations(candidate, evals)
        assert result.hard_gate_passed is True
        assert result.aggregate_score > 0

    def test_any_hard_fail_eliminated(self) -> None:
        """Any hard_pass=False → hard_gate_passed=False, score=0."""
        candidate = _make_candidate()
        evals = [
            _make_evaluation(hard_pass=True, utility=0.9),
            _make_evaluation(hard_pass=False, utility=0.1),
            _make_evaluation(hard_pass=True, utility=0.8),
        ]
        result = aggregate_evaluations(candidate, evals)
        assert result.hard_gate_passed is False
        assert result.aggregate_score == 0.0

    def test_all_hard_fail(self) -> None:
        """All hard_pass=False → hard_gate_passed=False."""
        candidate = _make_candidate()
        evals = [
            _make_evaluation(hard_pass=False),
            _make_evaluation(hard_pass=False),
        ]
        result = aggregate_evaluations(candidate, evals)
        assert result.hard_gate_passed is False
        assert result.aggregate_score == 0.0


class TestMeanUtility:
    """Tests for mean utility computation."""

    def test_mean_utility_single_evaluation(self) -> None:
        """Single evaluation: aggregate_score equals utility (plus bonuses)."""
        candidate = _make_candidate("r003")  # distance 5 min
        evals = [_make_evaluation(utility=0.8)]
        result = aggregate_evaluations(candidate, evals)
        # Score = 0.8 - 0 (no fairness penalty for single) + distance_bonus + budget_bonus
        assert result.aggregate_score >= 0.8  # bonuses are positive

    def test_mean_utility_multiple_evaluations(self) -> None:
        """Multiple evaluations: aggregate_score ≈ mean utility + bonuses."""
        candidate = _make_candidate("r003")
        evals = [
            _make_evaluation(utility=0.6),
            _make_evaluation(utility=0.8),
        ]
        result = aggregate_evaluations(candidate, evals)
        # Mean = 0.7, fairness penalty is small (std_dev=0.1, penalty=0.03)
        # Plus bonuses. Should be around 0.7 - 0.03 + bonuses.
        assert 0.6 <= result.aggregate_score <= 0.85

    def test_score_clamped_to_range(self) -> None:
        """Aggregate score is clamped to [0, 1]."""
        candidate = _make_candidate()
        evals = [_make_evaluation(utility=1.0)]
        result = aggregate_evaluations(candidate, evals)
        assert 0.0 <= result.aggregate_score <= 1.0


class TestFairnessPenalty:
    """Tests for fairness penalty (variance-based)."""

    def test_uniform_utilities_no_penalty(self) -> None:
        """When all utilities are the same, fairness penalty is 0."""
        candidate = _make_candidate("r003")
        evals = [
            _make_evaluation(utility=0.7),
            _make_evaluation(utility=0.7),
            _make_evaluation(utility=0.7),
        ]
        result_uniform = aggregate_evaluations(candidate, evals)

        # Compare with non-uniform (same mean).
        evals_varied = [
            _make_evaluation(utility=0.5),
            _make_evaluation(utility=0.7),
            _make_evaluation(utility=0.9),
        ]
        result_varied = aggregate_evaluations(candidate, evals_varied)

        # Uniform should have higher score (no penalty).
        assert result_uniform.aggregate_score > result_varied.aggregate_score

    def test_high_variance_lower_score(self) -> None:
        """Higher variance in utilities leads to lower score."""
        candidate = _make_candidate("r003")
        # Low variance
        evals_low = [
            _make_evaluation(utility=0.7),
            _make_evaluation(utility=0.75),
        ]
        result_low = aggregate_evaluations(candidate, evals_low)

        # High variance (same mean)
        evals_high = [
            _make_evaluation(utility=0.5),
            _make_evaluation(utility=0.95),
        ]
        result_high = aggregate_evaluations(candidate, evals_high)

        assert result_low.aggregate_score > result_high.aggregate_score


class TestBonuses:
    """Tests for distance and budget bonuses."""

    def test_closer_restaurant_gets_distance_bonus(self) -> None:
        """Closer restaurants get a higher distance bonus."""
        # r010 (速食工坊): distance 3 min
        # r006 (樱花日料): distance 22 min
        evals = [_make_evaluation(utility=0.7)]

        candidate_close = _make_candidate("r010")
        result_close = aggregate_evaluations(candidate_close, evals)

        candidate_far = _make_candidate("r006")
        result_far = aggregate_evaluations(candidate_far, evals)

        assert result_close.aggregate_score > result_far.aggregate_score


class TestDeterminism:
    """Tests for deterministic aggregation (P9-16)."""

    def test_same_input_same_output(self) -> None:
        """Same inputs always produce the same output."""
        candidate = _make_candidate("r003")
        evals = [
            _make_evaluation(utility=0.6),
            _make_evaluation(utility=0.8),
        ]
        r1 = aggregate_evaluations(candidate, evals)
        r2 = aggregate_evaluations(candidate, evals)
        assert r1.aggregate_score == r2.aggregate_score
        assert r1.hard_gate_passed == r2.hard_gate_passed

    def test_participant_order_does_not_matter(self) -> None:
        """Participant order does not affect the aggregate score."""
        candidate = _make_candidate("r003")
        eval_a = _make_evaluation(utility=0.6, reason_codes=["within_group_budget"])
        eval_b = _make_evaluation(utility=0.8, reason_codes=["reasonable_distance"])

        r1 = aggregate_evaluations(candidate, [eval_a, eval_b])
        r2 = aggregate_evaluations(candidate, [eval_b, eval_a])

        assert r1.aggregate_score == r2.aggregate_score
        assert r1.hard_gate_passed == r2.hard_gate_passed


class TestStableSort:
    """Tests for stable sorting in build_ranked_result (P9-16)."""

    def test_passing_candidates_ranked_above_failed(self) -> None:
        """Hard gate passing candidates rank above failed ones."""
        aggs = [
            AggregateResult(
                candidate_key="r001", aggregate_score=0.0,
                public_reason="Failed", rank=0, hard_gate_passed=False,
            ),
            AggregateResult(
                candidate_key="r002", aggregate_score=0.7,
                public_reason="Good", rank=0, hard_gate_passed=True,
            ),
        ]
        result = build_ranked_result(aggs)
        ranked = result["ranked_candidates"]
        assert ranked[0]["candidate_key"] == "r002"
        assert ranked[1]["candidate_key"] == "r001"

    def test_ties_broken_by_candidate_key_ascending(self) -> None:
        """Ties in score are broken by candidate_key ascending."""
        aggs = [
            AggregateResult(
                candidate_key="r003", aggregate_score=0.8,
                public_reason="Good", rank=0, hard_gate_passed=True,
            ),
            AggregateResult(
                candidate_key="r001", aggregate_score=0.8,
                public_reason="Good", rank=0, hard_gate_passed=True,
            ),
            AggregateResult(
                candidate_key="r002", aggregate_score=0.8,
                public_reason="Good", rank=0, hard_gate_passed=True,
            ),
        ]
        result = build_ranked_result(aggs)
        ranked = result["ranked_candidates"]
        assert ranked[0]["candidate_key"] == "r001"
        assert ranked[1]["candidate_key"] == "r002"
        assert ranked[2]["candidate_key"] == "r003"

    def test_higher_score_ranks_first(self) -> None:
        """Higher aggregate score ranks first."""
        aggs = [
            AggregateResult(
                candidate_key="r001", aggregate_score=0.5,
                public_reason="OK", rank=0, hard_gate_passed=True,
            ),
            AggregateResult(
                candidate_key="r002", aggregate_score=0.9,
                public_reason="Great", rank=0, hard_gate_passed=True,
            ),
        ]
        result = build_ranked_result(aggs)
        assert result["selected_candidate_key"] == "r002"
        assert result["ranked_candidates"][0]["rank"] == 1
        assert result["ranked_candidates"][0]["candidate_key"] == "r002"

    def test_no_passing_candidate_selected_is_none(self) -> None:
        """When no candidate passes hard gate, selected is None."""
        aggs = [
            AggregateResult(
                candidate_key="r001", aggregate_score=0.0,
                public_reason="Failed", rank=0, hard_gate_passed=False,
            ),
        ]
        result = build_ranked_result(aggs)
        assert result["selected_candidate_key"] is None


class TestEmptyEdgeCases:
    """Tests for empty and edge cases (P9-16)."""

    def test_empty_evaluations(self) -> None:
        """Empty evaluations list returns zero-scored result."""
        candidate = _make_candidate()
        result = aggregate_evaluations(candidate, [])
        assert result.aggregate_score == 0.0
        assert result.hard_gate_passed is False

    def test_empty_aggregates(self) -> None:
        """Empty aggregates list returns safe empty result."""
        result = build_ranked_result([])
        assert result["selected_candidate_key"] is None
        assert result["ranked_candidates"] == []
        assert "No candidates" in result["public_summary"]

    def test_single_participant(self) -> None:
        """Single participant evaluation works correctly."""
        candidate = _make_candidate("r003")
        evals = [_make_evaluation(utility=0.75)]
        result = aggregate_evaluations(candidate, evals)
        assert result.hard_gate_passed is True
        # No fairness penalty for single participant.
        assert result.aggregate_score >= 0.75

    def test_extreme_weights_uniform(self) -> None:
        """All-equal extreme utilities are handled correctly."""
        candidate = _make_candidate("r003")
        evals = [
            _make_evaluation(utility=1.0),
            _make_evaluation(utility=1.0),
            _make_evaluation(utility=1.0),
        ]
        result = aggregate_evaluations(candidate, evals)
        assert result.aggregate_score <= 1.0
        assert result.hard_gate_passed is True

    def test_extreme_weights_zero(self) -> None:
        """All-zero utilities are handled correctly."""
        candidate = _make_candidate("r003")
        evals = [
            _make_evaluation(utility=0.0),
            _make_evaluation(utility=0.0),
        ]
        result = aggregate_evaluations(candidate, evals)
        assert result.aggregate_score >= 0.0  # May have bonuses
        assert result.hard_gate_passed is True  # Hard pass is separate from utility


class TestPublicReason:
    """Tests for public reason in aggregate results."""

    def test_public_reason_is_string(self) -> None:
        """public_reason is a non-empty string."""
        candidate = _make_candidate()
        evals = [_make_evaluation(reason_codes=["within_group_budget"])]
        result = aggregate_evaluations(candidate, evals)
        assert isinstance(result.public_reason, str)
        assert len(result.public_reason) > 0

    def test_objection_noted_in_reason(self) -> None:
        """When any participant objects, the reason notes it."""
        candidate = _make_candidate()
        evals = [
            _make_evaluation(objection=False),
            _make_evaluation(objection=True),
        ]
        result = aggregate_evaluations(candidate, evals)
        assert "concerns" in result.public_reason.lower() or "concern" in result.public_reason.lower()
