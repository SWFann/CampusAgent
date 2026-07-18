"""P9-07 / P9-08 / P9-09: Core algorithm for the dorm dinner scenario.

This module implements three phases:
1. Candidate generation (P9-07): Filter restaurants using only public
   context and de-identified capsules — never raw private input.
2. Private evaluation (P9-08): Each participant privately evaluates
   each candidate against their own capsule.
3. Deterministic aggregation (P9-09): Aggregate private evaluations
   into a public-safe ranked result using a deterministic algorithm.

Determinism guarantees:
- Same inputs always produce the same output.
- Participant order does not affect the result.
- Ties are broken by deterministic restaurant ID.
- The algorithm works without any model calls — the model is only
  used for optional enhancement of the final public text (P9-11).
"""
from __future__ import annotations

import contextlib
import math
from typing import Any

from ...schemas import (
    AggregateResult,
    CandidateInput,
    EvaluationResult,
    PrivateCapsule,
)
from .capsule import (
    get_available_time,
    get_budget_range,
    get_cuisine_preferences,
    get_dietary_restrictions,
    get_distance_preference,
    get_environment_preference,
)
from .reasons import validate_reason_codes
from .restaurants import (
    Restaurant,
    get_all_restaurants,
)
from .schema import (
    DietaryRestriction,
    DistancePreference,
    TimeSlot,
)

# Minimum number of candidates to return (per P9-07).
MIN_CANDIDATES = 3


# ---------------------------------------------------------------------------
# P9-07: Candidate Generation
# ---------------------------------------------------------------------------


def generate_candidates(
    capsules: list[PrivateCapsule],
    public_context: dict[str, Any] | None,
) -> list[CandidateInput]:
    """Generate public candidates from all participants' capsules.

    Uses only the de-identified capsules and public context — never
    raw private input. The algorithm:

    1. Compute group budget range (intersection).
    2. Compute group dietary restrictions (union).
    3. Compute shared time slots (intersection).
    4. Compute most restrictive distance preference.
    5. Filter restaurants by all hard constraints.
    6. If fewer than MIN_CANDIDATES pass, relax constraints in order:
       distance, budget, time.
    7. Return at least MIN_CANDIDATES candidates (or empty if none pass).

    Returns:
        List of CandidateInput objects with public restaurant metadata.
    """
    if not capsules:
        return []

    # Extract aggregate constraints from capsules.
    all_dietary: set[str] = set()
    budget_mins: list[float] = []
    budget_maxs: list[float] = []
    all_times: set[str] = set()
    distance_preferences: list[str] = []

    for capsule in capsules:
        all_dietary |= get_dietary_restrictions(capsule)
        bmin, bmax = get_budget_range(capsule)
        budget_mins.append(bmin)
        budget_maxs.append(bmax)
        times = get_available_time(capsule)
        all_times |= set(times)
        distance_preferences.append(get_distance_preference(capsule))

    # Compute group budget range (intersection).
    group_budget_min = max(budget_mins) if budget_mins else 0.0
    group_budget_max = min(budget_maxs) if budget_maxs else 1000.0
    if group_budget_min > group_budget_max:
        # No overlap — use wider range.
        group_budget_min = min(budget_mins) if budget_mins else 0.0
        group_budget_max = max(budget_maxs) if budget_maxs else 1000.0

    # Compute most restrictive distance (closest acceptable).
    distance_order = [
        DistancePreference.CLOSE.value,
        DistancePreference.MODERATE.value,
        DistancePreference.FAR.value,
    ]
    min_distance_idx = min(
        (distance_order.index(d) for d in distance_preferences),
        default=1,
    )
    max_minutes = {0: 10, 1: 20, 2: 30}[min_distance_idx]

    # Convert dietary strings to enums.
    dietary_enums: set[DietaryRestriction] = set()
    for d in all_dietary:
        with contextlib.suppress(ValueError):
            dietary_enums.add(DietaryRestriction(d))

    # Convert time strings to enums.
    time_enums: set[TimeSlot] = set()
    for t in all_times:
        with contextlib.suppress(ValueError):
            time_enums.add(TimeSlot(t))

    # --- Filter restaurants (strict) ---
    candidates = _filter_restaurants(
        group_budget_min,
        group_budget_max,
        dietary_enums,
        time_enums,
        max_minutes,
    )

    # --- Relaxation: if fewer than MIN_CANDIDATES, relax constraints ---
    if len(candidates) < MIN_CANDIDATES:
        # Relax distance: allow up to 30 minutes.
        candidates = _filter_restaurants(
            group_budget_min,
            group_budget_max,
            dietary_enums,
            time_enums,
            max_minutes=30,
        )

    if len(candidates) < MIN_CANDIDATES:
        # Relax budget: use wider range.
        relaxed_min = min(budget_mins) if budget_mins else 0.0
        relaxed_max = max(budget_maxs) if budget_maxs else 1000.0
        candidates = _filter_restaurants(
            relaxed_min,
            relaxed_max,
            dietary_enums,
            time_enums,
            max_minutes=30,
        )

    if len(candidates) < MIN_CANDIDATES:
        # Relax time: accept any restaurant (ignore time constraint).
        candidates = _filter_restaurants(
            group_budget_min if group_budget_min <= group_budget_max else 0.0,
            group_budget_max if group_budget_min <= group_budget_max else 1000.0,
            dietary_enums,
            set(),
            max_minutes=30,
        )

    # Sort by deterministic ID for stable ordering.
    candidates.sort(key=lambda r: r.id)

    # Convert to CandidateInput list.
    return [
        CandidateInput(
            candidate_key=r.id,
            display_name=r.name,
            public_metadata=r.to_candidate_metadata(),
        )
        for r in candidates
    ]


