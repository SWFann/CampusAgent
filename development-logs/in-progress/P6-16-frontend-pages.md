# P6-16: Frontend Pages

## Date
2026-07-18

## Task
Implement frontend pages for agent management, memory/consent management, and audit log viewing.

## Deliverables

### API Client Libraries
- `apps/web/src/lib/agents.ts`: getAgents, getAgent, updateAgent functions.
- `apps/web/src/lib/memories.ts`: createMemory, listMemories, getMemory, updateMemory, deleteMemory, grantConsent, revokeConsent, listConsents functions.
- `apps/web/src/lib/audit.ts`: getAuditLogs function.

### Pages
- `apps/web/src/app/agents/page.tsx`: Agent management page — view agent info, edit name/avatar/persona, view delegation level, private config indicator (boolean only).
- `apps/web/src/app/memories/page.tsx`: Memory and consent management page — list memories (decrypted for owner), create/update/delete memories, grant/revoke consents.
- `apps/web/src/app/audit/page.tsx`: Audit log viewer — list own audit entries (metadata only, no content).

### Privacy Requirements
- No memory content stored in localStorage/sessionStorage.
- No token, private preference, or memory content in URL.
- Admin pages do not display user private preference content.
- All API calls use authenticated fetch with credentials.

### Build Verification
- All 3 pages successfully built as static routes in Next.js production build.
- ESLint and TypeScript type checking pass.

## Status
Complete.
