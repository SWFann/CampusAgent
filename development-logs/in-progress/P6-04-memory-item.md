# P6-04: MemoryItem Model

## Date
2026-07-18

## Task
Design and implement the MemoryItem ORM model with encrypted content, TTL, and soft delete.

## Deliverables

### ORM Model (`apps/api/src/modules/memories/models.py`)
- `MemoryItem`: id, owner_user_id, agent_id, category, sensitivity_level, source, content_encrypted, content_hash, encryption_key_version, expires_at, deleted_at, timestamps.

### Key Privacy Features
- `content_encrypted` stores Fernet ciphertext, never plaintext.
- `content_hash` stores SHA-256 hash for dedup/comparison.
- `expires_at` supports TTL-based expiration.
- `deleted_at` supports soft delete.
- `__repr__` does NOT output `content_encrypted` or any content-related fields.

### Tests (`test_memory_models.py`)
- 12 tests: content_encrypted required, content_hash set, expires_at nullable, soft delete, repr privacy, timestamps, sensitivity_level, source.

## Status
Complete.