def _filter_restaurants(
    budget_min: float,
    budget_max: float,
    dietary: set[DietaryRestriction],
    time_slots: set[TimeSlot],
    max_minutes: int,
) -> list[Restaurant]:
    """Filter restaurants by all hard constraints."""
    result = get_all_restaurants()

    # Budget filter.
    result = [r for r in result if r.price_min <= budget_max and r.price_max >= budget_min]

    # Dietary filter.
    if dietary and dietary != {DietaryRestriction.NONE}:
        result = [r for r in result if dietary.issubset(set(r.dietary_options))]

    # Time filter.
    if time_slots:
        result = [r for r in result if any(t in r.time_slots for t in time_slots)]

    # Distance filter.
    result = [r for r in result if r.distance_minutes <= max_minutes]

    return result


# ---------------------------------------------------------------------------
# P9-08: Private Candidate Evaluation
# ---------------------------------------------------------------------------


def evaluate_candidate(
    candidate: CandidateInput,
    capsule: PrivateCapsule,
) -> EvaluationResult:
    """Privately evaluate a candidate against one participant's capsule.

    The evaluation is never exposed publicly — it feeds into
    ``aggregate_results``.

    Returns:
        EvaluationResult with:
        - hard_pass: Whether the candidate satisfies all hard constraints.
        - utility: A float in [0, 1] representing how well the candidate
          matches the participant's soft preferences.
        - objection: Whether the participant objects to this candidate.
        - reason_codes: Allowlisted reason codes that apply.

    Hard constraints (must be satisfied):
    - Budget range: candidate's price range overlaps with the participant's.
    - Dietary restrictions: candidate accommodates all restrictions.

    Soft preferences (contribute to utility):
    - Cuisine match (weight: 0.30)
    - Budget fit (weight: 0.25)
    - Distance match (weight: 0.15)
    - Environment match (weight: 0.15)
    - Time match (weight: 0.15)
    """
    metadata = candidate.public_metadata or {}

    # Extract capsule data.
    dietary_restrictions = get_dietary_restrictions(capsule)
    cap_budget_min, cap_budget_max = get_budget_range(capsule)
    cuisine_prefs = get_cuisine_preferences(capsule)
    distance_pref = get_distance_preference(capsule)
    env_pref = get_environment_preference(capsule)
    available_times = get_available_time(capsule)
    weights = capsule.weights if capsule.weights else {}

    # --- Hard constraint checks ---
    hard_pass = True

    # Budget: candidate's price range must overlap with capsule's range.
    rest_price_min = float(metadata.get("price_min", 0))
    rest_price_max = float(metadata.get("price_max", 0))
    if rest_price_min > cap_budget_max or rest_price_max < cap_budget_min:
        hard_pass = False

    # Dietary: candidate must accommodate all restrictions.
    if dietary_restrictions and dietary_restrictions != {"none"}:
        rest_dietary = set(metadata.get("dietary_options", []))
        if not dietary_restrictions.issubset(rest_dietary):
            hard_pass = False

    # --- Soft preference scoring ---
    w_cuisine = weights.get("cuisine", 0.30)
    w_budget = weights.get("budget", 0.25)
    w_distance = weights.get("distance", 0.15)
    w_env = weights.get("environment", 0.15)
    w_time = weights.get("time", 0.15)

    # Cuisine score: 1.0 if the restaurant's cuisine is in the top
    # preference, decreasing for lower-ranked preferences.
    cuisine_score = 0.0
    rest_cuisine = metadata.get("cuisine", "")
    if rest_cuisine in cuisine_prefs:
        # Higher score for higher-ranked preferences.
        rank = cuisine_prefs.index(rest_cuisine)
        cuisine_score = 1.0 / (rank + 1)
    elif not cuisine_prefs:
        # No preference — neutral score.
        cuisine_score = 0.5

    # Budget score: 1.0 if the restaurant's mid-price is within the
    # participant's budget range, decreasing as it moves outside.
    rest_mid_price = (rest_price_min + rest_price_max) / 2
    if cap_budget_min <= rest_mid_price <= cap_budget_max:
        budget_score = 1.0
    elif rest_mid_price < cap_budget_min:
        # Cheaper than minimum — still acceptable, slightly lower score.
        budget_score = 0.8
    else:
        # More expensive than maximum — penalise.
        overshoot = rest_mid_price - cap_budget_max
        budget_score = max(0.0, 1.0 - overshoot / max(cap_budget_max, 1.0))

    # Distance score: 1.0 if within preference, decreasing for farther.
    rest_distance = int(metadata.get("distance_minutes", 30))
    distance_limits = {"close": 10, "moderate": 20, "far": 30}
    limit = distance_limits.get(distance_pref, 20)
    if rest_distance <= limit:
        distance_score = 1.0 - (rest_distance / max(limit, 1)) * 0.3  # 0.7 to 1.0
    else:
        # Beyond preference — penalise based on overshoot.
        overshoot = rest_distance - limit
        distance_score = max(0.0, 0.7 - overshoot / 30.0)

    # Environment score: 1.0 if matches, 0.5 if adjacent, 0.2 if opposite.
    rest_noise = metadata.get("noise_level", "moderate")
    env_order = ["quiet", "moderate", "lively"]
    if rest_noise == env_pref:
        env_score = 1.0
    elif abs(env_order.index(rest_noise) - env_order.index(env_pref)) == 1:
        env_score = 0.6
    else:
        env_score = 0.2

    # Time score: 1.0 if the restaurant is open during at least one
    # of the participant's available time slots, 0.3 otherwise.
    rest_time_slots = set(metadata.get("time_slots", []))
    if not available_times:
        time_score = 0.5  # No preference — neutral.
    elif rest_time_slots & set(available_times):
        time_score = 1.0
    else:
        time_score = 0.3

    # Compute weighted utility.
    utility = (
        w_cuisine * cuisine_score
        + w_budget * budget_score
        + w_distance * distance_score
        + w_env * env_score
        + w_time * time_score
    )
    # Clamp to [0, 1].
    utility = max(0.0, min(1.0, round(utility, 6)))

    # --- Objection ---
    # Object if the restaurant's cuisine is explicitly not in preferences
    # and the participant has strong cuisine preferences, or if the
    # restaurant is way outside budget.
    objection = False
    if cuisine_prefs and rest_cuisine not in cuisine_prefs and cuisine_score == 0.0:
        # Strong objection if the cuisine is completely outside preferences.
        objection = True
    if rest_price_min > cap_budget_max * 1.5:
        # Strong budget overshoot.
        objection = True

    # --- Reason codes ---
    reason_codes: list[str] = []
    if rest_cuisine in cuisine_prefs:
        reason_codes.append("matches_common_cuisine")
    if rest_price_min <= cap_budget_max and rest_price_max >= cap_budget_min:
        reason_codes.append("within_group_budget")
    if rest_distance <= limit:
        reason_codes.append("reasonable_distance")
    if not available_times or (rest_time_slots & set(available_times)):
        reason_codes.append("fits_shared_time")
    if utility >= 0.6:
        reason_codes.append("balanced_tradeoff")

    # Filter to allowlisted codes only.
    reason_codes = validate_reason_codes(reason_codes)

    return EvaluationResult(
        candidate_key=candidate.candidate_key,
        hard_pass=hard_pass,
        utility=utility,
        objection=objection,
        reason_codes=reason_codes,
    )


