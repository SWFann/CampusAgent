"""P8-04: Scene privacy utilities tests.

Tests:
- encrypt/decrypt round-trip.
- hash_payload produces consistent hashes.
- validate_capsule rejects forbidden keys.
- validate_capsule rejects oversized capsules.
- sanitise_log_dict strips sensitive keys.
- capsule_to_json / capsule_from_json round-trip.
"""
from __future__ import annotations

import pytest

from src.modules.scenes.privacy import (
    capsule_from_json,
    capsule_to_json,
    decrypt_payload,
    encrypt_payload,
    hash_payload,
    sanitise_log_dict,
    validate_capsule,
)
from src.modules.scenes.schemas import PrivateCapsule


class TestPayloadEncryption:
    """Test payload encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypt and decrypt should return the original data."""
        raw = {"require_vegetarian": True, "prefer_spicy": 3}
        ciphertext = encrypt_payload(raw)
        assert ciphertext != str(raw)  # ciphertext is not plaintext
        assert "require_vegetarian" not in ciphertext  # no plaintext in ciphertext

        decrypted = decrypt_payload(ciphertext)
        assert decrypted == raw

    def test_encrypt_produces_different_ciphertexts(self) -> None:
        """Each encryption should produce a different ciphertext (Fernet IV)."""
        raw = {"key": "value"}
        ct1 = encrypt_payload(raw)
        ct2 = encrypt_payload(raw)
        assert ct1 != ct2  # Fernet uses random IV

    def test_hash_payload_consistent(self) -> None:
        """Same input produces same hash."""
        raw = {"a": 1, "b": 2}
        h1 = hash_payload(raw)
        h2 = hash_payload(raw)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_hash_payload_different_for_different_input(self) -> None:
        """Different input produces different hash."""
        h1 = hash_payload({"a": 1})
        h2 = hash_payload({"a": 2})
        assert h1 != h2

    def test_hash_payload_order_independent(self) -> None:
        """Hash is order-independent (sorted keys)."""
        h1 = hash_payload({"a": 1, "b": 2})
        h2 = hash_payload({"b": 2, "a": 1})
        assert h1 == h2


class TestCapsuleValidation:
    """Test capsule validation."""

    def test_valid_capsule_passes(self) -> None:
        """A capsule with only allowed keys passes validation."""
        capsule = PrivateCapsule(
            hard_constraints={"require_vegetarian": True},
            soft_preferences={"prefer_spicy": 3},
            weights={"taste": 0.5},
        )
        validate_capsule(capsule)  # should not raise

    def test_capsule_with_raw_text_rejected(self) -> None:
        """A capsule with 'raw_text' key is rejected."""
        capsule = PrivateCapsule(
            hard_constraints={"raw_text": "sensitive data"},
        )
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_capsule_with_email_rejected(self) -> None:
        """A capsule with 'email' key is rejected."""
        capsule = PrivateCapsule(
            soft_preferences={"email": "user@example.com"},
        )
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_capsule_with_nested_forbidden_key_rejected(self) -> None:
        """A capsule with forbidden key in nested dict is rejected."""
        capsule = PrivateCapsule(
            hard_constraints={"metadata": {"phone": "1234567890"}},
        )
        with pytest.raises(ValueError, match="Forbidden key"):
            validate_capsule(capsule)

    def test_oversized_capsule_rejected(self) -> None:
        """A capsule exceeding the size limit is rejected."""
        large_data = {f"key_{i}": "x" * 100 for i in range(200)}
        capsule = PrivateCapsule(hard_constraints=large_data)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            validate_capsule(capsule)

    def test_capsule_json_roundtrip(self) -> None:
        """capsule_to_json and capsule_from_json round-trip correctly."""
        original = PrivateCapsule(
            hard_constraints={"a": 1},
            soft_preferences={"b": 2},
            weights={"c": 0.5},
        )
        json_str = capsule_to_json(original)
        restored = capsule_from_json(json_str)
        assert restored.hard_constraints == original.hard_constraints
        assert restored.soft_preferences == original.soft_preferences
        assert restored.weights == original.weights


class TestLogSanitisation:
    """Test log dictionary sanitisation."""

    def test_sanitise_strips_preferences(self) -> None:
        """sanitise_log_dict strips 'preferences' key."""
        data = {"preferences": {"secret": "data"}, "status": "ok"}
        sanitised = sanitise_log_dict(data)
        assert sanitised["preferences"] == "[REDACTED]"
        assert sanitised["status"] == "ok"

    def test_sanitise_strips_capsule(self) -> None:
        """sanitise_log_dict strips 'capsule' key."""
        data = {"capsule": {"hard_constraints": {}}, "count": 5}
        sanitised = sanitise_log_dict(data)
        assert sanitised["capsule"] == "[REDACTED]"
        assert sanitised["count"] == 5

    def test_sanitise_strips_encrypted_payload(self) -> None:
        """sanitise_log_dict strips 'encrypted_payload' key."""
        data = {"encrypted_payload": "abc123", "id": "xyz"}
        sanitised = sanitise_log_dict(data)
        assert sanitised["encrypted_payload"] == "[REDACTED]"

    def test_sanitise_handles_nested_dicts(self) -> None:
        """sanitise_log_dict recurses into nested dicts."""
        data = {"outer": {"inner": "ok", "email": "a@b.com"}, "status": "ok"}
        sanitised = sanitise_log_dict(data)
        assert sanitised["outer"]["email"] == "[REDACTED]"
        assert sanitised["outer"]["inner"] == "ok"

    def test_sanitise_strips_individual_score(self) -> None:
        """sanitise_log_dict strips 'individual_score' key."""
        data = {"individual_score": 0.85, "count": 3}
        sanitised = sanitise_log_dict(data)
        assert sanitised["individual_score"] == "[REDACTED]"
