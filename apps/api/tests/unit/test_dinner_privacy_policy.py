"""P9-02 / P9-05: Disclosure policy and minimisation tests.

Tests cover (per P9 guide §4, §7):
- Field disclosure classification is correct.
- ``notes`` is ``never_disclose`` — not in public result, prompt, or message.
- ``dietary_restrictions`` is ``aggregate_only`` — never identifies a member.
- ``budget_min/max`` is ``aggregate_only`` — only group range disclosed.
- Budget range computation (intersection).
- Cuisine / environment aggregation.
- Time slot intersection.
- Distance summary computation.
- Sanitisation functions strip forbidden fields.
"""
from __future__ import annotations

from src.modules.scenes.plugins.dorm_dinner.privacy import (
    FIELD_DISCLOSURE_POLICY,
    NEVER_IN_CAPSULE,
    NEVER_IN_PROMPT,
    NEVER_IN_PUBLIC,
    DisclosureLevel,
    aggregate_cuisine_preferences,
    aggregate_environment_preferences,
    compute_budget_range,
    compute_distance_summary,
    intersect_time_slots,
    sanitise_for_capsule,
    sanitise_for_prompt,
    sanitise_for_public,
)
from src.modules.scenes.plugins.dorm_dinner.schema import (
    Cuisine,
    DinnerPreferenceInput,
    DistancePreference,
    EnvironmentPreference,
    TimeSlot,
)


def _make_prefs(**kwargs) -> DinnerPreferenceInput:
    """Helper to create a preference with sensible defaults."""
    defaults = {"budget_min": 20, "budget_max": 50}
    defaults.update(kwargs)
    return DinnerPreferenceInput(**defaults)


class TestDisclosurePolicy:
    """Tests for field-level disclosure classification."""

    def test_notes_is_never_disclose(self) -> None:
        """notes must be classified as never_disclose."""
        assert FIELD_DISCLOSURE_POLICY["notes"] == DisclosureLevel.NEVER_DISCLOSE

    def test_budget_is_aggregate_only(self) -> None:
        """budget_min and budget_max must be aggregate_only."""
        assert FIELD_DISCLOSURE_POLICY["budget_min"] == DisclosureLevel.AGGREGATE_ONLY
        assert FIELD_DISCLOSURE_POLICY["budget_max"] == DisclosureLevel.AGGREGATE_ONLY

    def test_dietary_is_aggregate_only(self) -> None:
        """dietary_restrictions must be aggregate_only."""
        assert FIELD_DISCLOSURE_POLICY["dietary_restrictions"] == DisclosureLevel.AGGREGATE_ONLY

    def test_cuisine_is_category_disclosable(self) -> None:
        """cuisine_preferences must be category_disclosable."""
        assert FIELD_DISCLOSURE_POLICY["cuisine_preferences"] == DisclosureLevel.CATEGORY_DISCLOSABLE

    def test_environment_is_category_disclosable(self) -> None:
        """environment_preference must be category_disclosable."""
        assert FIELD_DISCLOSURE_POLICY["environment_preference"] == DisclosureLevel.CATEGORY_DISCLOSABLE

    def test_distance_is_aggregate_only(self) -> None:
        """distance_preference must be aggregate_only."""
        assert FIELD_DISCLOSURE_POLICY["distance_preference"] == DisclosureLevel.AGGREGATE_ONLY

    def test_time_is_aggregate_only(self) -> None:
        """available_time must be aggregate_only."""
        assert FIELD_DISCLOSURE_POLICY["available_time"] == DisclosureLevel.AGGREGATE_ONLY

    def test_notes_in_all_never_sets(self) -> None:
        """notes must appear in NEVER_IN_CAPSULE, NEVER_IN_PROMPT, NEVER_IN_PUBLIC."""
        assert "notes" in NEVER_IN_CAPSULE
        assert "notes" in NEVER_IN_PROMPT
        assert "notes" in NEVER_IN_PUBLIC

    def test_dietary_never_in_prompt_or_public(self) -> None:
        """dietary_restrictions must not appear in prompts or public output."""
        assert "dietary_restrictions" in NEVER_IN_PROMPT
        assert "dietary_restrictions" in NEVER_IN_PUBLIC

    def test_budget_never_in_public(self) -> None:
        """budget_min/max must not appear in public output."""
        assert "budget_min" in NEVER_IN_PUBLIC
        assert "budget_max" in NEVER_IN_PUBLIC