# ---------------------------------------------------------------------------
# P9-09: Deterministic Aggregation
# ---------------------------------------------------------------------------


def aggregate_evaluations(
    candidate: CandidateInput,
    evaluations: list[EvaluationResult],
) -> AggregateResult:
    """Aggregate private evaluations into a public-safe result.

    Algorithm order (per P9 guide §11):
    1. Hard gate: If any participant's hard_pass=False, the candidate
       is eliminated (hard_gate_passed=False).
    2. Mean utility: Average utility across all participants.
    3. Fairness penalty: Penalise high variance in utility (to avoid
       one person being very happy while another is very unhappy).
    4. Distance score: Closer restaurants get a small bonus.
    5. Budget score: Restaurants more central to the group budget get
       a small bonus.
    6. Stable sort by deterministic candidate ID.

    The final aggregate_score is in [0, 1]. The public_reason is
    built from allowlisted reason codes only.

    Returns:
        AggregateResult with aggregate_score, public_reason, rank, and
        hard_gate_passed.
    """
    if not evaluations:
        return AggregateResult(
            candidate_key=candidate.candidate_key,
            aggregate_score=0.0,
            public_reason="No evaluations available.",
            rank=0,
            hard_gate_passed=False,
        )

    # 1. Hard gate.
    hard_gate_passed = all(e.hard_pass for e in evaluations)

    # 2. Mean utility.
    mean_utility = sum(e.utility for e in evaluations) / len(evaluations)

    # 3. Fairness penalty: reduce score if utility variance is high.
    if len(evaluations) > 1:
        variance = sum(
            (e.utility - mean_utility) ** 2 for e in evaluations
        ) / len(evaluations)
        std_dev = math.sqrt(variance)
        # Penalty: up to 0.15 reduction for high variance.
        fairness_penalty = min(0.15, std_dev * 0.3)
    else:
        fairness_penalty = 0.0

    # 4. Distance score bonus.
    metadata = candidate.public_metadata or {}
    rest_distance = int(metadata.get("distance_minutes", 30))
    # Closer restaurants get up to 0.05 bonus.
    distance_bonus = max(0.0, 0.05 * (1 - rest_distance / 30.0))

    # 5. Budget centrality bonus.
    rest_price_min = float(metadata.get("price_min", 0))
    rest_price_max = float(metadata.get("price_max", 0))
    # Bonus is higher when the restaurant's mid-price is close to
    # the group's average budget midpoint. We don't have the group's
    # budget here, so we use a neutral bonus based on price range
    # tightness (smaller range = more predictable = small bonus).
    price_range = rest_price_max - rest_price_min
    budget_bonus = max(0.0, 0.03 * (1 - min(price_range / 100.0, 1.0)))

    # Compute final aggregate score.
    aggregate_score = mean_utility - fairness_penalty + distance_bonus + budget_bonus

    # If hard gate failed, set score to 0.
    aggregate_score = (
        0.0 if not hard_gate_passed
        else max(0.0, min(1.0, round(aggregate_score, 6)))
    )

    # 6. Collect reason codes (union across all evaluations, filtered).
    all_reason_codes: list[str] = []
    seen: set[str] = set()
    for e in evaluations:
        for code in e.reason_codes:
            if code not in seen:
                all_reason_codes.append(code)
                seen.add(code)

    # Build public reason text from allowlisted codes.
    from .reasons import build_public_reason_text

    public_reason = build_public_reason_text(all_reason_codes)

    # Check for objections — if any participant objects, note it.
    has_objection = any(e.objection for e in evaluations)
    if has_objection:
        public_reason += " (note: some participants had concerns)"

    return AggregateResult(
        candidate_key=candidate.candidate_key,
        aggregate_score=aggregate_score,
        public_reason=public_reason,
        rank=0,  # Rank is assigned by build_public_result
        hard_gate_passed=hard_gate_passed,
    )


