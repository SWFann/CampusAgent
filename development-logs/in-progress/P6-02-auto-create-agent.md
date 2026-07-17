# P6-02: Auto-Create Personal Agent

## Date
2026-07-18

## Task
Implement event handler that listens for UserRegistered events and auto-creates a personal agent for the new user.

## Deliverables

### Event Handler (`apps/api/src/modules/agents/handlers.py`)
- `PersonalAgentAutoCreateHandler`: listens for `UserRegistered` events.
- Ignores non-UserRegistered events (early return).
- Creates personal agent via `create_personal_agent()` service.
- Idempotent: skips if agent already exists.
- Handler failures are caught and logged — do NOT break registration flow.
- Uses its own DB session (independent from registration transaction).

### Registration Function (`apps/api/src/modules/agents/service.py`)
- `create_personal_agent(user, session)`: creates PERSONAL type agent with L0 delegation.
- Idempotent: checks for existing personal agent before creating.
- `register_personal_agent_handler()`: subscribes handler to `default_event_bus`.

### Tests (`test_agent_personal_creation.py`)
- 5 tests: handler ignores non-UserRegistered, handler failure doesn't raise, handler subscribes to event bus, create is idempotent, created agent is PERSONAL type.

## Status
Complete.
