# Dorm Dinner Chat Scene Redesign Plan

> **For agentic workers:** implement this as a vertical product slice. Preserve privacy boundaries: raw private preferences never appear in chat messages, logs, prompts, or public results.

**Goal:** turn the dorm dinner scene into a chat-native group workflow: members join/skip, submit private preferences, watch group status, run bounded agent debate, then vote on final options.

**Current State**
- Conversations already support group chat and messages.
- Scene APIs exist under `/api/v1/scenes/dorm_dinner/*`.
- The current dorm dinner UI is a standalone page, not chat-native.
- StepFun model provider is available through the model gateway when `ENABLE_EXTERNAL_MODEL=true`.
- WebSocket realtime exists for conversation events.

**Target Product Flow**
1. A user opens a group conversation.
2. User clicks “发起宿舍聚餐”.
3. A scene card appears in the group chat.
4. Each member chooses “参与” or “不参与”.
5. Participating members submit private preferences.
6. The chat card shows:
   - participating count
   - skipped count
   - submitted count
   - current phase
   - max debate rounds
7. When all participating members submit, the scene enters reasoning.
8. A coordinator agent runs up to `max_rounds` debate turns with participant agents.
9. The group chat shows public debate progress only.
10. The system creates 2-4 public candidate plans.
11. Members vote in chat.
12. The winning plan is shown as a final chat card.

**Data Model Direction**
- Reuse `SceneInstance`, `SceneParticipant`, `PrivateSubmission`, `SceneCandidate`, `SceneVote`, `SceneResult`.
- Bind the dorm dinner scene to a `conversation_id`.
- Add lightweight debate persistence if missing:
  - debate session id
  - max rounds
  - current round
  - status
  - public transcript messages

**Backend Tasks**

## Task 1: Conversation-bound Dorm Dinner API

Add or extend endpoints:
```text
POST /api/v1/scenes/conversations/{conversation_id}/dorm_dinner
GET  /api/v1/scenes/conversations/{conversation_id}/dorm_dinner
POST /api/v1/scenes/conversations/{conversation_id}/dorm_dinner/participation
POST /api/v1/scenes/conversations/{conversation_id}/dorm_dinner/preferences
POST /api/v1/scenes/conversations/{conversation_id}/dorm_dinner/debate/start
GET  /api/v1/scenes/conversations/{conversation_id}/dorm_dinner
POST /api/v1/scenes/conversations/{conversation_id}/dorm_dinner/votes
```

Rules:
- Only active conversation participants can read or write the scene.
- Only accepted participating users can submit preferences.
- Users who choose not to participate are excluded from readiness checks.
- Private preferences are encrypted through existing scene submission flow.
- Public chat messages may contain state, counts, candidates, and debate summaries only.

## Task 2: Status Card Contract

Return a stable object:
```json
{
  "scene_id": "uuid",
  "conversation_id": "uuid",
  "phase": "COLLECTING_PRIVATE_INPUT",
  "participant_count": 3,
  "joined_count": 2,
  "skipped_count": 1,
  "submitted_count": 2,
  "ready_for_debate": true,
  "max_rounds": 3,
  "current_round": 0,
  "candidates": [],
  "votes": [],
  "result": null
}
```

## Task 3: Debate Orchestration

Implement a bounded debate service:
- Input: de-identified preference capsules and public restaurant candidates.
- Agent roles:
  - coordinator agent
  - one participant proxy agent per participating user
- Loop:
  - for round `1..max_rounds`
  - each participant agent gives public argument/preferences summary
  - coordinator updates ranking and asks next question
  - stop early if ranking stabilizes for 2 consecutive rounds
- Output:
  - public debate turns
  - candidate list
  - public reasons

Privacy:
- No raw notes.
- No raw budgets tied to names.
- No participant identity in model prompt beyond anonymous labels such as `成员A`.

## Task 4: Chat Message Integration

Write system messages into the conversation:
- scene created
- participant joined/skipped
- preference submitted count updated
- debate started
- round completed
- candidates ready
- vote cast
- result confirmed

Message types:
- `SCENE_CARD` for current state
- `AGENT_PUBLIC` for public debate turns
- `RESULT` for final decision

## Task 5: Frontend Chat Card

Modify `apps/web/src/app/conversations/[conversationId]/page.tsx`:
- Add “发起宿舍聚餐” button for group conversations.
- Render a rich scene card when dorm dinner state exists.
- Let members:
  - participate
  - skip
  - submit preferences
  - set max rounds before debate starts
  - start debate when ready
  - vote for candidates

Keep it Chinese-first and demo-friendly.

**Verification**

Backend:
```bash
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests/unit apps/api/tests/integration -q -p no:cacheprovider
```

Frontend:
```bash
corepack pnpm --filter @campus-agent/web typecheck
corepack pnpm --filter @campus-agent/web lint
corepack pnpm --filter @campus-agent/web test -- --runInBand
corepack pnpm --filter @campus-agent/web build
```

Manual:
1. Login as Alice.
2. Open a group conversation.
3. Start dorm dinner.
4. Login Bob in another browser profile.
5. Bob joins and submits preferences.
6. Alice submits preferences.
7. Start debate with max rounds 3.
8. Confirm candidates appear in chat.
9. Both users vote.
10. Final result appears.
