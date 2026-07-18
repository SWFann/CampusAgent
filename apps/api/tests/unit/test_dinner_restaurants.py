"""P9-06: Fictional restaurant dataset tests.

Tests cover (per P9 guide §8):
- At least 8 restaurants exist.
- All restaurants have deterministic IDs.
- All restaurants are fictional (no real business data).
- Each restaurant has: name, cuisine, price_min/max, distance_minutes,
  capacity, noise_level, tags, dietary_options, time_slots.
- Lookup helpers work correctly.
- to_public_dict and to_candidate_metadata return safe data.
- distance_preference property maps correctly.
"""
from __future__ import annotations

from src.modules.scenes.plugins.dorm_dinner.restaurants import (
    RESTAURANTS,
    NoiseLevel,
    Restaurant,
    get_all_restaurants,
    get_restaurant_by_id,
    get_restaurants_accommodating_dietary,
    get_restaurants_by_cuisine,
    get_restaurants_open_at,
    get_restaurants_within_budget,
    get_restaurants_within_distance,
)
from src.modules.scenes.plugins.dorm_dinner.schema import (
    Cuisine,
    DietaryRestriction,
    DistancePreference,
    TimeSlot,
)


class TestRestaurantDataset:
    """Tests for the restaurant dataset."""

    def test_at_least_8_restaurants(self) -> None:
        """There must be at least 8 restaurants."""
        assert len(RESTAURANTS) >= 8

    def test_all_have_deterministic_ids(self) -> None:
        """All restaurants must have deterministic string IDs."""
        ids = [r.id for r in RESTAURANTS]
        assert all(isinstance(id_, str) for id_ in ids)
        assert all(id_.startswith("r") for id_ in ids)
        # IDs must be unique.
        assert len(ids) == len(set(ids))

    def test_all_have_required_fields(self) -> None:
        """Each restaurant must have all required fields."""
        for r in RESTAURANTS:
            assert r.name, f"Restaurant {r.id} has empty name"
            assert isinstance(r.cuisine, Cuisine)
            assert r.price_min >= 0
            assert r.price_max >= r.price_min
            assert r.distance_minutes > 0
            assert r.capacity > 0
            assert isinstance(r.noise_level, NoiseLevel)
            assert isinstance(r.tags, list)
            assert isinstance(r.dietary_options, list)
            assert isinstance(r.time_slots, list)

    def test_restaurants_are_fictional(self) -> None:
        """Restaurant names should be fictional (not real brands)."""
        # These are fictional names created for the demo.
        real_brands = ["海底捞", "麦当劳", "肯德基", "星巴克", "必胜客"]
        for r in RESTAURANTS:
            for brand in real_brands:
                assert brand not in r.name, f"Real brand '{brand}' found in restaurant name"

    def test_deterministic_order(self) -> None:
        """get_all_restaurants returns restaurants in deterministic order."""
        r1 = get_all_restaurants()
        r2 = get_all_restaurants()
        assert [r.id for r in r1] == [r.id for r in r2]


class TestRestaurantLookupHelpers:
    """Tests for restaurant lookup functions."""

    def test_get_restaurant_by_id_exists(self) -> None:
        """get_restaurant_by_id returns the correct restaurant."""
        r = get_restaurant_by_id("r001")
        assert r is not None
        assert r.id == "r001"
        assert r.name == "蜀香居"

    def test_get_restaurant_by_id_not_found(self) -> None:
        """get_restaurant_by_id returns None for unknown ID."""
        assert get_restaurant_by_id("r999") is None

    def test_get_restaurants_by_cuisine(self) -> None:
        """get_restaurants_by_cuisine filters correctly."""
        sichuan = get_restaurants_by_cuisine(Cuisine.SICHUAN)
        assert len(sichuan) >= 1
        assert all(r.cuisine == Cuisine.SICHUAN for r in sichuan)

    def test_get_restaurants_within_budget(self) -> None:
        """get_restaurants_within_budget filters by overlapping range."""
        # Budget 20-50: restaurants whose price_min <= 50 and price_max >= 20.
        results = get_restaurants_within_budget(20, 50)
        for r in results:
            assert r.price_min <= 50
            assert r.price_max >= 20

    def test_get_restaurants_within_distance(self) -> None:
        """get_restaurants_within_distance filters by max minutes."""
        results = get_restaurants_within_distance(10)
        for r in results:
            assert r.distance_minutes <= 10

    def test_get_restaurants_accommodating_dietary_none(self) -> None:
        """All restaurants accommodate 'none' restriction."""
        results = get_restaurants_accommodating_dietary({DietaryRestriction.NONE})
        assert len(results) == len(RESTAURANTS)

    def test_get_restaurants_accommodating_dietary_vegetarian(self) -> None:
        """Only restaurants with vegetarian options are returned."""
        results = get_restaurants_accommodating_dietary({DietaryRestriction.VEGETARIAN})
        for r in results:
            assert DietaryRestriction.VEGETARIAN in r.dietary_options

    def test_get_restaurants_accommodating_multiple_restrictions(self) -> None:
        """Restaurants must accommodate ALL restrictions."""
        results = get_restaurants_accommodating_dietary({
            DietaryRestriction.VEGETARIAN,
            DietaryRestriction.NUT_ALLERGY,
        })
        for r in results:
            assert DietaryRestriction.VEGETARIAN in r.dietary_options
            assert DietaryRestriction.NUT_ALLERGY in r.dietary_options

    def test_get_restaurants_open_at(self) -> None:
        """get_restaurants_open_at filters by time slot overlap."""
        results = get_restaurants_open_at({TimeSlot.DINNER})
        for r in results:
            assert TimeSlot.DINNER in r.time_slots

    def test_get_restaurants_open_at_empty_returns_all(self) -> None:
        """Empty time_slots set returns all restaurants."""
        results = get_restaurants_open_at(set())
        assert len(results) == len(RESTAURANTS)


