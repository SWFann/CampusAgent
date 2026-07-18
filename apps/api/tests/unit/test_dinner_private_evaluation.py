"""P9-08: Private candidate evaluation tests.

Tests cover (per P9 guide §10):
- Each participant evaluates each candidate privately.
- hard_pass check: budget overlap, dietary accommodation.
- utility score is in [0, 1].
- objection flag is set for strong mismatches.
- reason_codes are allowlisted only.
- The evaluation is never exposed publicly (it's an internal type).
"""
from __future__ import annotations

from src.modules.scenes.plugins.dorm_dinner.algorithm import evaluate_candidate
from src.modules.scenes.plugins.dorm_dinner.capsule import build_capsule
from src.modules.scenes.plugins.dorm_dinner.reasons import REASON_CODE_ALLOWLIST
from src.modules.scenes.plugins.dorm_dinner.restaurants import get_restaurant_by_id
from src.modules.scenes.schemas import CandidateInput, EvaluationResult, PrivateCapsule


def _make_capsule(**kwargs) -> PrivateCapsule:
    raw = {"budget_min": 20, "budget_max": 50}
    raw.update(kwargs)
    return build_capsule(raw)


def _make_candidate(restaurant_id: str = "r001") -> CandidateInput:
    """Create a CandidateInput from a real restaurant."""
    r = get_restaurant_by_id(restaurant_id)
    assert r is not None
    return CandidateInput(
        candidate_key=r.id,
        display_name=r.name,
        public_metadata=r.to_candidate_metadata(),
    )


class TestEvaluationResultStructure:
    """Tests for EvaluationResult structure."""

    def test_returns_evaluation_result(self) -> None:
        """evaluate_candidate returns an EvaluationResult."""
        capsule = _make_capsule()
        candidate = _make_candidate()
        result = evaluate_candidate(candidate, capsule)
        assert isinstance(result, EvaluationResult)

    def test_has_required_fields(self) -> None:
        """EvaluationResult has all required fields."""
        capsule = _make_capsule()
        candidate = _make_candidate()
        result = evaluate_candidate(candidate, capsule)
        assert hasattr(result, "candidate_key")
        assert hasattr(result, "hard_pass")
        assert hasattr(result, "utility")
        assert hasattr(result, "objection")
        assert hasattr(result, "reason_codes")

    def test_candidate_key_matches(self) -> None:
        """candidate_key in result matches the candidate."""
        capsule = _make_capsule()
        candidate = _make_candidate("r002")
        result = evaluate_candidate(candidate, capsule)
        assert result.candidate_key == "r002"


class TestHardConstraints:
    """Tests for hard constraint checking."""

    def test_budget_overlap_passes(self) -> None:
        """Budget overlap means hard_pass=True."""
        # r003 (北方饺子馆): price 15-35
        capsule = _make_capsule(budget_min=20, budget_max=50)
        candidate = _make_candidate("r003")
        result = evaluate_candidate(candidate, capsule)
        assert result.hard_pass is True

    def test_budget_no_overlap_fails(self) -> None:
        """No budget overlap means hard_pass=False."""
        # r009 (西餐小馆): price 55-130
        capsule = _make_capsule(budget_min=10, budget_max=15)
        candidate = _make_candidate("r009")
        result = evaluate_candidate(candidate, capsule)
        # r009 price_min=55 > capsule budget_max=15
        assert result.hard_pass is False

    def test_dietary_accommodated_passes(self) -> None:
        """Dietary restrictions that the restaurant can accommodate pass."""
        # r008 (绿野蔬食) has vegetarian, vegan, nut_allergy, lactose_intolerant
        capsule = _make_capsule(dietary_restrictions=["vegetarian"])
        candidate = _make_candidate("r008")
        result = evaluate_candidate(candidate, capsule)
        assert result.hard_pass is True

    def test_dietary_not_accommodated_fails(self) -> None:
        """Dietary restrictions the restaurant can't accommodate fail."""
        # r001 (蜀香居) only has NONE — can't accommodate vegetarian
        capsule = _make_capsule(dietary_restrictions=["vegan"])
        candidate = _make_candidate("r001")
        result = evaluate_candidate(candidate, capsule)
        assert result.hard_pass is False

    def test_none_restriction_always_passes(self) -> None:
        """NONE dietary restriction always passes hard constraint."""
        capsule = _make_capsule()  # defaults to [NONE]
        candidate = _make_candidate("r001")
        result = evaluate_candidate(candidate, capsule)
        # Budget should overlap (r001: 25-60, capsule: 20-50)
        assert result.hard_pass is True


