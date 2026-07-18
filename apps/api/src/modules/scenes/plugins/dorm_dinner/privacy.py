"""P9-02: Disclosure policy for the dorm dinner scenario.

Defines the data classification and public disclosure rules for each
field in the preference input. This module is the single source of
truth for what can and cannot appear in capsules, public results,
model prompts, and log entries.

Classification levels:
- ``category_disclosable``: The category/value can be disclosed in
  aggregate form (e.g. "2 participants prefer Sichuan").
- ``aggregate_only``: Only aggregate statistics (min, max, mean,
  intersection) may be disclosed — never individual values that could
  identify a member.
- ``never_disclose``: The field is never disclosed in any form. It
  stays in the encrypted private submission and is purged after
  candidate generation.

Privacy guarantees (P9 guide §4):
- ``notes`` is ``never_disclose``: not in public result, not in model
  prompt, not in messages.
- ``dietary_restrictions`` is ``aggregate_only``: never identifies
  which member has which restriction.
- ``budget_min/max`` is ``aggregate_only``: only the group's budget
  range (intersection) is disclosed.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from .schema import (
    DinnerPreferenceInput,
    DistancePreference,
    TimeSlot,
)

# ---------------------------------------------------------------------------
# Disclosure classification
# ---------------------------------------------------------------------------


class DisclosureLevel(StrEnum):
    """How much of a field can be disclosed publicly."""

    CATEGORY_DISCLOSABLE = "category_disclosable"
    AGGREGATE_ONLY = "aggregate_only"
    NEVER_DISCLOSE = "never_disclose"


# Field-level disclosure policy (frozen — must not change at runtime).
FIELD_DISCLOSURE_POLICY: dict[str, DisclosureLevel] = {
    "budget_min": DisclosureLevel.AGGREGATE_ONLY,
    "budget_max": DisclosureLevel.AGGREGATE_ONLY,
    "cuisine_preferences": DisclosureLevel.CATEGORY_DISCLOSABLE,
    "dietary_restrictions": DisclosureLevel.AGGREGATE_ONLY,
    "distance_preference": DisclosureLevel.AGGREGATE_ONLY,
    "available_time": DisclosureLevel.AGGREGATE_ONLY,
    "environment_preference": DisclosureLevel.CATEGORY_DISCLOSABLE,
    "notes": DisclosureLevel.NEVER_DISCLOSE,
}


# Fields that must NEVER appear in a model prompt.
NEVER_IN_PROMPT: frozenset[str] = frozenset({
    "notes",
    "dietary_restrictions",  # individual restrictions are P4
})

# Fields that must NEVER appear in a capsule (even encrypted).
NEVER_IN_CAPSULE: frozenset[str] = frozenset({
    "notes",
})

# Fields that must NEVER appear in a public result or message.
NEVER_IN_PUBLIC: frozenset[str] = frozenset({
    "notes",
    "dietary_restrictions",
    "budget_min",
    "budget_max",
})


# ---------------------------------------------------------------------------
# Aggregate disclosure helpers
# ---------------------------------------------------------------------------


def compute_budget_range(
    preferences: list[DinnerPreferenceInput],
) -> dict[str, float]:
    """Compute the group's intersected budget range.

    The group's effective budget range is:
    - min = max of all budget_min values (everyone must be comfortable).
    - max = min of all budget_max values (no one exceeds their max).

    This is an aggregate — individual values are not disclosed.

    Returns:
        Dict with ``budget_min`` and ``budget_max`` (the group's
        intersection range). If no preferences, returns wide defaults.
    """
    if not preferences:
        return {"budget_min": 0.0, "budget_max": 1000.0}

    mins = [p.budget_min for p in preferences]
    maxs = [p.budget_max for p in preferences]

    group_min = max(mins)  # Everyone must be comfortable at this minimum.
    group_max = min(maxs)  # No one exceeds their maximum.

    # If the range is inverted (no overlap), use the wider bounds.
    if group_min > group_max:
        group_min = min(mins)
        group_max = max(maxs)

    return {"budget_min": round(group_min, 2), "budget_max": round(group_max, 2)}


def aggregate_cuisine_preferences(
    preferences: list[DinnerPreferenceInput],
) -> dict[str, int]:
    """Aggregate cuisine preferences into a count dict.

    Returns a mapping of cuisine -> count of participants who prefer it.
    This is ``category_disclosable`` — the category can be named, but
    which participant prefers which cuisine is not disclosed.
    """
    counts: dict[str, int] = {}
    for prefs in preferences:
        for cuisine in prefs.cuisine_preferences:
            key = cuisine.value
            counts[key] = counts.get(key, 0) + 1
    return counts


def aggregate_environment_preferences(
    preferences: list[DinnerPreferenceInput],
) -> dict[str, int]:
    """Aggregate environment preferences into a count dict."""
    counts: dict[str, int] = {}
    for prefs in preferences:
        key = prefs.environment_preference.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def intersect_time_slots(
    preferences: list[DinnerPreferenceInput],
) -> list[str]:
    """Compute the intersection of all participants' available time slots.

    Returns the list of time slots where ALL participants are available.
    If no intersection exists, returns the union (so candidates can still
    be generated with a note that not everyone is available at the same time).
    """
    if not preferences:
        return []

    # Start with the first participant's slots.
    intersection: set[str] = {t.value for t in preferences[0].available_time}

    for prefs in preferences[1:]:
        current = {t.value for t in prefs.available_time}
        intersection &= current

    if intersection:
        # Sort by the TimeSlot enum order for deterministic output.
        order = [t.value for t in TimeSlot]
        return sorted(intersection, key=lambda t: order.index(t))

    # No intersection — return union (deterministic order).
    union: set[str] = set()
    for prefs in preferences:
        for t in prefs.available_time:
            union.add(t.value)
    order = [t.value for t in TimeSlot]
    return sorted(union, key=lambda t: order.index(t))


def compute_distance_summary(
    preferences: list[DinnerPreferenceInput],
) -> dict[str, Any]:
    """Compute aggregate distance statistics (no individual values).

    Returns:
        Dict with:
        - ``min_acceptable``: the most restrictive (closest) distance
          preference among participants.
        - ``distribution``: count of each distance preference.
    """
    if not preferences:
        return {"min_acceptable": "moderate", "distribution": {}}

    distribution: dict[str, int] = {}
    for prefs in preferences:
        key = prefs.distance_preference.value
        distribution[key] = distribution.get(key, 0) + 1

    # The most restrictive distance preference is the one closest to
    # the dormitory (smallest acceptable distance).
    distance_order = [
        DistancePreference.CLOSE.value,
        DistancePreference.MODERATE.value,
        DistancePreference.FAR.value,
    ]
    # Find the most restrictive preference (closest) that any participant has.
    min_acceptable = DistancePreference.FAR.value
    for prefs in preferences:
        idx = distance_order.index(prefs.distance_preference.value)
        if idx < distance_order.index(min_acceptable):
            min_acceptable = prefs.distance_preference.value

    return {"min_acceptable": min_acceptable, "distribution": distribution}


# ---------------------------------------------------------------------------
# Sanitisation
# ---------------------------------------------------------------------------


def sanitise_for_public(data: dict[str, Any]) -> dict[str, Any]:
    """Strip any field that must never appear in public output.

    This is a defence-in-depth measure. Even if a bug in the aggregation
    logic accidentally includes a private field, this function ensures
    it is removed before the data reaches the public result or message.
    """
    return {k: v for k, v in data.items() if k not in NEVER_IN_PUBLIC}


def sanitise_for_prompt(data: dict[str, Any]) -> dict[str, Any]:
    """Strip any field that must never appear in a model prompt.

    The model enhancement (P9-11) only receives sanitised, non-sensitive
    structured data. This function enforces that boundary.
    """
    return {k: v for k, v in data.items() if k not in NEVER_IN_PROMPT}


def sanitise_for_capsule(data: dict[str, Any]) -> dict[str, Any]:
    """Strip any field that must never appear in a capsule.

    The capsule is a minimised derivative — it must not contain raw
    free-text (notes) or any directly identifiable data.
    """
    return {k: v for k, v in data.items() if k not in NEVER_IN_CAPSULE}
