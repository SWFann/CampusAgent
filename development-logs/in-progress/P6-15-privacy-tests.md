# P6-15: Privacy Tests

## Date
2026-07-18

## Task
Comprehensive privacy tests covering A/B isolation, admin rejection, revoke immediate effect, encryption fail-closed, audit no content, and log no content.

## Deliverables

### Privacy Test Suite (`apps/api/tests/unit/test_privacy_memory.py`)

#### TestABIsolation
- A cannot read B's memory (list returns empty).
- A cannot get B's memory by ID (raises MemoryPermissionDeniedError).
- A list returns only A's memories.

#### TestAdminNoContent
- Admin cannot read memory content (no admin memory API exists).
- Admin can read agent metadata but not `private_config_encrypted` value.

#### TestRevokeImmediateEffect
- After consent revoke, agent cannot access memory (raises ConsentDeniedError).

#### TestEncryptionFailClosed
- Missing encryption key raises AppError (key="" → ENCRYPTION_KEY_MISSING).
- Decryption failure with corrupted ciphertext raises AppError.
- Wrong key cannot decrypt data encrypted with different key.

#### TestAuditNoContent
- Audit log for memory_read does not contain plaintext.
- Audit log does not contain encrypted content either.

#### TestLogsNoContent
- Service logs do not contain plaintext markers.

### Key Fixes Applied
- Fixed `test_wrong_key_cannot_decrypt` to directly inject a different key into the encryption service singleton instead of relying on env var changes (pydantic settings is loaded at import time).

## Status
Complete.
