# P6-09: Memory Query Policy

## Date
2026-07-18

## Task
Implement and test memory query policy ensuring all access checks are enforced.

## Deliverables

### Query Policy Enforcement (`apps/api/src/modules/memories/service.py`)
All memory queries must match:
- **owner**: memory belongs to the requesting user, OR valid consent exists.
- **agent**: if accessing via agent, agent_id must match consent's grantee.
- **purpose**: must match consent's purpose.
- **category/scope**: must match consent's scope if specified.
- **active consent**: consent must be granted, not expired, not revoked.
- **not expired**: memory's `expires_at` must be in the future or None.
- **not deleted**: memory's `deleted_at` must be None.

### Tests (`test_memory_query_policy.py`)
- 8 tests: A cannot query B's memory, A's agent cannot query with wrong purpose, revoke immediately blocks access, expired memory excluded, deleted memory excluded, consent with category scope, consent with wrong category denied, owner bypasses consent check.

## Status
Complete.
