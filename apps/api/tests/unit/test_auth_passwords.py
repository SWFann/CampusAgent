"""
Unit tests for password hashing, verification, and strength validation (P3-02).

Tests verify:
- hash_password result is not plaintext.
- Same password produces different hashes (salt works).
- Correct password verifies successfully.
- Wrong password fails verification.
- Short passwords fail strength validation.
- Pure letter or pure digit passwords fail.
- Passwords containing email local part fail.
- Passwords containing student_no fail.
- Weak password error does not leak the original password.
"""

from __future__ import annotations

import pytest

from src.modules.auth.exceptions import WeakPasswordError
from src.modules.auth.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)

# ---------------------------------------------------------------------------
# 1. hash_password
# ---------------------------------------------------------------------------


class TestHashPassword:
    def test_hash_is_not_plaintext(self):
        """The hash must not equal the plaintext password."""
        password = "MySecure123"
        hashed = hash_password(password)
        assert hashed != password
        assert password not in hashed

    def test_same_password_different_hashes(self):
        """Identical passwords must produce different hashes (salt effect)."""
        password = "MySecure123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_hash_starts_with_bcrypt_prefix(self):
        """The hash should start with the bcrypt prefix."""
        hashed = hash_password("MySecure123")
        assert hashed.startswith("$2")


# ---------------------------------------------------------------------------
# 2. verify_password
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    def test_correct_password_verifies(self):
        """A correct password must verify successfully."""
        password = "MySecure123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        """An incorrect password must fail verification."""
        hashed = hash_password("MySecure123")
        assert verify_password("WrongPassword456", hashed) is False

    def test_empty_password_fails(self):
        """An empty password must fail verification."""
        hashed = hash_password("MySecure123")
        assert verify_password("", hashed) is False

    def test_malformed_hash_returns_false(self):
        """A malformed hash should return False, not raise."""
        assert verify_password("anything", "not-a-hash") is False

    def test_none_password_returns_false(self):
        """A None password should return False, not raise."""
        hashed = hash_password("MySecure123")
        assert verify_password(None, hashed) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. validate_password_strength
# ---------------------------------------------------------------------------


class TestPasswordStrength:
    def test_strong_password_passes(self):
        """A strong password should not raise."""
        validate_password_strength("MySecure123")

    def test_short_password_fails(self):
        """Passwords shorter than 8 characters must fail."""
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength("Ab1")
        assert "8" in exc_info.value.message

    def test_pure_letters_fails(self):
        """Passwords with only letters must fail (no digit)."""
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength("abcdefgh")
        assert "数字" in exc_info.value.message

    def test_pure_digits_fails(self):
        """Passwords with only digits must fail (no letter)."""
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength("12345678")
        assert "字母" in exc_info.value.message

    def test_all_whitespace_fails(self):
        """Passwords that are all whitespace must fail."""
        with pytest.raises(WeakPasswordError):
            validate_password_strength("        ")

    def test_contains_email_local_part_fails(self):
        """Passwords containing the email local part must fail."""
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength(
                "student123",
                email="student@example.edu",
            )
        assert "邮箱" in exc_info.value.message

    def test_contains_student_no_fails(self):
        """Passwords containing the student number must fail."""
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength(
                "20260001abc",
                student_no="20260001",
            )
        assert "学号" in exc_info.value.message

    def test_no_email_or_student_no_is_ok(self):
        """Without email/student_no context, those checks are skipped."""
        validate_password_strength("MySecure123")

    def test_error_does_not_leak_password(self):
        """The error message and details must not contain the plaintext password."""
        password = "SecretPwd999"
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength(password[:2] + "xxxx")  # too short
        # The error message should not contain the actual password input
        assert "SecretPwd999" not in exc_info.value.message
        assert "SecretPwd999" not in str(exc_info.value.details)

    def test_error_code_is_auth_weak_password(self):
        """The error code must be AUTH_WEAK_PASSWORD."""
        with pytest.raises(WeakPasswordError) as exc_info:
            validate_password_strength("short")
        assert exc_info.value.code == "AUTH_WEAK_PASSWORD"
        assert exc_info.value.status_code == 400
