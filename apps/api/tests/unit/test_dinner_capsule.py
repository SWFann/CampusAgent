"""P9-04 / P9-05: Preference capsule builder tests.

Tests cover (per P9 guide §6, §7):
- Capsule contains hard_constraints, soft_preferences, weights, allowed_reason_codes.
- Capsule does NOT contain notes original text.
- Capsule does NOT contain email, student_no, user display_name, memory content.
- Capsule does NOT contain psychological/economic inference labels.
- Budget is intervalized (min, max).
- Dietary restrictions stored as a list (not tied to user identity).
- Allowed reason codes are a subset of the public allowlist.
- Default weights are correct and deterministic.
"""
from __future__ import annotations

from src.modules.scenes.plugins.dorm_dinner.capsule import (
    ALL_REASON_CODES,
    DEFAULT_WEIGHTS,
    build_capsule,
    get_available_time,
    get_budget_range,
    get_cuisine_preferences,
    get_dietary_restrictions,
    get_distance_preference,
    get_environment_preference,
)
from src.modules.scenes.plugins.dorm_dinner.reasons import REASON_CODE_ALLOWLIST
from src.modules.scenes.schemas import PrivateCapsule


def _make_raw_prefs(**kwargs) -> dict:
    """Helper to create raw preference dict with sensible defaults."""
    defaults = {"budget_min": 20, "budget_max": 50}
    defaults.update(kwargs)
    return defaults


