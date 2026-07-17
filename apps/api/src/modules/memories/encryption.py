"""Field encryption service for CampusAgent memories.

Uses Fernet authenticated encryption (AES-128-CBC + HMAC-SHA256).
Supports key versioning. Fail-closed on missing key or decryption failure.

Privacy: ciphertext and plaintext never appear in logs.
"""
from __future__ import annotations

import hashlib
import logging

from cryptography.fernet import Fernet  # type: ignore[import-not-found]

from ...config import settings
from ...utils.errors import AppError

logger = logging.getLogger("campus_agent.encryption")

# Key version 1 — derive Fernet key from FIELD_ENCRYPTION_KEY
_KEY_VERSION = 1


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a 32-byte Fernet key from an arbitrary-length string.

    SHA-256 always produces 32 bytes, which is exactly what Fernet needs
    after URL-safe base64 encoding.
    """
    import base64

    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class EncryptionService:
    """Field-level encryption service using Fernet.

    Fail-closed: missing key or decryption failure raises AppError.
    """

    def __init__(self, key: str | None = None) -> None:
        raw_key = key if key is not None else settings.FIELD_ENCRYPTION_KEY.get_secret_value()
        if not raw_key:
            raise AppError(
                code="ENCRYPTION_KEY_MISSING",
                message="Field encryption key is not configured",
                status_code=500,
            )
        self._fernet = Fernet(_derive_fernet_key(raw_key))
        self._key_version = _KEY_VERSION

    @property
    def key_version(self) -> int:
        """Return the current encryption key version."""
        return self._key_version

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return a ciphertext string.

        Args:
            plaintext: The plaintext to encrypt.

        Returns:
            A Fernet token string (ciphertext).

        Raises:
            AppError: If encryption fails.
        """
        try:
            token = self._fernet.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as exc:
            logger.error("encryption.encrypt.failed", extra={"error": str(exc)})
            raise AppError(
                code="ENCRYPTION_FAILED",
                message="Failed to encrypt data",
                status_code=500,
            ) from None

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a ciphertext string and return plaintext.

        Args:
            ciphertext: The Fernet token string.

        Returns:
            The decrypted plaintext string.

        Raises:
            AppError: If decryption fails (wrong key, corrupted data, etc.).
        """
        try:
            plaintext = self._fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext.decode("utf-8")
        except Exception as exc:
            logger.error("encryption.decrypt.failed", extra={"error": str(exc)})
            raise AppError(
                code="DECRYPTION_FAILED",
                message="Failed to decrypt data",
                status_code=500,
            ) from None

    def hash_content(self, plaintext: str) -> str:
        """Compute SHA-256 hash of plaintext for dedup/comparison."""
        return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


# Singleton instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get the singleton EncryptionService instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def reset_encryption_service() -> None:
    """Reset the singleton (for testing)."""
    global _encryption_service
    _encryption_service = None
