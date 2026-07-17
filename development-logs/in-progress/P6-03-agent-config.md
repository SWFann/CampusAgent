# P6-03: Agent Configuration API

## Date
2026-07-18

## Task
Implement agent configuration REST API endpoints with owner-only write and admin metadata-only read.

## Deliverables

### API Endpoints (`apps/api/src/modules/agents/api.py`)
- `GET /api/v1/agents/me` — list current user's agents.
- `GET /api/v1/agents/{agent_id}` — get agent by ID.
- `PATCH /api/v1/agents/{agent_id}` — update agent configuration.

### Permission Rules
- Owner can read and write their own agents.
- Non-owner cannot read private config.
- Admin can only read metadata, NOT `private_config_encrypted`.
- Response includes `has_private_config` boolean, not the encrypted value.

### Tests (`test_agent_config.py`)
- 11 tests: get own agent, get by ID, update name/avatar/persona, update private config, non-owner denied, admin sees metadata only, L4 delegation rejected.

## Status
Complete.
