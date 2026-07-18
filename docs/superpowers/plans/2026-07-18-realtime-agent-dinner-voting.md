# Realtime Agent Dinner Voting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver realtime group messaging and a chat-native, evidence-backed, multi-agent dorm-dinner voting workflow using StepFun search and `step-3.7-flash`.

**Architecture:** Keep the database as the source of truth and route every public scene message through the conversation service so committed writes publish realtime events. Add a server-only StepFun search adapter and a focused dinner negotiation service that stores public, de-identified round memory in scene context while private submissions remain encrypted. Render the scene as an expandable chat message and recover realtime gaps through HTTP snapshots.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, httpx, Redis Pub/Sub, Next.js, React, TypeScript, Jest, pytest.

---

## File map

- `apps/api/src/modules/conversations/service.py`: reusable system-message write path that publishes `MessageCreated` after commit.
- `apps/api/src/modules/scenes/chat_dorm_dinner.py`: conversation-bound scene lifecycle, permissions, public snapshots, voting and memory.
- `apps/api/src/modules/scenes/dinner_search.py`: StepFun `/search` adapter and strict evidence models.
- `apps/api/src/modules/scenes/dinner_negotiation.py`: per-member Agent turns, coordinator summaries and evidence-backed candidates.
- `apps/api/src/modules/scenes/api.py`: typed chat-dinner endpoints, including close and end actions.
- `apps/api/src/config.py` and `.env.example`: server-only search/model configuration.
- `apps/web/src/lib/dormDinnerChat.ts`: typed API client.
- `apps/web/src/app/conversations/[conversationId]/page.tsx`: chat toolbar button, expandable scene message and modal workflow.
- `apps/api/tests/unit/test_chat_dorm_dinner.py`: lifecycle, ownership, memory and public-message tests.
- `apps/api/tests/unit/test_dinner_search.py`: search parsing and evidence validation.
- `apps/api/tests/unit/test_dinner_negotiation.py`: grounded candidate and privacy tests.
- `apps/web/tests/unit/dorm-dinner-chat.test.tsx`: interaction and rendering tests.

### Task 1: Realtime-safe public conversation messages

**Files:**
- Modify: `apps/api/src/modules/conversations/service.py`
- Modify: `apps/api/src/modules/scenes/chat_dorm_dinner.py`
- Test: `apps/api/tests/unit/test_chat_dorm_dinner.py`

- [ ] **Step 1: Write the failing test**

```python
def test_scene_public_message_publishes_message_created(event_bus_spy, scene_context):
    scene_context.start()
    assert event_bus_spy.last_event.message_type == "SCENE_CARD"
    assert event_bus_spy.last_event.conversation_id == scene_context.conversation_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: FAIL because the scene helper writes `Message` directly and emits no event.

- [ ] **Step 3: Implement the reusable service path**

Add `create_system_message(...)` beside `create_message(...)`. It must validate the conversation, allocate the next sequence, persist a SYSTEM/AGENT message, commit, publish `MessageCreatedEvent`, and return `_message_to_read(msg)`. Replace `_post_system_message` direct ORM writes with this service.

- [ ] **Step 4: Run the focused test**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: PASS.

### Task 2: StepFun search with verifiable evidence

**Files:**
- Create: `apps/api/src/modules/scenes/dinner_search.py`
- Modify: `apps/api/src/config.py`
- Modify: `.env.example`
- Test: `apps/api/tests/unit/test_dinner_search.py`

- [ ] **Step 1: Write failing adapter tests**

```python
def test_search_returns_only_https_evidence(mock_transport):
    client = StepFunSearchClient(api_key="secret", transport=mock_transport)
    results = client.search("上海 复旦大学 聚餐", limit=5)
    assert [item.url for item in results] == ["https://example.com/restaurant"]

def test_search_never_exposes_api_key():
    client = StepFunSearchClient(api_key="secret-value")
    assert "secret-value" not in repr(client)
```

- [ ] **Step 2: Verify RED**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_dinner_search.py -q -p no:cacheprovider`

Expected: FAIL because `StepFunSearchClient` does not exist.

- [ ] **Step 3: Implement strict search models and client**

Implement immutable `SearchEvidence(title, url, snippet, content, indexed_at, retrieved_at)` and `StepFunSearchClient.search(query, limit)`. POST to `${MODEL_GATEWAY_BASE_URL}/search`, authenticate with a `SecretStr`, cap results at 20, accept HTTPS URLs only, never log body/key, and raise a stable scene search error on timeout or non-2xx.

- [ ] **Step 4: Verify GREEN**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_dinner_search.py -q -p no:cacheprovider`

Expected: PASS.

### Task 3: Evidence-grounded multi-agent negotiation and memory

**Files:**
- Create: `apps/api/src/modules/scenes/dinner_negotiation.py`
- Modify: `apps/api/src/modules/scenes/chat_dorm_dinner.py`
- Modify: `apps/api/src/modules/model_gateway/openai_compatible.py`
- Test: `apps/api/tests/unit/test_dinner_negotiation.py`

- [ ] **Step 1: Write failing grounding and privacy tests**

```python
def test_candidate_must_reference_search_evidence(negotiator):
    with pytest.raises(UngroundedCandidateError):
        negotiator.validate_candidate({"name": "虚构餐厅", "source_urls": []}, [])

