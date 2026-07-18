"""P9-04 / P9-05: Preference capsule builder for the dorm dinner scenario.

The capsule is a de-identified, minimised derivative of the raw
preferences. It contains only the information needed for candidate
generation and private evaluation — never raw free-text, identifiable
data, or psychological/economic inferences.

Capsule contents:
- hard_constraints: dietary_restrictions (as a set), budget range.
- soft_preferences: cuisine preferences (ordered), distance, environment, time.
- weights: relative importance of each preference dimension.
- allowed_reason_codes: subset of the public reason allowlist relevant
  to this participant's preferences.

Capsule does NOT contain:
- notes original text (never_disclose).
- email, student_no, user display_name.
- memory content.
- psychological/economic inference tags.

Minimisation guarantees (P9-05):
- Free-text (notes) never leaves the private submission.
- Budget is intervalized (min, max) — individual values are not in the
  capsule.
- Dietary restrictions are stored as a set — they do not identify the
  member.
- No psychological/economic inference labels are generated.
"""
from __future__ import annotations

from typing import Any

from ...schemas import PrivateCapsule
from .privacy import sanitise_for_capsule
from .schema import (
    DinnerPreferenceInput,
)

# ---------------------------------------------------------------------------
# Default weights for preference dimensions (deterministic, fair)
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "cuisine": 0.30,
    "budget": 0.25,
    "distance": 0.15,
    "environment": 0.15,
    "time": 0.15,
}

# All allowed reason codes for this scenario.
ALL_REASON_CODES: list[str] = [
    "matches_common_cuisine",
    "within_group_budget",
    "reasonable_distance",
    "fits_shared_time",
    "balanced_tradeoff",
]


# ---------------------------------------------------------------------------
# Capsule builder
# ---------------------------------------------------------------------------


def build_capsule(raw_preferences: dict[str, Any]) -> PrivateCapsule:
    """Build a de-identified capsule from raw preferences.

    This function is called by the plugin's ``build_private_capsule``
    method. It validates the input, extracts hard constraints and soft
    preferences, and returns a PrivateCapsule.

    Privacy:
    - The ``notes`` field is never included in any part of the capsule.
    - Dietary restrictions are stored as a list of strings (not tied to
      a user identity).
    - Budget is stored as a range (min, max), not as a single value.
    - No inference labels are generated.

    Args:
        raw_preferences: The user's raw preference dict.

    Returns:
        PrivateCapsule with hard_constraints, soft_preferences, weights,
        and allowed_reason_codes.

    Raises:
        ValueError: If the raw preferences fail validation.
    """
    # Validate the raw input.
    prefs = DinnerPreferenceInput.model_validate(raw_preferences)

    # --- Hard constraints ---
    # These MUST be satisfied — a candidate that violates any hard
    # constraint gets hard_pass=False in evaluation.
    hard_constraints: dict[str, Any] = {
        "dietary_restrictions": [r.value for r in prefs.dietary_restrictions],
        "budget_min": prefs.budget_min,
        "budget_max": prefs.budget_max,
    }

    # --- Soft preferences ---
    # These are preferences that contribute to utility scoring but
    # are not strict requirements.
    soft_preferences: dict[str, Any] = {
        "cuisine_preferences": [c.value for c in prefs.cuisine_preferences],
        "distance_preference": prefs.distance_preference.value,
        "environment_preference": prefs.environment_preference.value,
        "available_time": [t.value for t in prefs.available_time],
    }

    # --- Weights ---
    # Use default weights (deterministic, no personalisation).
    weights: dict[str, float] = dict(DEFAULT_WEIGHTS)

    # --- Allowed reason codes ---
    # Only include reason codes relevant to this participant's preferences.
    allowed_reason_codes: list[str] = []
    if prefs.cuisine_preferences:
        allowed_reason_codes.append("matches_common_cuisine")
    # Budget is always relevant.
    allowed_reason_codes.append("within_group_budget")
    # Distance is relevant if the participant has a preference (always does).
    allowed_reason_codes.append("reasonable_distance")
    if prefs.available_time:
        allowed_reason_codes.append("fits_shared_time")
    # Balanced tradeoff is always potentially applicable.
    allowed_reason_codes.append("balanced_tradeoff")

    # Defence-in-depth: ensure no forbidden fields leaked into the capsule.
    hard_constraints = sanitise_for_capsule(hard_constraints)
    soft_preferences = sanitise_for_capsule(soft_preferences)

    return PrivateCapsule(
        hard_constraints=hard_constraints,
        soft_preferences=soft_preferences,
        weights=weights,
        allowed_reason_codes=allowed_reason_codes,
    )


# ---------------------------------------------------------------------------
# Capsule inspection helpers (for testing and debugging)
# ---------------------------------------------------------------------------


def get_hard_constraints(capsule: PrivateCapsule) -> dict[str, Any]:
    """Extract hard constraints from a capsule."""
    return dict(capsule.hard_constraints)


def get_soft_preferences(capsule: PrivateCapsule) -> dict[str, Any]:
    """Extract soft preferences from a capsule."""
    return dict(capsule.soft_preferences)


def get_dietary_restrictions(capsule: PrivateCapsule) -> set[str]:
    """Extract dietary restrictions as a set of strings."""
    restrictions = capsule.hard_constraints.get("dietary_restrictions", [])
    return set(restrictions) if restrictions else set()


def get_budget_range(capsule: PrivateCapsule) -> tuple[float, float]:
    """Extract the budget range (min, max) from a capsule."""
    bmin = capsule.hard_constraints.get("budget_min", 0.0)
    bmax = capsule.hard_constraints.get("budget_max", 1000.0)
    return float(bmin), float(bmax)


def get_cuisine_preferences(capsule: PrivateCapsule) -> list[str]:
    """Extract cuisine preferences as an ordered list of strings."""
    cuisines = capsule.soft_preferences.get("cuisine_preferences", [])
    return list(cuisines) if cuisines else []


def get_distance_preference(capsule: PrivateCapsule) -> str:
    """Extract the distance preference from a capsule."""
    return str(capsule.soft_preferences.get("distance_preference", "moderate"))


def get_environment_preference(capsule: PrivateCapsule) -> str:
    """Extract the environment preference from a capsule."""
    return str(capsule.soft_preferences.get("environment_preference", "moderate"))


def get_available_time(capsule: PrivateCapsule) -> list[str]:
    """Extract available time slots from a capsule."""
    times = capsule.soft_preferences.get("available_time", [])
    return list(times) if times else []
