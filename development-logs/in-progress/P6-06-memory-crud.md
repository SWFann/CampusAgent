# P6-06: Memory CRUD

## Date
2026-07-18

## Task
Implement Memory CRUD API with owner-only access, encrypted storage, and audit logging.

## Deliverables

### API Endpoints (`apps/api/src/modules/memories/api.py`)
- `POST /api/v1/memories` — create memory.
- `GET /api/v1/memories` — list memories (owner-only, decrypted).
- `GET /api/v1/memories/{memory_id}` — get memory by ID.
- `PATCH /api/v1/memories/{memory_id}` — update memory.
- `DELETE /api/v1/memories/{memory_id}` — soft-delete memory.

### Service Layer (`apps/api/src/modules/memories/service.py`)
- `create_memory()`: encrypts content, stores hash, logs audit.
- `get_memory()`: owner sees decrypted; non-owner needs consent.
- `list_memories()`: owner-only, filters expired and deleted.
- `update_memory()`: owner-only, re-encrypts on content change.
- `delete_memory()`: owner-only, soft-delete.
- `_parse_datetime()`: handles string/datetime for `expires_at`.
- `_ensure_aware()`: normalizes naive datetimes from SQLite for comparison.

### Key Fixes Applied
- Added `_parse_datetime()` to convert ISO string `expires_at` to datetime (SQLite requires datetime objects, not strings).
- Added `_ensure_aware()` to handle SQLite stripping timezone info.
- Added audit logging for memory_write, memory_read, memory_delete.

### Tests (`test_memory_crud.py`)
- 15 tests: create, encrypts content, expiry, get owner, not found, deleted raises, list owner, list by category, list excludes expired, update content, update category, non-owner denied, delete, delete non-owner denied, delete already deleted.

## Status
Complete.