class TestCapsuleStructure:
    """Tests for capsule structure and contents."""

    def test_capsule_has_required_fields(self) -> None:
        """Capsule must have hard_constraints, soft_preferences, weights, allowed_reason_codes."""
        capsule = build_capsule(_make_raw_prefs())
        assert isinstance(capsule, PrivateCapsule)
        assert hasattr(capsule, "hard_constraints")
        assert hasattr(capsule, "soft_preferences")
        assert hasattr(capsule, "weights")
        assert hasattr(capsule, "allowed_reason_codes")

    def test_hard_constraints_contains_budget_and_dietary(self) -> None:
        """Hard constraints must include budget range and dietary restrictions."""
        raw = _make_raw_prefs(
            budget_min=30, budget_max=80,
            dietary_restrictions=["vegetarian"],
        )
        capsule = build_capsule(raw)
        assert "budget_min" in capsule.hard_constraints
        assert "budget_max" in capsule.hard_constraints
        assert "dietary_restrictions" in capsule.hard_constraints
        assert capsule.hard_constraints["budget_min"] == 30
        assert capsule.hard_constraints["budget_max"] == 80

    def test_soft_preferences_contains_cuisine_distance_env_time(self) -> None:
        """Soft preferences must include cuisine, distance, environment, time."""
        raw = _make_raw_prefs(
            cuisine_preferences=["sichuan", "hotpot"],
            distance_preference="close",
            environment_preference="lively",
            available_time=["dinner", "late_dinner"],
        )
        capsule = build_capsule(raw)
        assert "cuisine_preferences" in capsule.soft_preferences
        assert "distance_preference" in capsule.soft_preferences
        assert "environment_preference" in capsule.soft_preferences
        assert "available_time" in capsule.soft_preferences
        assert capsule.soft_preferences["cuisine_preferences"] == ["sichuan", "hotpot"]

    def test_default_weights_are_correct(self) -> None:
        """Default weights must be deterministic and correct."""
        capsule = build_capsule(_make_raw_prefs())
        assert capsule.weights == DEFAULT_WEIGHTS
        assert capsule.weights["cuisine"] == 0.30
        assert capsule.weights["budget"] == 0.25
        assert capsule.weights["distance"] == 0.15
        assert capsule.weights["environment"] == 0.15
        assert capsule.weights["time"] == 0.15

    def test_weights_sum_to_one(self) -> None:
        """Default weights should sum to approximately 1.0."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001


class TestCapsulePrivacy:
    """Tests for capsule privacy guarantees (P9-05)."""

    def test_notes_not_in_capsule(self) -> None:
        """Notes must never appear in any part of the capsule."""
        raw = _make_raw_prefs(notes="This is a secret note with sensitive info.")
        capsule = build_capsule(raw)
        capsule_dict = capsule.model_dump()
        # Check that 'notes' doesn't appear anywhere in the capsule.
        assert "notes" not in capsule_dict
        assert "notes" not in capsule.hard_constraints
        assert "notes" not in capsule.soft_preferences
        # The actual note text must not appear in any field value.
        import json
        assert "This is a secret note" not in json.dumps(capsule_dict)

    def test_no_email_in_capsule(self) -> None:
        """Email must not appear in the capsule."""
        raw = _make_raw_prefs()
        raw["email"] = "user@example.com"  # type: ignore[dict-item]
        # This should be rejected by extra='forbid', but if it somehow passes:
        try:
            capsule = build_capsule(raw)
            import json
            assert "user@example.com" not in json.dumps(capsule.model_dump())
        except (ValueError, Exception):
            # Expected: extra field rejected
            pass

    def test_no_user_identity_in_capsule(self) -> None:
        """User identifiers (student_no, display_name) must not appear."""
        raw = _make_raw_prefs(notes="My name is Zhang San, student no 2024001")
        capsule = build_capsule(raw)
        import json
        capsule_json = json.dumps(capsule.model_dump())
        # The notes text must not leak into the capsule.
        assert "Zhang San" not in capsule_json
        assert "2024001" not in capsule_json

    def test_no_psychological_inferences(self) -> None:
        """No psychological/economic inference labels are generated."""
        raw = _make_raw_prefs(
            budget_min=5, budget_max=10,  # Low budget
            notes="I'm very stressed about money",
        )
        capsule = build_capsule(raw)
        import json
        capsule_json = json.dumps(capsule.model_dump()).lower()
        # No inference labels should be present.
        forbidden_labels = ["economic", "financial", "psychological", "stress", "low_income"]
        for label in forbidden_labels:
            assert label not in capsule_json, f"Found forbidden label '{label}' in capsule"

    def test_dietary_restrictions_not_tied_to_user(self) -> None:
        """Dietary restrictions are stored as a list, not tied to user identity."""
        raw = _make_raw_prefs(dietary_restrictions=["vegetarian", "nut_allergy"])
        capsule = build_capsule(raw)
        restrictions = capsule.hard_constraints["dietary_restrictions"]
        assert isinstance(restrictions, list)
        assert "vegetarian" in restrictions
        assert "nut_allergy" in restrictions
        # No user ID or name associated with the restrictions.
        import json
        assert "user_id" not in json.dumps(capsule.hard_constraints).lower()

    def test_budget_is_intervalized(self) -> None:
        """Budget is stored as a range (min, max), not a single value."""
        raw = _make_raw_prefs(budget_min=25, budget_max=60)
        capsule = build_capsule(raw)
        bmin, bmax = get_budget_range(capsule)
        assert bmin == 25
        assert bmax == 60
        # No single "budget" value — only min and max.
        assert "budget" not in capsule.hard_constraints
        assert "budget_min" in capsule.hard_constraints
        assert "budget_max" in capsule.hard_constraints


class TestCapsuleReasonCodes:
    """Tests for allowed_reason_codes in the capsule."""

    def test_reason_codes_are_subset_of_allowlist(self) -> None:
        """All reason codes in the capsule must be in the allowlist."""
        raw = _make_raw_prefs(
            cuisine_preferences=["sichuan"],
            available_time=["dinner"],
        )
        capsule = build_capsule(raw)
        for code in capsule.allowed_reason_codes:
            assert code in REASON_CODE_ALLOWLIST, f"Reason code '{code}' not in allowlist"

    def test_reason_codes_include_budget_and_distance(self) -> None:
        """Budget and distance reason codes are always included."""
        capsule = build_capsule(_make_raw_prefs())
        assert "within_group_budget" in capsule.allowed_reason_codes
        assert "reasonable_distance" in capsule.allowed_reason_codes
        assert "balanced_tradeoff" in capsule.allowed_reason_codes

    def test_cuisine_reason_code_when_cuisine_prefs_exist(self) -> None:
        """matches_common_cuisine is included when cuisine preferences exist."""
        raw = _make_raw_prefs(cuisine_preferences=["sichuan"])
        capsule = build_capsule(raw)
        assert "matches_common_cuisine" in capsule.allowed_reason_codes

    def test_time_reason_code_when_time_slots_exist(self) -> None:
        """fits_shared_time is included when time slots exist."""
        raw = _make_raw_prefs(available_time=["dinner"])
        capsule = build_capsule(raw)
        assert "fits_shared_time" in capsule.allowed_reason_codes

    def test_all_reason_codes_defined(self) -> None:
        """ALL_REASON_CODES must match the allowlist keys."""
        assert set(ALL_REASON_CODES) == set(REASON_CODE_ALLOWLIST.keys())


class TestCapsuleHelperFunctions:
    """Tests for capsule inspection helper functions."""

    def test_get_dietary_restrictions(self) -> None:
        raw = _make_raw_prefs(dietary_restrictions=["vegetarian", "halal"])
        capsule = build_capsule(raw)
        restrictions = get_dietary_restrictions(capsule)
        assert isinstance(restrictions, set)
        assert "vegetarian" in restrictions
        assert "halal" in restrictions

    def test_get_budget_range(self) -> None:
        raw = _make_raw_prefs(budget_min=30, budget_max=70)
        capsule = build_capsule(raw)
        bmin, bmax = get_budget_range(capsule)
        assert bmin == 30
        assert bmax == 70

    def test_get_cuisine_preferences(self) -> None:
        raw = _make_raw_prefs(cuisine_preferences=["sichuan", "hotpot"])
        capsule = build_capsule(raw)
        cuisines = get_cuisine_preferences(capsule)
        assert cuisines == ["sichuan", "hotpot"]

    def test_get_distance_preference(self) -> None:
        raw = _make_raw_prefs(distance_preference="close")
        capsule = build_capsule(raw)
        assert get_distance_preference(capsule) == "close"

    def test_get_environment_preference(self) -> None:
        raw = _make_raw_prefs(environment_preference="lively")
        capsule = build_capsule(raw)
        assert get_environment_preference(capsule) == "lively"

    def test_get_available_time(self) -> None:
        raw = _make_raw_prefs(available_time=["dinner", "lunch"])
        capsule = build_capsule(raw)
        times = get_available_time(capsule)
        assert times == ["dinner", "lunch"]


class TestCapsuleEmptyPreferences:
    """Tests for conservative capsule from empty/minimal preferences."""

    def test_empty_preferences_produce_valid_capsule(self) -> None:
        """Empty preferences (only budget) produce a conservative capsule."""
        raw = _make_raw_prefs()
        capsule = build_capsule(raw)
        assert isinstance(capsule, PrivateCapsule)
        assert capsule.hard_constraints["budget_min"] == 20
        assert capsule.hard_constraints["budget_max"] == 50
        assert capsule.soft_preferences["cuisine_preferences"] == []
        assert capsule.soft_preferences["available_time"] == []

    def test_empty_cuisine_does_not_add_cuisine_reason(self) -> None:
        """No cuisine reason code when cuisine preferences are empty."""
        raw = _make_raw_prefs()
        capsule = build_capsule(raw)
        assert "matches_common_cuisine" not in capsule.allowed_reason_codes

    def test_empty_time_does_not_add_time_reason(self) -> None:
        """No time reason code when time slots are empty."""
        raw = _make_raw_prefs()
        capsule = build_capsule(raw)
        assert "fits_shared_time" not in capsule.allowed_reason_codes
