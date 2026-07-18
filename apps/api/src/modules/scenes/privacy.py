"""Privacy utilities for the scenes module.

Responsibilities:
- Encrypt/decrypt private submission payloads using the shared Fernet
  EncryptionService.
- Validate that capsules do not contain sensitive free-text fields.
- Ensure private data never leaks into logs, events, or API responses.

Privacy principles (P8 guide §7):
- PrivateSubmission.encrypted_payload is Fernet ciphertext; plaintext is
  never stored, logged, or returned.
- capsule_json is a minimised derivative — hard constraints, soft
  preferences, weights — NOT raw input.
- The response (PrivateSubmissionResponse) never echoes the raw payload.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, cast

from ..memories.encryption import get_encryption_service
from .schemas import PrivateCapsule

logger = logging.getLogger("campus_agent.scenes.privacy")

# Fields that must NEVER appear in a capsule (they indicate raw/identifiable
# data that should have been reduced to constraints/preferences).
_FORBIDDEN_CAPSULE_KEYS: frozenset[str] = frozenset(
    {
        "raw_text",
        "raw_input",
        "plaintext",
        "content",
        "message",
        "email",
        "phone",
        "student_no",
        "name",
        "address",
        "id_card",
        "password",
        "token",
    }
)

# Maximum capsule size in bytes (prevents exfiltration via oversized capsule).
_MAX_CAPSULE_BYTES = 8192


def encrypt_payload(raw_preferences: dict[str, Any]) -> str:
    """Encrypt raw preferences into a Fernet ciphertext string.

    The plaintext is serialised to JSON before encryption. The original
    dict is not retained after this call.
    """
    enc = get_encryption_service()
    plaintext = json.dumps(raw_preferences, sort_keys=True, ensure_ascii=False)
    return enc.encrypt(plaintext)


def decrypt_payload(ciphertext: str) -> dict[str, Any]:
    """Decrypt a Fernet ciphertext back to the original preferences dict.

    This is only called by the coordinator during candidate generation,
    within the owning user's context. The decrypted value is never
    persisted or logged.
    """
    enc = get_encryption_service()
    plaintext = enc.decrypt(ciphertext)
    return cast("dict[str, Any]", json.loads(plaintext))


def hash_payload(raw_preferences: dict[str, Any]) -> str:
    """Compute a SHA-256 hash of the raw preferences for dedup/integrity."""
    blob = json.dumps(raw_preferences, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate_capsule(capsule: PrivateCapsule) -> None:
    """Validate that a capsule does not contain forbidden sensitive fields.

    Raises:
        ValueError: If a forbidden key is found or the capsule is too large.
    """
    # Check all dict fields for forbidden keys.
    for field_name in ("hard_constraints", "soft_preferences"):
        field_dict = getattr(capsule, field_name)
        _check_forbidden_keys(field_dict, field_name)

    # Check serialised size.
    serialised = capsule.model_dump_json()
    if len(serialised.encode("utf-8")) > _MAX_CAPSULE_BYTES:
        raise ValueError(
            f"Capsule exceeds maximum size of {_MAX_CAPSULE_BYTES} bytes"
        )


def _check_forbidden_keys(data: dict[str, Any], field_name: str) -> None:
    """Recursively check for forbidden keys in a dict."""
    for key, value in data.items():
        if key.lower() in _FORBIDDEN_CAPSULE_KEYS:
            raise ValueError(
                f"Forbidden key '{key}' found in capsule field '{field_name}'"
            )
        if isinstance(value, dict):
            _check_forbidden_keys(value, field_name)


def sanitise_log_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Strip any private/sensitive keys from a dict before logging.

    This is a defence-in-depth measure — logs should never contain raw
    preferences, capsules, or individual scores.
    """
    sensitive_keys = _FORBIDDEN_CAPSULE_KEYS | frozenset(
        {"preferences", "capsule", "encrypted_payload", "individual_score",
         "evaluation", "evaluations"}
    )
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = sanitise_log_dict(value)
        else:
            result[key] = value
    return result


def capsule_to_json(capsule: PrivateCapsule) -> str:
    """Serialise a capsule to JSON for storage (capsule_json column)."""
    return capsule.model_dump_json()


def capsule_from_json(capsule_json: str) -> PrivateCapsule:
    """Deserialise a capsule from JSON."""
    return PrivateCapsule.model_validate_json(capsule_json)