class TestBudgetRangeComputation:
    """Tests for compute_budget_range (aggregate_only disclosure)."""

    def test_intersection_range(self) -> None:
        """The group budget is the intersection of all ranges."""
        prefs = [
            _make_prefs(budget_min=20, budget_max=50),
            _make_prefs(budget_min=30, budget_max=80),
        ]
        result = compute_budget_range(prefs)
        assert result["budget_min"] == 30  # max of mins
        assert result["budget_max"] == 50  # min of maxs

    def test_no_overlap_uses_wider_bounds(self) -> None:
        """When ranges don't overlap, wider bounds are used."""
        prefs = [
            _make_prefs(budget_min=10, budget_max=20),
            _make_prefs(budget_min=50, budget_max=80),
        ]
        result = compute_budget_range(prefs)
        # No overlap: min of mins, max of maxs
        assert result["budget_min"] == 10
        assert result["budget_max"] == 80

    def test_empty_preferences_returns_defaults(self) -> None:
        """Empty preferences list returns wide defaults."""
        result = compute_budget_range([])
        assert result["budget_min"] == 0.0
        assert result["budget_max"] == 1000.0

    def test_single_preference(self) -> None:
        """Single preference returns its own range."""
        prefs = [_make_prefs(budget_min=25, budget_max=60)]
        result = compute_budget_range(prefs)
        assert result["budget_min"] == 25
        assert result["budget_max"] == 60


class TestCuisineAggregation:
    """Tests for aggregate_cuisine_preferences (category_disclosable)."""

    def test_counts_per_cuisine(self) -> None:
        """Cuisine preferences are counted per category."""
        prefs = [
            _make_prefs(cuisine_preferences=[Cuisine.SICHUAN, Cuisine.HOTPOT]),
            _make_prefs(cuisine_preferences=[Cuisine.SICHUAN]),
            _make_prefs(cuisine_preferences=[Cuisine.CANTONESE]),
        ]
        counts = aggregate_cuisine_preferences(prefs)
        assert counts["sichuan"] == 2
        assert counts["hotpot"] == 1
        assert counts["cantonese"] == 1

    def test_empty_preferences(self) -> None:
        """Empty preferences produce empty counts."""
        assert aggregate_cuisine_preferences([]) == {}


class TestEnvironmentAggregation:
    """Tests for aggregate_environment_preferences."""

    def test_counts_per_environment(self) -> None:
        """Environment preferences are counted per category."""
        prefs = [
            _make_prefs(environment_preference=EnvironmentPreference.QUIET),
            _make_prefs(environment_preference=EnvironmentPreference.QUIET),
            _make_prefs(environment_preference=EnvironmentPreference.LIVELY),
        ]
        counts = aggregate_environment_preferences(prefs)
        assert counts["quiet"] == 2
        assert counts["lively"] == 1


