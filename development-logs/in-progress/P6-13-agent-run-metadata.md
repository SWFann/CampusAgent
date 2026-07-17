# P6-13: AgentRun Metadata

## Date
2026-07-18

## Task
Design and implement AgentRun ORM model storing only metadata (hashes, model, token, latency, status), never prompt or response content.

## Deliverables

### ORM Model (`apps/api/src/modules/agents/models.py`)
- `AgentRun`: id, agent_id, actor_user_id, purpose, input_hash, output_hash, model_name, token_count, latency_ms, status, timestamps.

### Privacy Guarantees
- Only `input_hash` and `output_hash` are stored — never raw input/output.
- `model_name` stores the model identifier used.
- `token_count` stores total tokens consumed.
- `latency_ms` stores execution time.
- `status` stores run result (SUCCESS/FAILED/TIMEOUT).
- `__repr__` only outputs hashes and metadata, never content.

### Tests (`test_agent_run_metadata.py`)
- 8 tests: create run, input_hash only (no input), output_hash only (no output), model_name, token_count, latency_ms, status, repr privacy.

## Status
Complete.
