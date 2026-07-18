"""P9-01: Frozen input schema for the dorm dinner planning scenario.

Fields (per P9 guide §3):
- budget_min / budget_max: spending range in CNY.
- cuisine_preferences: ordered list of preferred cuisines.
- dietary_restrictions: medical / religious / personal restrictions.
- distance_preference: acceptable walking distance.
- available_time: time slots the participant is available.
- environment_preference: preferred noise / atmosphere level.
- notes: free-text remarks (NEVER disclosed, NEVER sent to model).

Validation rules (P9-03):
- budget_min >= 0.
- budget_max >= budget_min.
- cuisine enum membership.
- distance enum membership.
- environment enum membership.
- notes max length 500, may be empty.
- Prompt-injection text in notes is treated as ordinary private text —
  it never reaches the model, so it cannot execute.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Cuisine(StrEnum):
    """Supported cuisine types (fictional categories for the demo)."""

    SICHUAN = "sichuan"
    CANTONESE = "cantonese"
    NORTHERN = "northern"
    HOTPOT = "hotpot"
    BBQ = "bbq"
    JAPANESE = "japanese"
    KOREAN = "korean"
    WESTERN = "western"
    FAST_FOOD = "fast_food"
    VEGETARIAN = "vegetarian"


class DietaryRestriction(StrEnum):
    """Dietary restrictions that must be respected as hard constraints."""

    NONE = "none"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    HALAL = "halal"
    GLUTEN_FREE = "gluten_free"
    NUT_ALLERGY = "nut_allergy"
    LACTOSE_INTOLERANT = "lactose_intolerant"
    NO_SPICY = "no_spicy"


class DistancePreference(StrEnum):
    """Acceptable walking distance from the dormitory."""

    CLOSE = "close"        # <= 10 minutes
    MODERATE = "moderate"  # <= 20 minutes
    FAR = "far"            # <= 30 minutes


class EnvironmentPreference(StrEnum):
    """Preferred noise / atmosphere level."""

    QUIET = "quiet"
    MODERATE = "moderate"
    LIVELY = "lively"


class TimeSlot(StrEnum):
    """Available time slots for the dinner."""

    LUNCH = "lunch"              # 11:30 - 13:00
    EARLY_DINNER = "early_dinner"  # 17:00 - 18:00
    DINNER = "dinner"             # 18:00 - 20:00
    LATE_DINNER = "late_dinner"   # 20:00 - 22:00


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


# Maximum length for the free-text notes field.
MAX_NOTES_LENGTH = 500

# Maximum budget values (sanity bounds to prevent abuse).
MAX_BUDGET = 1000.0


class DinnerPreferenceInput(BaseModel):
    """Validated private preference input for a single participant.

    This model is used by the plugin's ``validate_private_submission``
    to enforce range, enum, and length constraints before the raw data
    is encrypted and stored.

    Privacy:
    - The ``notes`` field is treated as P4 (never_disclose). It is
      validated for length only — its content is never parsed, never
      sent to a model, and never included in any capsule or public
      output.
    - Prompt-injection attempts in ``notes`` are inert because the
      field never reaches any model prompt.
    """

    budget_min: float = Field(
        ...,
        ge=0,
        le=MAX_BUDGET,
        description="Minimum acceptable spending per person (CNY).",
    )
    budget_max: float = Field(
        ...,
        ge=0,
        le=MAX_BUDGET,
        description="Maximum acceptable spending per person (CNY).",
    )
    cuisine_preferences: list[Cuisine] = Field(
        default_factory=list,
        description="Ordered list of preferred cuisines (most preferred first).",
    )
    dietary_restrictions: list[DietaryRestriction] = Field(
        default_factory=list,
        description="Medical, religious, or personal dietary restrictions.",
    )
    distance_preference: DistancePreference = Field(
        default=DistancePreference.MODERATE,
        description="Acceptable walking distance from the dormitory.",
    )
    available_time: list[TimeSlot] = Field(
        default_factory=list,
        description="Time slots the participant is available.",
    )
    environment_preference: EnvironmentPreference = Field(
        default=EnvironmentPreference.MODERATE,
        description="Preferred noise / atmosphere level.",
    )
    notes: str = Field(
        default="",
        max_length=MAX_NOTES_LENGTH,
        description="Free-text remarks. NEVER disclosed or sent to model.",
    )

    model_config = {"extra": "forbid"}

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("notes")
    @classmethod
    def _validate_notes(cls, v: str) -> str:
        """Notes are validated for length only — content is never parsed."""
        if len(v) > MAX_NOTES_LENGTH:
            raise ValueError(
                f"notes exceeds maximum length of {MAX_NOTES_LENGTH} characters"
            )
        return v

    @model_validator(mode="after")
    def _validate_budget_range(self) -> DinnerPreferenceInput:
        """budget_max must be >= budget_min."""
        if self.budget_max < self.budget_min:
            raise ValueError(
                "budget_max must be greater than or equal to budget_min"
            )
        return self

    @field_validator("cuisine_preferences")
    @classmethod
    def _dedupe_cuisines(cls, v: list[Cuisine]) -> list[Cuisine]:
        """Remove duplicate cuisines while preserving order."""
        seen: set[str] = set()
        result: list[Cuisine] = []
        for c in v:
            if c.value not in seen:
                seen.add(c.value)
                result.append(c)
        return result

    @field_validator("dietary_restrictions")
    @classmethod
    def _normalise_restrictions(cls, v: list[DietaryRestriction]) -> list[DietaryRestriction]:
        """Remove duplicates and filter out 'none' if other restrictions exist."""
        if not v:
            return [DietaryRestriction.NONE]
        # If 'none' appears alongside real restrictions, drop 'none'.
        filtered = [r for r in v if r != DietaryRestriction.NONE]
        if not filtered:
            return [DietaryRestriction.NONE]
        # Dedupe while preserving order.
        seen: set[str] = set()
        result: list[DietaryRestriction] = []
        for r in filtered:
            if r.value not in seen:
                seen.add(r.value)
                result.append(r)
        return result

    @field_validator("available_time")
    @classmethod
    def _dedupe_time_slots(cls, v: list[TimeSlot]) -> list[TimeSlot]:
        """Remove duplicate time slots while preserving order."""
        seen: set[str] = set()
        result: list[TimeSlot] = []
        for t in v:
            if t.value not in seen:
                seen.add(t.value)
                result.append(t)
        return result


# ---------------------------------------------------------------------------
# Raw preferences dict helpers
# ---------------------------------------------------------------------------


def validate_raw_preferences(raw: dict[str, Any]) -> DinnerPreferenceInput:
    """Validate a raw preferences dict and return the typed model.

    Raises:
        ValueError: If the input fails validation (with a human-readable
            message suitable for the SceneSubmissionError).
    """
    try:
        return DinnerPreferenceInput.model_validate(raw)
    except Exception as exc:
        # Re-raise with a clean message.
        raise ValueError(str(exc)) from exc


def preference_to_dict(prefs: DinnerPreferenceInput) -> dict[str, Any]:
    """Convert a validated preference model to a plain dict.

    This is used when encrypting the raw submission.
    """
    return prefs.model_dump(mode="json")
