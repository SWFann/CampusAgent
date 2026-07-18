"""P9-10: Safe public reason code allowlist tests.

Tests cover (per P9 guide §12):
- Only allowlisted reason codes are used.
- Forbidden patterns (individual, member, user, etc.) are rejected.
- build_public_reason_text produces safe, non-identifying text.
- validate_reason_codes filters out non-allowlisted codes.
- check_reason_for_leaks detects forbidden patterns.
"""
from __future__ import annotations

from src.modules.scenes.plugins.dorm_dinner.reasons import (
    FORBIDDEN_REASON_PATTERNS,
    REASON_CODE_ALLOWLIST,
    build_public_reason_text,
    check_reason_for_leaks,
    get_reason_description,
    is_allowed_reason_code,
    validate_reason_codes,
)


class TestReasonCodeAllowlist:
    """Tests for the reason code allowlist."""

    def test_allowlist_has_5_codes(self) -> None:
        """The allowlist must have exactly 5 reason codes."""
        expected = {
            "matches_common_cuisine",
            "within_group_budget",
            "reasonable_distance",
            "fits_shared_time",
            "balanced_tradeoff",
        }
        assert set(REASON_CODE_ALLOWLIST.keys()) == expected

    def test_allowlist_values_are_non_empty(self) -> None:
        """Each allowlisted code has a non-empty description."""
        for _code, desc in REASON_CODE_ALLOWLIST.items():
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_allowlist_descriptions_are_safe(self) -> None:
        """Allowlist descriptions must not contain forbidden patterns."""
        for code, desc in REASON_CODE_ALLOWLIST.items():
            assert check_reason_for_leaks(desc), (
                f"Description for '{code}' contains forbidden pattern: {desc}"
            )


class TestIsAllowedReasonCode:
    """Tests for is_allowed_reason_code."""

    def test_allowed_code_returns_true(self) -> None:
        """Allowlisted codes return True."""
        assert is_allowed_reason_code("within_group_budget")
        assert is_allowed_reason_code("matches_common_cuisine")
        assert is_allowed_reason_code("reasonable_distance")
        assert is_allowed_reason_code("fits_shared_time")
        assert is_allowed_reason_code("balanced_tradeoff")

    def test_non_allowed_code_returns_false(self) -> None:
        """Non-allowlisted codes return False."""
        assert not is_allowed_reason_code("budget_low")
        assert not is_allowed_reason_code("individual_allergy")
        assert not is_allowed_reason_code("zhang_san_budget")
        assert not is_allowed_reason_code("")


class TestValidateReasonCodes:
    """Tests for validate_reason_codes."""

    def test_filters_non_allowlisted(self) -> None:
        """Non-allowlisted codes are filtered out."""
        codes = ["within_group_budget", "budget_low", "individual_allergy"]
        result = validate_reason_codes(codes)
        assert result == ["within_group_budget"]

    def test_all_allowlisted_passes(self) -> None:
        """All allowlisted codes pass through."""
        codes = ["within_group_budget", "reasonable_distance"]
        result = validate_reason_codes(codes)
        assert result == codes

    def test_empty_input(self) -> None:
        """Empty input returns empty list."""
        assert validate_reason_codes([]) == []

    def test_all_non_allowlisted(self) -> None:
        """All non-allowlisted returns empty list."""
        codes = ["budget_low", "individual_allergy", "zhang_san"]
        assert validate_reason_codes(codes) == []