class TestUtilityScore:
    """Tests for utility scoring."""

    def test_utility_in_range(self) -> None:
        """Utility score must be in [0, 1]."""
        capsule = _make_capsule()
        candidate = _make_candidate()
        result = evaluate_candidate(candidate, capsule)
        assert 0.0 <= result.utility <= 1.0

    def test_cuisine_match_increases_utility(self) -> None:
        """Cuisine match increases utility score."""
        # r001 is Sichuan
        capsule_match = _make_capsule(cuisine_preferences=["sichuan"])
        capsule_no_match = _make_capsule(cuisine_preferences=["japanese"])
        candidate = _make_candidate("r001")
        result_match = evaluate_candidate(candidate, capsule_match)
        result_no_match = evaluate_candidate(candidate, capsule_no_match)
        assert result_match.utility > result_no_match.utility

    def test_budget_fit_increases_utility(self) -> None:
        """Budget fit increases utility score."""
        # r003 (北方饺子馆): price 15-35
        capsule_fit = _make_capsule(budget_min=15, budget_max=35)
        capsule_overshoot = _make_capsule(budget_min=5, budget_max=10)
        candidate = _make_candidate("r003")
        result_fit = evaluate_candidate(candidate, capsule_fit)
        result_overshoot = evaluate_candidate(candidate, capsule_overshoot)
        assert result_fit.utility > result_overshoot.utility

    def test_distance_match_increases_utility(self) -> None:
        """Distance within preference gives high utility score."""
        # r010 (速食工坊): distance 3 min — very close
        capsule_close = _make_capsule(distance_preference="close")
        candidate = _make_candidate("r010")
        result_close = evaluate_candidate(candidate, capsule_close)
        # A close restaurant should give a high distance score regardless
        # of whether the preference is close or far.
        assert result_close.utility >= 0.7

    def test_environment_match_increases_utility(self) -> None:
        """Environment match increases utility score."""
        # r001 (蜀香居): noise_level=lively
        capsule_match = _make_capsule(environment_preference="lively")
        capsule_no_match = _make_capsule(environment_preference="quiet")
        candidate = _make_candidate("r001")
        result_match = evaluate_candidate(candidate, capsule_match)
        result_no_match = evaluate_candidate(candidate, capsule_no_match)
        assert result_match.utility > result_no_match.utility


class TestObjection:
    """Tests for the objection flag."""

    def test_no_objection_for_good_match(self) -> None:
        """No objection when the candidate is a good match."""
        capsule = _make_capsule(
            budget_min=20, budget_max=60,
            cuisine_preferences=["sichuan"],
        )
        candidate = _make_candidate("r001")  # 蜀香居, Sichuan, 25-60
        result = evaluate_candidate(candidate, capsule)
        assert result.objection is False

    def test_objection_for_cuisine_mismatch(self) -> None:
        """Objection when cuisine is completely outside preferences."""
        capsule = _make_capsule(
            budget_min=20, budget_max=50,
            cuisine_preferences=["sichuan", "hotpot"],
        )
        # r006 (樱花日料) is Japanese, not in preferences
        candidate = _make_candidate("r006")
        result = evaluate_candidate(candidate, capsule)
        # Price range 45-120, capsule 20-50 — overlap exists
        # But cuisine not in preferences
        assert result.objection is True

    def test_objection_for_extreme_budget_overshoot(self) -> None:
        """Objection when restaurant is way over budget."""
        # r009 (西餐小馆): price 55-130
        capsule = _make_capsule(
            budget_min=10, budget_max=20,
            cuisine_preferences=["western"],
        )
        candidate = _make_candidate("r009")
        result = evaluate_candidate(candidate, capsule)
        # price_min=55 > cap_budget_max*1.5 = 30
        assert result.objection is True


class TestReasonCodes:
    """Tests for reason codes in evaluation results."""

    def test_reason_codes_are_allowlisted(self) -> None:
        """All reason codes must be in the allowlist."""
        capsule = _make_capsule(
            budget_min=20, budget_max=50,
            cuisine_preferences=["sichuan"],
            available_time=["dinner"],
        )
        candidate = _make_candidate("r001")
        result = evaluate_candidate(candidate, capsule)
        for code in result.reason_codes:
            assert code in REASON_CODE_ALLOWLIST

    def test_cuisine_reason_code_when_matched(self) -> None:
        """matches_common_cuisine is set when cuisine matches."""
        capsule = _make_capsule(cuisine_preferences=["sichuan"])
        candidate = _make_candidate("r001")  # Sichuan
        result = evaluate_candidate(candidate, capsule)
        assert "matches_common_cuisine" in result.reason_codes

    def test_budget_reason_code_when_in_range(self) -> None:
        """within_group_budget is set when budget overlaps."""
        capsule = _make_capsule(budget_min=20, budget_max=60)
        candidate = _make_candidate("r001")  # 25-60
        result = evaluate_candidate(candidate, capsule)
        assert "within_group_budget" in result.reason_codes

    def test_distance_reason_code_when_within_preference(self) -> None:
        """reasonable_distance is set when distance is within preference."""
        capsule = _make_capsule(distance_preference="close")  # <= 10 min
        candidate = _make_candidate("r010")  # distance 3 min
        result = evaluate_candidate(candidate, capsule)
        assert "reasonable_distance" in result.reason_codes

    def test_time_reason_code_when_available(self) -> None:
        """fits_shared_time is set when time slots overlap."""
        capsule = _make_capsule(available_time=["dinner"])
        candidate = _make_candidate("r001")  # open at dinner
        result = evaluate_candidate(candidate, capsule)
        assert "fits_shared_time" in result.reason_codes


class TestEvaluationDeterminism:
    """Tests for deterministic evaluation."""

    def test_same_input_same_output(self) -> None:
        """Same input always produces the same evaluation."""
        capsule = _make_capsule(budget_min=20, budget_max=50)
        candidate = _make_candidate("r001")
        r1 = evaluate_candidate(candidate, capsule)
        r2 = evaluate_candidate(candidate, capsule)
        assert r1.utility == r2.utility
        assert r1.hard_pass == r2.hard_pass
        assert r1.reason_codes == r2.reason_codes
        assert r1.objection == r2.objection
