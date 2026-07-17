# P6-05: Field Encryption Service

## Date
2026-07-18

## Task
Implement Fernet-based field encryption service with key versioning and fail-closed behavior.

## Deliverables

### Encryption Service (`apps/api/src/modules/memories/encryption.py`)
- Uses `cryptography.fernet.Fernet` (AES-128-CBC + HMAC-SHA256).
- Key derived from `FIELD_ENCRYPTION_KEY` via SHA-256 + URL-safe base64.
- Key version tracking (currently version 1).
- `encrypt(plaintext)` → ciphertext string.
- `decrypt(ciphertext)` → plaintext string.
- `hash_content(plaintext)` → SHA-256 hex digest.
- Singleton pattern with `get_encryption_service()` and `reset_encryption_service()`.
- Fail-closed: missing key raises `AppError(ENCRYPTION_KEY_MISSING)`.
- Fail-closed: decryption failure raises `AppError(DECRYPTION_FAILED)`.
- Logs never contain plaintext or ciphertext.

### Key Fix Applied
- Changed `key or settings...` to `key if key is not None else settings...` so that explicitly passing `key=""` raises `ENCRYPTION_KEY_MISSING` instead of falling back to settings.

### Tests (`test_memory_encryption.py`)
- 10 tests: roundtrip, wrong key fails, ciphertext no plaintext, log no content, missing key raises, key version exposed, hash content, different plaintext different ciphertext, corrupted fails, empty string encrypt.

## Status
Complete.