def test_public_turn_excludes_private_note(negotiator):
    result = negotiator.run_member_turn(private_note="我只有20元", display_name="成员A Agent")
    assert "我只有20元" not in result.public_text
```

- [ ] **Step 2: Verify RED**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_dinner_negotiation.py -q -p no:cacheprovider`

Expected: FAIL because the negotiation service does not exist.

- [ ] **Step 3: Implement negotiation**

Create typed member turns, coordinator turns, candidate evidence, negotiation sessions and public memory. Each requested negotiation accepts `round_count` in `1..10`; each member Agent searches from the required city and origin plus minimized preferences; the coordinator calls `step-3.7-flash` for strict JSON, rejects candidates whose source URLs are absent from the search evidence, and stores only public/de-identified history in `public_context_json`.

- [ ] **Step 4: Remove hard-coded fake candidates**

Delete the fixed “蜀香居/粤味轩/小火锅集合店” fallback. Search/model failures return a public retryable error and create no candidates.

- [ ] **Step 5: Verify GREEN**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_dinner_negotiation.py apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: PASS.

### Task 4: Lifecycle, owner controls and repeat negotiation

**Files:**
- Modify: `apps/api/src/modules/scenes/api.py`
- Modify: `apps/api/src/modules/scenes/chat_dorm_dinner.py`
- Modify: `apps/web/src/lib/dormDinnerChat.ts`
- Test: `apps/api/tests/unit/test_chat_dorm_dinner.py`

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_only_creator_can_close_vote(scene_context, member):
    with pytest.raises(ScenePermissionDeniedError):
        scene_context.close_vote(member)

def test_next_negotiation_keeps_public_memory(scene_context):
    scene_context.run(round_count=2)
    scene_context.request_next_round()
    result = scene_context.run(round_count=5)
    assert result.negotiation_number == 2
    assert result.previous_summary is not None
```

- [ ] **Step 2: Verify RED**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: FAIL because owner controls and repeat negotiation are missing.

- [ ] **Step 3: Implement typed endpoints**

Add request models and endpoints for start metadata (`city`, `origin`, `topic`, `vote_deadline`, `round_count`), disagreement/private reason, next negotiation, close vote and end scene. Enforce active membership and creator-only start/close/end. Return `scene_version`, progress, display mode, negotiation history, sources and creator capabilities in every snapshot.

- [ ] **Step 4: Verify GREEN**

Run: `conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_chat_dorm_dinner.py -q -p no:cacheprovider`

Expected: PASS.

### Task 5: Chat-native expandable card and modal

**Files:**
- Modify: `apps/web/src/app/conversations/[conversationId]/page.tsx`
- Modify: `apps/web/src/lib/dormDinnerChat.ts`
- Create: `apps/web/tests/unit/dorm-dinner-chat.test.tsx`

- [ ] **Step 1: Write failing UI tests**

```tsx
it("opens the dinner composer from the chat toolbar", async () => {
  render(<ConversationPage />);
  await user.click(screen.getByRole("button", { name: "宿舍聚餐" }));
  expect(screen.getByLabelText("城市")).toBeInTheDocument();
});

it("opens a scene message into the four-tab detail dialog", async () => {
  render(<ConversationPage />);
  await user.click(screen.getByRole("button", { name: "打开投票" }));
  expect(screen.getByRole("tab", { name: "智能体协商" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Verify RED**

Run: `corepack pnpm --filter @campus-agent/web test -- --runInBand apps/web/tests/unit/dorm-dinner-chat.test.tsx`

Expected: FAIL because the fixed page section still exists.

- [ ] **Step 3: Implement the toolbar, scene message and modal**

Remove the fixed `DormDinnerChatCard` section. Add a chat toolbar trigger, required start form, compact `SCENE_CARD` renderer, and dialog tabs for private needs, Agent debate, candidates and result. Show evidence links with `target="_blank" rel="noreferrer"`, source retrieval time and the “到店前确认” warning. Only render close/end controls when `capabilities.can_manage` is true.

- [ ] **Step 4: Integrate realtime refresh**

On any dinner `SCENE_CARD`, `AGENT_PUBLIC`, `VOTE` or `RESULT` message event, fetch the latest dinner snapshot. On reconnect and `visibilitychange`, backfill both messages and scene state.

- [ ] **Step 5: Verify GREEN**

Run: `corepack pnpm --filter @campus-agent/web test -- --runInBand apps/web/tests/unit/dorm-dinner-chat.test.tsx`

Expected: PASS.

### Task 6: Full verification and delivery

**Files:**
- Modify: `development-logs/PROGRESS.md` or add a focused completion log if required by repository workflow.

- [ ] **Step 1: Run backend quality checks**

```bash
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests/unit apps/api/tests/integration -q -p no:cacheprovider
```

- [ ] **Step 2: Run frontend quality checks**

```bash
corepack pnpm --filter @campus-agent/web typecheck
corepack pnpm --filter @campus-agent/web lint
corepack pnpm --filter @campus-agent/web test -- --runInBand
corepack pnpm --filter @campus-agent/web build
```

- [ ] **Step 3: Run repository delivery checks**

```bash
git diff --check
git status --short
```

- [ ] **Step 4: Commit and push all authorized changes**

```bash
git add -A
git commit -m "feat: deliver realtime agent dinner voting demo"
git push origin main
```

Expected: push succeeds and `origin/main` points to the delivery commit.
