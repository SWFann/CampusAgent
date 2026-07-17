# P6-01: Agent Model Design

## Date
2026-07-18

## Task
Design and implement the Agent and AgentRun ORM models, Pydantic schemas, Alembic migration 0005, and model tests.

## Deliverables

### ORM Models (`apps/api/src/modules/agents/models.py`)
- `Agent`: id, owner_user_id, type (PERSONAL/GROUP/ORG), name, avatar_url, public_persona, private_config_encrypted, delegation_level (L0-L3, L4 disabled in P6), status, timestamps.
- `AgentRun`: id, agent_id, actor_user_id, purpose, input_hash, output_hash, model_name, token_count, latency_ms, status, timestamps.

### Key Privacy Features
- `Agent.__repr__` does NOT output `private_config_encrypted`.
- `AgentRun.__repr__` only outputs hashes, not prompt/response content.
- Delegation level L4 is rejected at the model level.

### Alembic Migration (`apps/api/alembic/versions/0005_agent_memory_consent_audit_tables.py`)
- `down_revision` = `0004_conversation_message` (P5).
- Creates `agents` and `agent_runs` tables.
- Indexes: agent owner/type/status, agent_run agent_id/created_at.

### Tests (`test_agent_models.py`)
- 15 tests: personal agent creation, owner required, L0-L3 valid, L4 rejected, repr privacy, timestamps.

## Status
Complete.