class TestBuildPublicReasonText:
    """Tests for build_public_reason_text."""

    def test_single_code(self) -> None:
        """Single reason code produces a capitalised description."""
        text = build_public_reason_text(["within_group_budget"])
        assert text[0].isupper()
        assert "budget" in text.lower()

    def test_multiple_codes_joined_with_semicolons(self) -> None:
        """Multiple codes are joined with semicolons."""
        text = build_public_reason_text([
            "within_group_budget",
            "reasonable_distance",
        ])
        assert ";" in text

    def test_empty_codes_returns_default(self) -> None:
        """Empty codes returns a default safe message."""
        text = build_public_reason_text([])
        assert "group preferences" in text.lower()

    def test_non_allowlisted_codes_filtered(self) -> None:
        """Non-allowlisted codes are silently dropped."""
        text = build_public_reason_text(["budget_low", "within_group_budget"])
        assert "budget_low" not in text
        assert "budget" in text.lower()

    def test_text_does_not_identify_members(self) -> None:
        """The reason text never identifies individual members."""
        codes = ["within_group_budget", "matches_common_cuisine"]
        text = build_public_reason_text(codes)
        assert check_reason_for_leaks(text)

    def test_text_does_not_contain_notes(self) -> None:
        """The reason text never contains notes or raw data."""
        text = build_public_reason_text(["within_group_budget"])
        assert "notes" not in text.lower()
        assert "raw" not in text.lower()


class TestCheckReasonForLeaks:
    """Tests for check_reason_for_leaks."""

    def test_safe_text_returns_true(self) -> None:
        """Safe text returns True."""
        assert check_reason_for_leaks("Fits within the group's budget range")
        assert check_reason_for_leaks("Matches the group's preferred cuisine types")

    def test_text_with_individual_returns_false(self) -> None:
        """Text containing 'individual' returns False."""
        assert not check_reason_for_leaks("Because individual member has low budget")

    def test_text_with_member_returns_false(self) -> None:
        """Text containing 'member' returns False."""
        assert not check_reason_for_leaks("One member cannot eat spicy food")

    def test_text_with_user_returns_false(self) -> None:
        """Text containing 'user' returns False."""
        assert not check_reason_for_leaks("User Zhang San prefers cheap food")

    def test_text_with_notes_returns_false(self) -> None:
        """Text containing 'notes' returns False."""
        assert not check_reason_for_leaks("Based on the user's notes")

    def test_text_with_budget_low_returns_false(self) -> None:
        """Text containing 'budget_low' returns False."""
        assert not check_reason_for_leaks("budget_low is a concern")

    def test_text_with_economic_returns_false(self) -> None:
        """Text containing 'economic' returns False."""
        assert not check_reason_for_leaks("Economic pressure from one participant")

    def test_text_with_allergy_returns_false(self) -> None:
        """Text containing 'allergy' returns False."""
        assert not check_reason_for_leaks("Someone has a nut allergy")

    def test_text_with_dietary_returns_false(self) -> None:
        """Text containing 'dietary' returns False."""
        assert not check_reason_for_leaks("Dietary restrictions prevent this choice")


class TestGetReasonDescription:
    """Tests for get_reason_description."""

    def test_known_code_returns_description(self) -> None:
        """Known code returns its description."""
        desc = get_reason_description("within_group_budget")
        assert "budget" in desc.lower()

    def test_unknown_code_returns_empty(self) -> None:
        """Unknown code returns empty string."""
        assert get_reason_description("unknown_code") == ""


class TestForbiddenPatterns:
    """Tests for the forbidden patterns set."""

    def test_forbidden_patterns_include_individual(self) -> None:
        """'individual' is in the forbidden patterns."""
        assert "individual" in FORBIDDEN_REASON_PATTERNS

    def test_forbidden_patterns_include_member(self) -> None:
        """'member' is in the forbidden patterns."""
        assert "member" in FORBIDDEN_REASON_PATTERNS

    def test_forbidden_patterns_include_user(self) -> None:
        """'user' is in the forbidden patterns."""
        assert "user" in FORBIDDEN_REASON_PATTERNS

    def test_forbidden_patterns_include_notes(self) -> None:
        """'notes' is in the forbidden patterns."""
        assert "notes" in FORBIDDEN_REASON_PATTERNS

    def test_forbidden_patterns_include_surnames(self) -> None:
        """Common Chinese surnames are in the forbidden patterns."""
        for name in ["zhang", "li", "wang", "chen"]:
            assert name in FORBIDDEN_REASON_PATTERNS