# ---------------------------------------------------------------------------
# P9-09 (continued): Build public result
# ---------------------------------------------------------------------------


def build_ranked_result(
    aggregates: list[AggregateResult],
) -> dict[str, Any]:
    """Build the final public result from aggregated candidates.

    Ranking algorithm (deterministic):
    1. Eliminated candidates (hard_gate_passed=False) go to the bottom.
    2. Among passing candidates, sort by aggregate_score descending.
    3. Ties are broken by candidate_key ascending (deterministic ID).

    Returns:
        Dict with:
        - selected_candidate_key: The top-ranked candidate.
        - public_summary: A safe, non-identifying summary.
        - ranked_candidates: List of {candidate_key, score, rank}.
    """
    if not aggregates:
        return {
            "selected_candidate_key": None,
            "public_summary": "No candidates available for this scenario.",
            "ranked_candidates": [],
        }

    # Sort: passing candidates first (by score desc), then by key asc.
    def sort_key(a: AggregateResult) -> tuple[int, float, str]:
        # hard_gate_passed=True first (0 < 1), then score desc, then key asc.
        return (0 if a.hard_gate_passed else 1, -a.aggregate_score, a.candidate_key)

    sorted_aggs = sorted(aggregates, key=sort_key)

    # Assign ranks.
    for i, agg in enumerate(sorted_aggs):
        agg.rank = i + 1

    selected = sorted_aggs[0] if sorted_aggs[0].hard_gate_passed else None

    ranked = [
        {
            "candidate_key": a.candidate_key,
            "score": a.aggregate_score,
            "rank": a.rank,
            "hard_gate_passed": a.hard_gate_passed,
            "public_reason": a.public_reason,
        }
        for a in sorted_aggs
    ]

    if selected:
        summary = f"Recommended: {selected.candidate_key}. {selected.public_reason}"
    else:
        summary = "No candidate passed all hard constraints. Please try again with different preferences."

    return {
        "selected_candidate_key": selected.candidate_key if selected else None,
        "public_summary": summary,
        "ranked_candidates": ranked,
    }
