"""P9-06: Fictional restaurant dataset for the dorm dinner scenario.

All restaurants are entirely fictional. No real business data is used.
The data is deterministic — the same seed always produces the same
restaurants, ensuring reproducible demos.

Each restaurant has:
- id: deterministic string identifier (e.g. "r001").
- name: fictional restaurant name.
- cuisine: Cuisine enum value.
- price_min / price_max: per-person price range in CNY.
- distance_minutes: walking distance from the dormitory.
- capacity: maximum group size.
- noise_level: NoiseLevel enum value.
- tags: list of string tags for public display.
- dietary_options: list of dietary options the restaurant can accommodate.
- time_slots: list of time slots the restaurant is open.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .schema import Cuisine, DietaryRestriction, DistancePreference, TimeSlot

# ---------------------------------------------------------------------------
# Noise level enum
# ---------------------------------------------------------------------------


class NoiseLevel(StrEnum):
    """Restaurant noise/atmosphere level."""

    QUIET = "quiet"
    MODERATE = "moderate"
    LIVELY = "lively"


# ---------------------------------------------------------------------------
# Restaurant data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Restaurant:
    """A fictional restaurant with deterministic properties."""

    id: str
    name: str
    cuisine: Cuisine
    price_min: float
    price_max: float
    distance_minutes: int
    capacity: int
    noise_level: NoiseLevel
    tags: list[str] = field(default_factory=list)
    dietary_options: list[DietaryRestriction] = field(default_factory=list)
    time_slots: list[TimeSlot] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, Any]:
        """Return a public-safe dict (no sensitive data).

        This dict is safe to include in candidate public_metadata —
        it contains only restaurant attributes that are already public
        (name, cuisine, price range, distance, tags).
        """
        return {
            "id": self.id,
            "name": self.name,
            "cuisine": self.cuisine.value,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "distance_minutes": self.distance_minutes,
            "capacity": self.capacity,
            "noise_level": self.noise_level.value,
            "tags": list(self.tags),
        }

    def to_candidate_metadata(self) -> dict[str, Any]:
        """Return metadata for CandidateInput.public_metadata.

        This is the data that plugins use during candidate generation
        and evaluation. It is safe to expose publicly — it includes
        dietary_options and time_slots which are public restaurant
        attributes needed by the evaluation algorithm.
        """
        data = self.to_public_dict()
        data["dietary_options"] = [d.value for d in self.dietary_options]
        data["time_slots"] = [t.value for t in self.time_slots]
        return data

    @property
    def distance_preference(self) -> DistancePreference:
        """Map distance_minutes to a DistancePreference enum."""
        if self.distance_minutes <= 10:
            return DistancePreference.CLOSE
        elif self.distance_minutes <= 20:
            return DistancePreference.MODERATE
        else:
            return DistancePreference.FAR


# ---------------------------------------------------------------------------
# Fictional restaurant dataset (8+ restaurants, deterministic)
# ---------------------------------------------------------------------------

RESTAURANTS: list[Restaurant] = [
    Restaurant(
        id="r001",
        name="蜀香居",
        cuisine=Cuisine.SICHUAN,
        price_min=25.0,
        price_max=60.0,
        distance_minutes=8,
        capacity=8,
        noise_level=NoiseLevel.LIVELY,
        tags=["麻辣", "川菜", "适合聚餐"],
        dietary_options=[DietaryRestriction.NONE],
        time_slots=[TimeSlot.DINNER, TimeSlot.LATE_DINNER],
    ),
    Restaurant(
        id="r002",
        name="粤味轩",
        cuisine=Cuisine.CANTONESE,
        price_min=30.0,
        price_max=70.0,
        distance_minutes=12,
        capacity=6,
        noise_level=NoiseLevel.MODERATE,
        tags=["清淡", "粤菜", "早茶"],
        dietary_options=[DietaryRestriction.NONE, DietaryRestriction.NO_SPICY],
        time_slots=[TimeSlot.LUNCH, TimeSlot.EARLY_DINNER, TimeSlot.DINNER],
    ),
    Restaurant(
        id="r003",
        name="北方饺子馆",
        cuisine=Cuisine.NORTHERN,
        price_min=15.0,
        price_max=35.0,
        distance_minutes=5,
        capacity=10,
        noise_level=NoiseLevel.QUIET,
        tags=["实惠", "面食", "饺子"],
        dietary_options=[
            DietaryRestriction.NONE,
            DietaryRestriction.VEGETARIAN,
        ],
        time_slots=[TimeSlot.LUNCH, TimeSlot.EARLY_DINNER, TimeSlot.DINNER],
    ),
    Restaurant(
        id="r004",
        name="沸腾鱼庄",
        cuisine=Cuisine.HOTPOT,
        price_min=40.0,
        price_max=90.0,
        distance_minutes=15,
        capacity=12,
        noise_level=NoiseLevel.LIVELY,
        tags=["火锅", "自助", "适合多人"],
        dietary_options=[
            DietaryRestriction.NONE,
            DietaryRestriction.VEGETARIAN,
            DietaryRestriction.HALAL,
        ],
        time_slots=[TimeSlot.EARLY_DINNER, TimeSlot.DINNER, TimeSlot.LATE_DINNER],
    ),
    Restaurant(
        id="r005",
        name="炭火烤肉社",
        cuisine=Cuisine.BBQ,
        price_min=50.0,
        price_max=100.0,
        distance_minutes=18,
        capacity=8,
        noise_level=NoiseLevel.LIVELY,
        tags=["烤肉", "啤酒", "夜宵"],
        dietary_options=[DietaryRestriction.NONE],
        time_slots=[TimeSlot.DINNER, TimeSlot.LATE_DINNER],
    ),
    Restaurant(
        id="r006",
        name="樱花日料",
        cuisine=Cuisine.JAPANESE,
        price_min=45.0,
        price_max=120.0,
        distance_minutes=22,
        capacity=6,
        noise_level=NoiseLevel.QUIET,
        tags=["日料", "寿司", "环境好"],
        dietary_options=[
            DietaryRestriction.NONE,
            DietaryRestriction.GLUTEN_FREE,
            DietaryRestriction.NUT_ALLERGY,
        ],
        time_slots=[TimeSlot.LUNCH, TimeSlot.EARLY_DINNER, TimeSlot.DINNER],
    ),
    Restaurant(
        id="r007",
        name="首尔厨房",
        cuisine=Cuisine.KOREAN,
        price_min=35.0,
        price_max=80.0,
        distance_minutes=10,
        capacity=8,
        noise_level=NoiseLevel.MODERATE,
        tags=["韩餐", "石锅拌饭", "部队锅"],
        dietary_options=[
            DietaryRestriction.NONE,
            DietaryRestriction.NO_SPICY,
        ],
        time_slots=[TimeSlot.LUNCH, TimeSlot.EARLY_DINNER, TimeSlot.DINNER],
    ),
    Restaurant(
        id="r008",
        name="绿野蔬食",
        cuisine=Cuisine.VEGETARIAN,
        price_min=20.0,
        price_max=50.0,
        distance_minutes=7,
        capacity=6,
        noise_level=NoiseLevel.QUIET,
        tags=["素食", "健康", "轻食"],
        dietary_options=[
            DietaryRestriction.VEGETARIAN,
            DietaryRestriction.VEGAN,
            DietaryRestriction.NUT_ALLERGY,
            DietaryRestriction.LACTOSE_INTOLERANT,
        ],
        time_slots=[TimeSlot.LUNCH, TimeSlot.EARLY_DINNER, TimeSlot.DINNER],
    ),
    Restaurant(
        id="r009",
        name="西餐小馆",
        cuisine=Cuisine.WESTERN,
        price_min=55.0,
        price_max=130.0,
        distance_minutes=25,
        capacity=4,
        noise_level=NoiseLevel.QUIET,
        tags=["西餐", "牛排", "氛围好"],
        dietary_options=[
            DietaryRestriction.NONE,
            DietaryRestriction.GLUTEN_FREE,
            DietaryRestriction.LACTOSE_INTOLERANT,
        ],
        time_slots=[TimeSlot.EARLY_DINNER, TimeSlot.DINNER],
    ),
    Restaurant(
        id="r010",
        name="速食工坊",
        cuisine=Cuisine.FAST_FOOD,
        price_min=12.0,
        price_max=30.0,
        distance_minutes=3,
        capacity=4,
        noise_level=NoiseLevel.MODERATE,
        tags=["快餐", "便捷", "实惠"],
        dietary_options=[
            DietaryRestriction.NONE,
            DietaryRestriction.VEGETARIAN,
        ],
        time_slots=[TimeSlot.LUNCH, TimeSlot.EARLY_DINNER, TimeSlot.DINNER, TimeSlot.LATE_DINNER],
    ),
]


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


_RESTAURANT_BY_ID: dict[str, Restaurant] = {r.id: r for r in RESTAURANTS}


def get_restaurant_by_id(restaurant_id: str) -> Restaurant | None:
    """Look up a restaurant by its deterministic ID."""
    return _RESTAURANT_BY_ID.get(restaurant_id)


def get_all_restaurants() -> list[Restaurant]:
    """Return all restaurants (deterministic order)."""
    return list(RESTAURANTS)


def get_restaurants_by_cuisine(cuisine: Cuisine) -> list[Restaurant]:
    """Filter restaurants by cuisine type."""
    return [r for r in RESTAURANTS if r.cuisine == cuisine]


def get_restaurants_within_budget(
    budget_min: float,
    budget_max: float,
) -> list[Restaurant]:
    """Filter restaurants that fit within the group's budget range.

    A restaurant fits if its price_min <= budget_max and its
    price_max >= budget_min (ranges overlap).
    """
    return [
        r
        for r in RESTAURANTS
        if r.price_min <= budget_max and r.price_max >= budget_min
    ]


def get_restaurants_within_distance(max_minutes: int) -> list[Restaurant]:
    """Filter restaurants within a maximum walking distance."""
    return [r for r in RESTAURANTS if r.distance_minutes <= max_minutes]


def get_restaurants_accommodating_dietary(
    restrictions: set[DietaryRestriction],
) -> list[Restaurant]:
    """Filter restaurants that can accommodate ALL dietary restrictions.

    A restaurant qualifies if it offers options for every restriction
    in the set. If the set only contains ``NONE``, all restaurants qualify.
    """
    if not restrictions or restrictions == {DietaryRestriction.NONE}:
        return list(RESTAURANTS)

    return [
        r
        for r in RESTAURANTS
        if restrictions.issubset(set(r.dietary_options))
    ]


def get_restaurants_open_at(time_slots: set[TimeSlot]) -> list[Restaurant]:
    """Filter restaurants that are open during at least one of the given time slots."""
    if not time_slots:
        return list(RESTAURANTS)
    return [
        r
        for r in RESTAURANTS
        if any(t in r.time_slots for t in time_slots)
    ]
