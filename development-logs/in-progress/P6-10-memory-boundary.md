# P6-10: Memory Service Boundary Enforcement

## Date
2026-07-18

## Task
Implement architecture test to prevent modules from bypassing Memory Service by directly importing MemoryRepository or ConsentRepository.

## Deliverables

### Architecture Test (`apps/api/tests/unit/test_memory_boundary.py`)
- Scans all Python files under `apps/api/src/modules/`.
- Asserts that no module outside `modules/memories/` imports `MemoryRepository` or `ConsentRepository`.
- Allows `modules/memories/service.py` and `modules/memories/consent.py` to import repositories.
- Allows test files to import repositories.

### Tests (`test_memory_boundary.py`)
- 6 tests: no external MemoryRepository import, no external ConsentRepository import, memories service allowed, memories consent allowed, memories cleanup allowed, audit service does not import memory repo.

## Status
Complete.
