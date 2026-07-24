# Group Chat Member Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual group participant UUID entry with a searchable member picker for creating group chats.

**Architecture:** Reuse the existing directory search API from `apps/web/src/lib/directory.ts` and keep the existing group creation API unchanged. The conversations page will manage selected user objects locally, send only selected IDs to `createGroupConversation`, and show user-friendly validation before calling the backend.

**Tech Stack:** Next.js React page component, TypeScript API helpers, Jest and Testing Library.

---

### Task 1: Conversation Page Member Picker Test

**Files:**
- Modify: `apps/web/src/app/conversations/page.tsx`
- Create: `apps/web/tests/unit/conversations-create.test.tsx`

- [ ] **Step 1: Write failing UI behavior test**

Create a Jest test that renders the conversations page, switches to group creation, searches for `Alice`, clicks `添加`, verifies Alice appears in selected members, submits the form, and asserts `createGroupConversation` receives `participant_user_ids: ["user-alice"]`.

- [ ] **Step 2: Run test to verify failure**

Run: `corepack pnpm --filter @campus-agent/web test -- conversations-create.test.tsx --runInBand`

Expected: failure because the page still renders the manual `参与者用户 ID` input and has no user search picker.

### Task 2: Implement Search And Selection

**Files:**
- Modify: `apps/web/src/app/conversations/page.tsx`

- [ ] **Step 1: Import directory search**

Add `searchDirectory` and `DirectoryUserResult` imports from `@/lib/directory`.

- [ ] **Step 2: Replace participant ID text state**

Replace `participantIds` string state with:

```ts
const [memberSearchQuery, setMemberSearchQuery] = useState("");
const [memberSearchResults, setMemberSearchResults] = useState<DirectoryUserResult[]>([]);
const [memberSearchLoading, setMemberSearchLoading] = useState(false);
const [selectedMembers, setSelectedMembers] = useState<DirectoryUserResult[]>([]);
```

- [ ] **Step 3: Add search handler**

Add a handler that trims the query, requires at least 2 characters, calls `searchDirectory(query, "users", 8)`, filters out already selected users, and shows an action error if the search fails.

- [ ] **Step 4: Add add/remove helpers**

Add `addSelectedMember(user)` and `removeSelectedMember(userId)` helpers that dedupe by ID.

- [ ] **Step 5: Submit selected IDs**

Change group submit validation to require `selectedMembers.length > 0`, show `请至少选择一位成员`, and send `selectedMembers.map((member) => member.id)`.

- [ ] **Step 6: Render picker UI**

Render search input, search button, result rows with `添加`, selected member chips with `移除`, and remove the manual UUID input.

### Task 3: Verification And Commit

**Files:**
- Verify touched files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
corepack pnpm --filter @campus-agent/web test -- conversations-create.test.tsx --runInBand
corepack pnpm --filter @campus-agent/web typecheck
```

- [ ] **Step 2: Run full checks**

Run:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

- [ ] **Step 3: Commit and push**

Commit all local changes and push to `main`.
