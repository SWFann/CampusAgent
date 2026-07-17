# P6-07: ConsentRecord Model

## Date
2026-07-18

## Task
Design and implement the ConsentRecord ORM model for tracking user-to-agent authorization grants.

## Deliverables

### ORM Model (`apps/api/src/modules/memories/models.py`)
- `ConsentRecord`: id, grantor_user_id, grantee_agent_id, purpose, scope_json, granted, expires_at, revoked_at, timestamps.

### Purpose Enum
- `chat_reply`: agent can access memories for chat responses.
- `scene_execution`: agent can access memories during scene execution.
- `memory_review`: agent can access memories for review.
- `recommendation`: agent can access memories for recommendations.

### Scope Fields (stored in `scope_json`)
- `category`: restrict to specific memory category.
- `memory_id`: restrict to specific memory.
- `scene_instance_id`: restrict to specific scene instance.
- `expires_at`: additional scope-level expiry.

### Tests (`test_consent_records.py`)
- 10 tests: create consent, purpose values, scope_json, granted default, expires_at, revoked_at, timestamps, repr privacy.

## Status
Complete.
