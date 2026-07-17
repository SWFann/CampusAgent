# P5-01: Conversation Data Model

## Date
2026-07-17

## Task
Design and implement the conversation data model (Conversation, ConversationParticipant, Message), Alembic migration 0004, and update conftest/tests.

## Deliverables

### ORM Models (`apps/api/src/modules/conversations/models.py`)
- `Conversation`: type (PRIVATE/GROUP/ORG_GROUP/SCENE), title, organization_id, created_by, status, timestamps, soft-delete.
- `ConversationParticipant`: conversation_id, participant_type (USER/AGENT), participant_user_id, participant_agent_id, role (OWNER/ADMIN/MEMBER/GUEST), status (ACTIVE/LEFT/REMOVED), timestamps.
- `Message`: conversation_id, sender_type (USER/AGENT/SYSTEM), sender_user_id, sender_agent_id, message_type (TEXT/IMAGE/FILE/SYSTEM/AGENT_PUBLIC/SCENE_CARD/VOTE/PROPOSAL/RESULT/PRIVACY_NOTICE), content, payload_json, idempotency_key, status, sequence, timestamps, soft-delete.

### Key Privacy Features
- `Message.__repr__` does NOT output content or payload_json.
- `Conversation.__repr__` does NOT output title.
- Deleted messages have DELETED status and deleted_at set; API responses will return empty content.

### Alembic Migration (`apps/api/alembic/versions/0004_conversation_message_tables.py`)
- `down_revision` = `0003_org_member` (P4).
- Creates `conversations`, `conversation_participants`, `messages` tables.
- Indexes: conversation type/status/org_id, participant conversation/user/status, message conversation/created_at/idempotency_key/status + composite index.
- Unique constraint on participants: (conversation_id, participant_type, participant_user_id, participant_agent_id).

### Test Updates
- `conftest.py`: Added imports for Conversation, ConversationParticipant, Message so `Base.metadata.create_all()` registers them.
- `test_alembic.py`: Added P5 table assertions in existing tests + new `TestP5ConversationTables` class.
- `test_conversation_models.py`: New unit tests for all models.

## Status
Complete.