class TestTimeSlotIntersection:
    """Tests for intersect_time_slots (aggregate_only)."""

    def test_intersection_exists(self) -> None:
        """Returns only time slots where ALL participants are available."""
        prefs = [
            _make_prefs(available_time=[TimeSlot.DINNER, TimeSlot.LUNCH]),
            _make_prefs(available_time=[TimeSlot.DINNER, TimeSlot.EARLY_DINNER]),
        ]
        result = intersect_time_slots(prefs)
        assert result == ["dinner"]

    def test_no_intersection_returns_union(self) -> None:
        """When no intersection exists, returns the union."""
        prefs = [
            _make_prefs(available_time=[TimeSlot.LUNCH]),
            _make_prefs(available_time=[TimeSlot.DINNER]),
        ]
        result = intersect_time_slots(prefs)
        assert set(result) == {"lunch", "dinner"}

    def test_empty_preferences(self) -> None:
        """Empty preferences produce empty list."""
        assert intersect_time_slots([]) == []

    def test_deterministic_order(self) -> None:
        """Result order is deterministic (by TimeSlot enum order)."""
        prefs = [
            _make_prefs(available_time=[TimeSlot.LATE_DINNER, TimeSlot.LUNCH, TimeSlot.DINNER]),
            _make_prefs(available_time=[TimeSlot.LATE_DINNER, TimeSlot.LUNCH, TimeSlot.DINNER]),
        ]
        result = intersect_time_slots(prefs)
        # Should be in enum order: lunch, dinner, late_dinner
        assert result == ["lunch", "dinner", "late_dinner"]


class TestDistanceSummary:
    """Tests for compute_distance_summary (aggregate_only)."""

    def test_most_restrictive_distance(self) -> None:
        """The most restrictive (closest) distance is reported."""
        prefs = [
            _make_prefs(distance_preference=DistancePreference.FAR),
            _make_prefs(distance_preference=DistancePreference.CLOSE),
            _make_prefs(distance_preference=DistancePreference.MODERATE),
        ]
        result = compute_distance_summary(prefs)
        assert result["min_acceptable"] == "close"
        assert result["distribution"]["close"] == 1
        assert result["distribution"]["moderate"] == 1
        assert result["distribution"]["far"] == 1

    def test_empty_preferences(self) -> None:
        """Empty preferences produce defaults."""
        result = compute_distance_summary([])
        assert result["min_acceptable"] == "moderate"
        assert result["distribution"] == {}


class TestSanitisationFunctions:
    """Tests for sanitise_for_public, sanitise_for_prompt, sanitise_for_capsule."""

    def test_sanitise_for_public_strips_notes(self) -> None:
        """sanitise_for_public removes notes."""
        data = {"notes": "secret", "name": "restaurant", "score": 0.8}
        result = sanitise_for_public(data)
        assert "notes" not in result
        assert "name" in result

    def test_sanitise_for_public_strips_budget(self) -> None:
        """sanitise_for_public removes budget_min and budget_max."""
        data = {"budget_min": 20, "budget_max": 50, "name": "restaurant"}
        result = sanitise_for_public(data)
        assert "budget_min" not in result
        assert "budget_max" not in result

    def test_sanitise_for_public_strips_dietary(self) -> None:
        """sanitise_for_public removes dietary_restrictions."""
        data = {"dietary_restrictions": ["vegetarian"], "name": "restaurant"}
        result = sanitise_for_public(data)
        assert "dietary_restrictions" not in result

    def test_sanitise_for_prompt_strips_notes(self) -> None:
        """sanitise_for_prompt removes notes."""
        data = {"notes": "secret", "name": "restaurant"}
        result = sanitise_for_prompt(data)
        assert "notes" not in result

    def test_sanitise_for_prompt_strips_dietary(self) -> None:
        """sanitise_for_prompt removes dietary_restrictions."""
        data = {"dietary_restrictions": ["vegetarian"], "name": "restaurant"}
        result = sanitise_for_prompt(data)
        assert "dietary_restrictions" not in result

    def test_sanitise_for_capsule_strips_notes(self) -> None:
        """sanitise_for_capsule removes notes."""
        data = {"notes": "secret", "hard_constraints": {}}
        result = sanitise_for_capsule(data)
        assert "notes" not in result
        assert "hard_constraints" in result

    def test_sanitise_preserves_safe_fields(self) -> None:
        """Safe fields are preserved through all sanitisation functions."""
        safe_data = {"cuisine": "sichuan", "distance_minutes": 10, "tags": ["good"]}
        assert sanitise_for_public(safe_data) == safe_data
        assert sanitise_for_prompt(safe_data) == safe_data
        assert sanitise_for_capsule(safe_data) == safe_data
