# P6-14: TTL Cleanup Task

## Date
2026-07-18

## Task
Implement reentrant cleanup task for expired memories and revoked consents.

## Deliverables

### Cleanup Module (`apps/api/src/modules/memories/cleanup.py`)
- `cleanup_expired_memories(session)`: soft-deletes memories where `expires_at` < now and `deleted_at` is None.
- `cleanup_revoked_consents(session)`: removes consents where `revoked_at` is set and older than retention period.
- Reentrant: running multiple times produces the same result as running once.
- Returns counts of affected items.

### Tests (`test_memory_cleanup.py`)
- 9 tests: expired memory soft deleted, active memory not affected, repeated cleanup no-op, revoked consent cleanup, active consent not affected, cleanup returns counts, cleanup with no expired items, cleanup with mixed items, cleanup idempotent.

## Status
Complete.
