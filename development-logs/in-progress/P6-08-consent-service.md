# P6-08: Consent Service

## Date
2026-07-18

## Task
Implement consent management service with grant, check, revoke, and expire operations.

## Deliverables

### Consent Service (`apps/api/src/modules/memories/consent.py`)
- `grant_consent(grantor_id, agent_id, purpose, session, scope=None, expires_at=None)`: creates a ConsentRecord.
- `check_consent(grantor_id, agent_id, purpose, session, category=None)`: returns True if active consent exists.
- `revoke_consent(grantor_id, consent_id, session)`: sets `revoked_at`, immediately effective.
- `list_consents(grantor_id, session)`: lists all consents for a user.
- Audit logging for grant and revoke operations.

### Check Logic
- Consent must be `granted=True`.
- Consent must not be expired (`expires_at` > now or None).
- Consent must not be revoked (`revoked_at` is None).
- Purpose must match.
- Category scope must match if specified.

### Tests (`test_consent_service.py`)
- 16 tests: grant then check true, revoked then false, expired then false, wrong purpose false, wrong category false, list consents, revoke by ID, grant with scope, grant with expiry, audit on grant, audit on revoke, duplicate grant, revoke already revoked, consent isolation A/B, check non-existent, grant with scene scope.

## Status
Complete.
