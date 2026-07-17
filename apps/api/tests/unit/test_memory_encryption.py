"""P6-05: Field encryption service tests.

Tests:
- encrypt/decrypt roundtrip.
- Wrong key fails decryption.
- Ciphertext does not contain plaintext.
- Logs do not contain ciphertext or plaintext.
- Missing key raises AppError (fail-closed).
- key_version is exposed.
"""
from __future__ import annotations

import logging

import pytest

from src.modules.memories.encryption import EncryptionService
from src.utils.errors import AppError


class TestEncryptionService:
    """Test the EncryptionService."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypt then decrypt returns original plaintext."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        plaintext = "my secret preference"
        ciphertext = enc.encrypt(plaintext)
        assert ciphertext != plaintext
        decrypted = enc.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_wrong_key_fails(self) -> None:
        """Decryption with wrong key raises AppError."""
        enc1 = EncryptionService(key="key-one-for-encryption")
        enc2 = EncryptionService(key="key-two-different-key")
        ciphertext = enc1.encrypt("secret data")
        with pytest.raises(AppError) as exc_info:
            enc2.decrypt(ciphertext)
        assert exc_info.value.code == "DECRYPTION_FAILED"

    def test_ciphertext_no_plaintext(self) -> None:
        """Ciphertext does not contain the plaintext string."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        plaintext = "unique-plaintext-marker-12345"
        ciphertext = enc.encrypt(plaintext)
        assert plaintext not in ciphertext
        assert "unique-plaintext-marker" not in ciphertext

    def test_log_no_ciphertext_or_plaintext(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logs must not contain ciphertext or plaintext."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        plaintext = "log-test-plaintext-marker"
        ciphertext = enc.encrypt(plaintext)

        with caplog.at_level(logging.DEBUG, logger="campus_agent.encryption"):
            enc.encrypt(plaintext)
            enc.decrypt(ciphertext)

        for record in caplog.records:
            assert plaintext not in record.getMessage()
            assert ciphertext not in record.getMessage()

    def test_missing_key_raises(self) -> None:
        """Missing encryption key raises AppError (fail-closed)."""
        with pytest.raises(AppError) as exc_info:
            EncryptionService(key="")
        assert exc_info.value.code == "ENCRYPTION_KEY_MISSING"

    def test_key_version_exposed(self) -> None:
        """key_version is available."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        assert enc.key_version == 1

    def test_hash_content(self) -> None:
        """hash_content returns SHA-256 hex digest."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        h = enc.hash_content("test content")
        assert len(h) == 64  # SHA-256 hex = 64 chars
        assert h == enc.hash_content("test content")  # Deterministic
        assert h != enc.hash_content("different content")

    def test_different_plaintext_different_ciphertext(self) -> None:
        """Same plaintext produces different ciphertext (Fernet uses random IV)."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        c1 = enc.encrypt("same text")
        c2 = enc.encrypt("same text")
        assert c1 != c2  # Fernet adds random IV
        assert enc.decrypt(c1) == enc.decrypt(c2)

    def test_decrypt_corrupted_fails(self) -> None:
        """Corrupted ciphertext raises AppError."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        with pytest.raises(AppError):
            enc.decrypt("not-a-valid-fernet-token")

    def test_encrypt_empty_string(self) -> None:
        """Empty string can be encrypted and decrypted."""
        enc = EncryptionService(key="test-encryption-key-for-p6-tests")
        ciphertext = enc.encrypt("")
        assert enc.decrypt(ciphertext) == ""
