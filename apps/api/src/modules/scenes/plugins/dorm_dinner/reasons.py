"""P9-10: Safe public reason code allowlist and mapping.

Public reasons explain *why* a candidate was selected using only
allowlisted reason codes. They never:
- Identify a specific member ("because Zhang San has a low budget").
- Disclose individual dietary restrictions ("someone can't eat spicy
  food" — this is aggregate_only, and even in aggregate it must not
  point to a member).
- Reveal economic/psychological inferences ("a member has financial
  pressure").
- Output the original notes text.

The allowlist is frozen — plugins may only use reason codes defined
here. Any reason code not in the allowlist is rejected.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Frozen allowlist of reason codes
# ---------------------------------------------------------------------------

# Each reason code maps to a safe, non-identifying public description.
# The descriptions use only aggregate language. This dict is treated as
# immutable — do not mutate at runtime.
REASON_CODE_ALLOWLIST: dict[str, str] = {
    "matches_common_cuisine": "matches the group's preferred cuisine types",
    "within_group_budget": "fits within the group's budget range",
    "reasonable_distance": "within a reasonable walking distance for the group",
    "fits_shared_time": "available during the group's shared time slots",
    "balanced_tradeoff": "offers a balanced tradeoff across all preferences",
}


# Reason codes that are forbidden (would identify members or leak P4 data).
FORBIDDEN_REASON_PATTERNS: frozenset[str] = frozenset(
    {
        "individual",
        "member",
        "user",
        "person",
        "zhang",
        "li",
        "wang",
        "chen",
        "budget_low",
        "budget_high",
        "economic",
        "financial",
        "psychological",
        "allergy",
        "restriction",
        "dietary",
        "notes",
        "raw",
    }
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def is_allowed_reason_code(code: str) -> bool:
    """Check whether a reason code is in the allowlist."""
    return code in REASON_CODE_ALLOWLIST


def validate_reason_codes(codes: list[str]) -> list[str]:
    """Filter a list of reason codes, keeping only allowlisted ones.

    This is a defence-in-depth measure — even if the algorithm
    accidentally produces a non-allowlisted code, it is silently
    dropped before reaching the public output.
    """
    return [c for c in codes if c in REASON_CODE_ALLOWLIST]


def get_reason_description(code: str) -> str:
    """Get the safe public description for a reason code.

    Returns an empty string if the code is not in the allowlist.
    """
    return REASON_CODE_ALLOWLIST.get(code, "")


def build_public_reason_text(codes: list[str]) -> str:
    """Build a human-readable public reason string from reason codes.

    Only allowlisted codes are used. The output never identifies
    individual members or discloses private data.

    Example:
        >>> build_public_reason_text(["within_group_budget", "reasonable_distance"])
        'Fits within the group's budget range; within a reasonable walking distance for the group'
    """
    safe_codes = validate_reason_codes(codes)
    if not safe_codes:
        return "Selected based on overall group preferences."

    descriptions = [REASON_CODE_ALLOWLIST[c] for c in safe_codes]
    # Capitalise the first letter and join with semicolons.
    text = "; ".join(descriptions)
    return text[0].upper() + text[1:] if text else ""


def check_reason_for_leaks(reason_text: str) -> bool:
    """Check whether a public reason text contains forbidden patterns.

    Returns True if the text is safe (no leaks), False if it contains
    a forbidden pattern.

    This is used by tests to verify that the reason text does not
    accidentally leak individual member information.
    """
    text_lower = reason_text.lower()
    return all(pattern not in text_lower for pattern in FORBIDDEN_REASON_PATTERNS)
