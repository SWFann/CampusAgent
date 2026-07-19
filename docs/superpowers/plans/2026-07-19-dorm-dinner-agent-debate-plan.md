# Dorm Dinner Agent Debate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace flat dorm dinner recommendation summaries with a hosted, visible multi-agent debate transcript and grounded final vote candidates.

**Architecture:** Extend the StepFun dinner adapter schema to parse hosted debate output, then persist and publish that transcript through the existing chat-native scene flow. Keep final candidate groundedness checks as the anti-fake boundary, while exposing demo-friendly preference reasoning in public debate turns.

**Tech Stack:** Python 3.11, FastAPI service modules, Pydantic models, SQLAlchemy scene models, Next.js/React TypeScript UI, Jest, Pytest.

---

### Task 1: Backend Debate Schema

**Files:**
- Modify: `apps/api/src/modules/scenes/dinner_search.py`
- Test: `apps/api/tests/unit/test_dinner_search.py`

- [ ] **Step 1: Write failing parser tests**

Add tests that return a model JSON object with `opening`, `agent_proposals`, `rounds`, `coordinator_summary`, and grounded `candidates`. Assert the parsed result exposes these fields and still rejects candidates whose source URLs are not in search evidence.

- [ ] **Step 2: Run tests to verify failure**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_dinner_search.py -q -p no:cacheprovider`

Expected: failure because `NegotiationResult` has no hosted debate fields.

- [ ] **Step 3: Implement schema**

Add Pydantic models for proposals, debate turns, debate rounds, and final candidates. Update `StepFunDinnerProvider.negotiate` prompt and parsing to produce a structured debate transcript while preserving evidence URL validation.

- [ ] **Step 4: Run tests to verify pass**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_dinner_search.py -q -p no:cacheprovider`

Expected: pass.

### Task 2: Chat Scene Persistence And Messages

**Files:**
- Modify: `apps/api/src/modules/scenes/chat_dorm_dinner.py`
- Test: `apps/api/tests/unit/test_chat_dorm_dinner.py`

- [ ] **Step 1: Write failing chat-status test**

Add a mocked `StepFunDinnerProvider` result with opening, agent proposals, two debate turns, host summary, and coordinator summary. Assert `run_debate` persists `debate_turns` containing phase labels and publishes public messages for each visible step.

- [ ] **Step 2: Run tests to verify failure**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: failure because current `run_debate` only flattens `negotiation.agents`.

- [ ] **Step 3: Implement transcript flattening**

Convert the structured debate result into `public_context_json.debate_turns` entries with `phase`, `round`, `speaker`, `content`, `search_summary`, `source_urls`, and `proposals`. Publish chat messages for host opening, agent proposals, debate turns, host summaries, and coordinator summary.

- [ ] **Step 4: Run tests to verify pass**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: pass.

### Task 3: Frontend Transcript Types And Modal Rendering

**Files:**
- Modify: `apps/web/src/lib/dormDinnerChat.ts`
- Modify: `apps/web/src/app/conversations/[conversationId]/page.tsx`
- Test: `apps/web/tests/unit/dorm-dinner-chat.test.ts`

- [ ] **Step 1: Write failing UI helper test**

Add a test that imports a debate grouping helper and asserts proposal, debate, host summary, and coordinator summary turns are grouped into scan-friendly sections.

- [ ] **Step 2: Run test to verify failure**

Run: `corepack pnpm --filter @campus-agent/web test -- dorm-dinner-chat.test.ts --runInBand`

Expected: failure because no grouping helper exists.

- [ ] **Step 3: Implement types and rendering**

Extend `DormDinnerDebateTurn` with `phase` and `proposals`. Add a grouping helper. Update the modal to render host opening, each agent proposal list, debate rounds, host summaries, and final coordinator summary with labels.

- [ ] **Step 4: Run test to verify pass**

Run: `corepack pnpm --filter @campus-agent/web test -- dorm-dinner-chat.test.ts --runInBand`

Expected: pass.

### Task 4: Verification, Runtime, Commit

**Files:**
- Verify all touched files.

- [ ] **Step 1: Run focused tests**

Run backend and frontend focused tests from Tasks 1-3.

- [ ] **Step 2: Run full checks**

Run:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

- [ ] **Step 3: Smoke test runtime**

Restart local services if needed and verify:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health/ready
```

- [ ] **Step 4: Commit and push**

Commit implementation changes and push to `main`.