class TestRestaurantPublicDict:
    """Tests for to_public_dict and to_candidate_metadata."""

    def test_to_public_dict_has_safe_fields(self) -> None:
        """to_public_dict returns only safe public fields."""
        r = get_restaurant_by_id("r001")
        assert r is not None
        d = r.to_public_dict()
        assert "id" in d
        assert "name" in d
        assert "cuisine" in d
        assert "price_min" in d
        assert "price_max" in d
        assert "distance_minutes" in d
        assert "capacity" in d
        assert "noise_level" in d
        assert "tags" in d

    def test_to_public_dict_no_sensitive_fields(self) -> None:
        """to_public_dict must not contain sensitive fields."""
        r = get_restaurant_by_id("r001")
        assert r is not None
        d = r.to_public_dict()
        assert "notes" not in d
        assert "email" not in d
        assert "user_id" not in d

    def test_to_candidate_metadata_includes_evaluation_fields(self) -> None:
        """to_candidate_metadata includes dietary_options and time_slots."""
        r = get_restaurant_by_id("r001")
        assert r is not None
        metadata = r.to_candidate_metadata()
        # Must include fields needed by the evaluation algorithm.
        assert "dietary_options" in metadata
        assert "time_slots" in metadata
        # Must also include all public dict fields.
        public = r.to_public_dict()
        for key in public:
            assert key in metadata


class TestRestaurantDistancePreference:
    """Tests for the distance_preference property."""

    def test_close_distance(self) -> None:
        """distance_minutes <= 10 maps to CLOSE."""
        r = Restaurant(
            id="test1", name="Test", cuisine=Cuisine.FAST_FOOD,
            price_min=10, price_max=30, distance_minutes=5,
            capacity=4, noise_level=NoiseLevel.QUIET,
        )
        assert r.distance_preference == DistancePreference.CLOSE

    def test_moderate_distance(self) -> None:
        """distance_minutes 11-20 maps to MODERATE."""
        r = Restaurant(
            id="test2", name="Test", cuisine=Cuisine.FAST_FOOD,
            price_min=10, price_max=30, distance_minutes=15,
            capacity=4, noise_level=NoiseLevel.QUIET,
        )
        assert r.distance_preference == DistancePreference.MODERATE

    def test_far_distance(self) -> None:
        """distance_minutes > 20 maps to FAR."""
        r = Restaurant(
            id="test3", name="Test", cuisine=Cuisine.FAST_FOOD,
            price_min=10, price_max=30, distance_minutes=25,
            capacity=4, noise_level=NoiseLevel.QUIET,
        )
        assert r.distance_preference == DistancePreference.FAR

    def test_boundary_10_minutes(self) -> None:
        """10 minutes maps to CLOSE (boundary)."""
        r = Restaurant(
            id="test4", name="Test", cuisine=Cuisine.FAST_FOOD,
            price_min=10, price_max=30, distance_minutes=10,
            capacity=4, noise_level=NoiseLevel.QUIET,
        )
        assert r.distance_preference == DistancePreference.CLOSE

    def test_boundary_20_minutes(self) -> None:
        """20 minutes maps to MODERATE (boundary)."""
        r = Restaurant(
            id="test5", name="Test", cuisine=Cuisine.FAST_FOOD,
            price_min=10, price_max=30, distance_minutes=20,
            capacity=4, noise_level=NoiseLevel.QUIET,
        )
        assert r.distance_preference == DistancePreference.MODERATE
