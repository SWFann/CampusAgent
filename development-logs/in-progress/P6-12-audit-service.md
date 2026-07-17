# P6-12: Audit Write and Query Service

## Date
2026-07-18

## Task
Implement audit logging service with automatic write on sensitive operations and user-facing query API.

## Deliverables

### Audit Service (`apps/api/src/modules/audit/service.py`)
- `log_audit(actor_id, action, resource_type, resource_id, purpose, result, session, metadata=None)`: writes audit log entry.
- `list_audit_logs(actor_id, session, limit, offset)`: returns user's own audit logs.

### Automatic Audit Points
- **memory_read**: logged on every memory get (SUCCESS or DENIED).
- **memory_write**: logged on memory create.
- **memory_delete**: logged on memory soft-delete.
- **consent_grant**: logged on consent grant.
- **consent_revoke**: logged on consent revoke.
- **agent_config_update**: logged on agent PATCH.

### API Endpoint (`apps/api/src/modules/audit/api.py`)
- `GET /api/v1/audit/me` — returns current user's audit logs only.

### Tests (in `test_audit_logs.py` and `test_privacy_memory.py`)
- Audit log creation, user isolation, no plaintext in metadata, no encrypted content in metadata.

## Status
Complete.
