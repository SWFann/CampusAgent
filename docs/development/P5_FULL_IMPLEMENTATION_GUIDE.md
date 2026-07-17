# P5 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P5「会话、消息与实时通信」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P5-01～P5-13；不得跳任务、不得执行 P6+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。

## 0. 项目背景

项目名称：CampusAgent

项目路径：

```text
/root/CampusAgent
```

远程仓库：

```text
git@github.com:SWFann/CampusAgent.git
```

P5 前置条件：

- P0/P1 契约已冻结。
- P2 后端公共底座已完成并推送。
- P3 身份、用户与会话安全已完成并推送。
- P4 组织、成员与校园目录必须已由 Codex 审计、修复、提交并推送。
- 如果 P4 仍处于未提交状态，不要开始 P5。

P5 阶段名称：会话、消息与实时通信。

P5 目标：完成私聊、普通群聊、组织群聊、消息历史与可靠的实时状态同步。

P5 不是：

- 不实现 Agent 业务逻辑。
- 不实现 Memory。
- 不实现 Scene 真实执行。
- 不实现模型网关。
- 不实现 P6+。

## 1. 开始前检查

执行：

```bash
cd /root/CampusAgent
git status --short --branch
git log -5 --oneline
```

预期：

- 当前分支为 `main`。
- 工作树干净。
- 最新提交应是 P4 Codex 收口提交。
- 如果不是，停止并报告。

不要执行：

```bash
git reset --hard
git checkout -- .
git clean -fd
```

除非用户明确要求。

## 2. 必读文件

必须阅读：

1. `docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md`
2. `docs/project/README.md`
3. `docs/development/DEVELOPMENT_PLAN.md`
4. `docs/development/P4-COMPLETION-REPORT.md`
5. `docs/api/API_CONTRACT.md`
6. `docs/api/WEBSOCKET_CONTRACT.md`
7. `docs/domain/DOMAIN_VOCABULARY.md`
8. `docs/architecture/PERMISSION_MATRIX.md`
9. `docs/privacy/PRIVACY_TEST_MATRIX.md`
10. `docs/security/THREAT_MODEL.md`
11. `apps/api/src/main.py`
12. `apps/api/src/modules/auth/dependencies.py`
13. `apps/api/src/modules/auth/csrf.py`
14. `apps/api/src/modules/users/models.py`
15. `apps/api/src/modules/organizations/models.py`
16. `apps/api/src/modules/organizations/events.py`
17. `apps/api/src/modules/organizations/service.py`
18. `apps/api/src/events/bus.py`
19. `apps/api/src/cache/redis.py`
20. `apps/api/src/schemas/envelope.py`
21. `apps/api/tests/conftest.py`
22. `apps/web/src/lib/api.ts`
23. `apps/web/src/lib/csrf.ts`

重点理解：

- P3 的 Cookie / CSRF / `get_current_user`。
- P4 的 Organization / Membership / role 权限。
- P2 的 Redis client 和 EventBus。
- WebSocket 冻结契约里的 envelope、认证、订阅、错误事件。

## 3. 冻结契约边界

禁止修改以下文件的语义：

- `docs/api/API_CONTRACT.md`
- `docs/api/WEBSOCKET_CONTRACT.md`
- `docs/architecture/PERMISSION_MATRIX.md`
- `docs/privacy/PRIVACY_TEST_MATRIX.md`
- `docs/security/THREAT_MODEL.md`

如发现契约与实现存在冲突：

1. 优先遵守冻结契约。
2. 在完成报告中记录冲突位置。
3. 不擅自修改冻结契约。

P5 必须对齐的能力：

- Conversation 创建、列表、详情。
- Participant 管理。
- Message 写入、列表、删除态。
- WebSocket 鉴权、订阅、事件推送、重连回补。
- 非成员无法读消息或订阅。
- 私有偏好不得进入消息表或 WebSocket。

## 4. 总体验收标准

P5 完成后必须满足：

- 两人可私聊。
- 四人可群聊。
- 组织成员可进入组织默认群聊。
- 组织成员加入/退出后，组织默认群聊参与者同步变化。
- 非成员无法读取 conversation。
- 非成员无法读取 messages。
- 非成员无法订阅 WebSocket conversation。
- 消息可分页。
- WebSocket event envelope 字段完整。
- 断线后可通过 HTTP 回补消息。
- 场景卡可以作为结构化消息占位，但不执行真实场景。
- 任何私有偏好、raw preference、Memory 正文不进入 message content、payload、日志或 WebSocket。

## 5. 文件结构规划

新增或重写：

```text
apps/api/src/modules/conversations/models.py
apps/api/src/modules/conversations/schemas.py
apps/api/src/modules/conversations/repository.py
apps/api/src/modules/conversations/service.py
apps/api/src/modules/conversations/permissions.py
apps/api/src/modules/conversations/events.py
apps/api/src/modules/conversations/exceptions.py
apps/api/src/modules/conversations/api.py
```

新增：

```text
apps/api/src/realtime/__init__.py
apps/api/src/realtime/connection_manager.py
apps/api/src/realtime/events.py
apps/api/src/realtime/pubsub.py
apps/api/src/realtime/api.py
```

迁移：

```text
apps/api/alembic/versions/0004_conversation_message_tables.py
```

修改：

```text
apps/api/src/main.py
apps/api/tests/conftest.py
apps/api/tests/unit/test_alembic.py
```

前端新增：

```text
apps/web/src/app/conversations/page.tsx
apps/web/src/app/conversations/[conversationId]/page.tsx
apps/web/src/lib/conversations.ts
apps/web/src/lib/realtime.ts
```

测试新增：

```text
apps/api/tests/unit/test_conversation_models.py
apps/api/tests/unit/test_private_conversation.py
apps/api/tests/unit/test_group_conversation.py
apps/api/tests/unit/test_org_group_conversation.py
apps/api/tests/unit/test_message_write.py
apps/api/tests/unit/test_message_pagination.py
apps/api/tests/unit/test_message_privacy.py
apps/api/tests/unit/test_websocket_auth.py
apps/api/tests/unit/test_realtime_pubsub.py
apps/api/tests/unit/test_realtime_event_envelope.py
apps/api/tests/unit/test_realtime_reconnect.py
apps/api/tests/integration/test_conversation_flow.py
apps/api/tests/integration/test_realtime_flow.py
```

日志新增：

```text
development-logs/in-progress/P5-01-conversation-model.md
development-logs/in-progress/P5-02-private-conversation.md
development-logs/in-progress/P5-03-group-conversation.md
development-logs/in-progress/P5-04-org-default-conversation.md
development-logs/in-progress/P5-05-message-write.md
development-logs/in-progress/P5-06-message-pagination.md
development-logs/in-progress/P5-07-message-privacy-guard.md
development-logs/in-progress/P5-08-websocket-auth.md
development-logs/in-progress/P5-09-realtime-pubsub.md
development-logs/in-progress/P5-10-realtime-event-envelope.md
development-logs/in-progress/P5-11-reconnect-backfill.md
development-logs/in-progress/P5-12-chat-frontend.md
development-logs/in-progress/P5-13-realtime-integration-tests.md
```

完成报告：

```text
docs/development/P5-COMPLETION-REPORT.md
```

## 6. 数据模型设计

### 6.1 Conversation

推荐枚举：

```python
class ConversationType(StrEnum):
    PRIVATE = "PRIVATE"
    GROUP = "GROUP"
    ORG_GROUP = "ORG_GROUP"
    SCENE = "SCENE"

class ConversationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"
```

推荐字段：

```python
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id"), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=ConversationStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

### 6.2 ConversationParticipant

推荐枚举：

```python
class ParticipantType(StrEnum):
    USER = "USER"
    AGENT = "AGENT"

class ConversationRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    GUEST = "GUEST"

class ParticipantStatus(StrEnum):
    ACTIVE = "ACTIVE"
    LEFT = "LEFT"
    REMOVED = "REMOVED"
```

P5 只真正支持 USER participant。`AGENT` 可作为字段/Schema 占位，不创建真实 Agent。

### 6.3 Message

推荐枚举：

```python
class MessageType(StrEnum):
    TEXT = "TEXT"
    SYSTEM = "SYSTEM"
    SCENE_CARD = "SCENE_CARD"

class MessageStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
```

推荐字段：

- `id`
- `conversation_id`
- `sender_user_id`
- `sender_agent_id`
- `message_type`
- `content`
- `payload_json`
- `idempotency_key`
- `status`
- `created_at`
- `deleted_at`

隐私要求：

- `__repr__` 不输出 content。
- `__repr__` 不输出 payload。
- deleted message 响应不返回 content。
- message content/payload 不能包含 P4/P6/P9 私密字段。

## 7. Alembic 迁移

新增：

```text
apps/api/alembic/versions/0004_conversation_message_tables.py
```

要求：

- `down_revision` 指向 P4 迁移。
- 创建 `conversations`。
- 创建 `conversation_participants`。
- 创建 `messages`。
- 创建索引：
  - conversation type/status
  - participant conversation/user/status
  - message conversation/created_at
  - message idempotency_key
- upgrade/downgrade 可回放。

更新 `apps/api/tests/unit/test_alembic.py`。

## 8. API 设计

建议端点：

- `POST /api/v1/conversations/private`
- `POST /api/v1/conversations`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`
- `POST /api/v1/conversations/{conversation_id}/participants`
- `DELETE /api/v1/conversations/{conversation_id}/participants/{participant_id}`
- `POST /api/v1/conversations/{conversation_id}/messages`
- `GET /api/v1/conversations/{conversation_id}/messages`
- `DELETE /api/v1/conversations/{conversation_id}/messages/{message_id}`

所有 POST/DELETE：

- 必须认证。
- 必须 CSRF。
- 使用 P3 `get_current_user` 和 `require_csrf`。

所有读：

- 必须认证。
- 必须 participant active 或系统权限。

响应：

- 使用统一 API Envelope。
- 不返回 token/session。

## 9. WebSocket 设计

Endpoint：

```text
/ws
```

认证：

- 使用 access_token Cookie。
- token invalid 或 expired 拒绝连接。

客户端消息：

```json
{
  "type": "conversation.subscribe",
  "conversation_id": "uuid",
  "last_event_id": "optional"
}
```

服务端事件 envelope：

```json
{
  "version": "1.0",
  "event_id": "uuid",
  "type": "message.created",
  "occurred_at": "ISO-8601",
  "conversation_id": "uuid",
  "sequence": 123,
  "payload": {}
}
```

错误事件：

```json
{
  "version": "1.0",
  "event_id": "uuid",
  "type": "error",
  "occurred_at": "ISO-8601",
  "error": {
    "code": "CONVERSATION_PERMISSION_DENIED",
    "message": "Permission denied"
  }
}
```

## 10. P5-01 设计会话数据模型

目标：

- 实现 ORM。
- 实现 0004 迁移。
- 更新 conftest。
- 更新 Alembic 测试。

最低测试：

- 创建 PRIVATE conversation。
- 创建 GROUP conversation。
- 创建 ORG_GROUP conversation。
- participant 唯一约束。
- message 创建。
- message repr 不泄露 content。
- migration upgrade/downgrade。

执行：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_conversation_models.py apps/api/tests/unit/test_alembic.py -q -p no:cacheprovider
```

## 11. P5-02 实现私聊创建

目标：

- 两人私聊幂等。
- 参与者集合一致则复用。

测试：

- A 创建 B 私聊成功。
- A 重复创建 B 返回同一个 conversation。
- B 创建 A 返回同一个 conversation。
- A 不能创建与 deleted user 的私聊。
- C 不能读取 A/B 私聊。

## 12. P5-03 实现群聊创建

目标：

- 创建普通 GROUP。
- 创建者 OWNER。
- 初始成员 MEMBER。

测试：

- 四人群聊创建成功。
- 创建者 OWNER。
- 初始成员去重。
- 非 OWNER 不能添加成员。
- OWNER 可移除 MEMBER。

## 13. P5-04 实现组织默认群聊

目标：

- 组织有默认 ORG_GROUP。
- P4 成员事件触发 participant 同步。

测试：

- 创建组织后可创建/获取默认 org group。
- 成员加入组织后进入 org group。
- 成员退出组织后 participant LEFT。
- 非组织成员不可读 org group。

## 14. P5-05 实现消息写入

目标：

- ACTIVE participant 可写消息。
- 支持 idempotency。
- 支持 TEXT/SYSTEM/SCENE_CARD。

测试：

- MEMBER 发送 TEXT 成功。
- 非成员发送失败。
- LEFT participant 发送失败。
- 重复 idempotency_key 不重复写入。
- 普通用户不能伪造 SYSTEM message。

## 15. P5-06 实现消息分页

目标：

- 稳定 cursor。
- deleted message 不泄露正文。

测试：

- 第一页/第二页稳定。
- cursor 非法返回 validation error。
- 非成员不能分页。
- deleted message content 为空或 tombstone。

## 16. P5-07 阻断私有偏好进入消息

目标：

- content/payload 敏感字段检测。
- WebSocket broadcast 也检测。

敏感字段：

- `private_preference`
- `raw_preference`
- `memory_content`
- `budget_detail`
- `dietary_restriction_private`
- `personal_note`

测试：

- content 命中拒绝。
- payload 嵌套命中拒绝。
- 日志不含被拒绝正文。
- broadcast 不含敏感字段。

## 17. P5-08 WebSocket 鉴权

测试：

- 未登录连接失败。
- 登录连接成功。
- 非成员 subscribe 失败。
- 成员 subscribe 成功。
- invalid token close。

## 18. P5-09 实时发布层

实现：

- Redis Pub/Sub backend。
- In-memory fake backend for tests。

测试：

- publish/subscribe。
- Redis unavailable 行为明确。
- 不泄露 payload 正文到 error log。

## 19. P5-10 事件 Envelope

测试：

- version 固定。
- event_id 唯一。
- occurred_at UTC。
- sequence 单调或语义明确。
- payload 无敏感字段。

## 20. P5-11 重连策略

后端：

- 支持 last_event_id 或 since timestamp 回补。

前端：

- 指数退避。
- 去重 event_id。
- HTTP 回补。

## 21. P5-12 聊天页面

页面：

- `/conversations`
- `/conversations/[conversationId]`

要求：

- 会话列表。
- 消息区。
- 输入框。
- 成员栏。
- WebSocket 状态。
- 场景卡占位。
- 不保存 token。

## 22. P5-13 实时集成测试

覆盖：

- 私聊端到端。
- 群聊端到端。
- WebSocket message.created。
- 非成员订阅失败。
- 断线后回补。
- duplicate event 去重。

## 23. 文档和完成报告

更新：

- `docs/development/DEVELOPMENT_PLAN.md`
- P5-01～P5-13 标记 `[x]`。
- P6 保持未开始。

新增：

- `docs/development/P5-COMPLETION-REPORT.md`
- P5 development logs。

报告必须包含：

- 基准提交。
- 修改文件。
- 数据模型。
- API。
- WebSocket。
- 隐私阻断。
- 测试数量。
- 验证结果。
- 未执行项。

## 24. 全量验证

```bash
git status --short --branch
git diff HEAD --check
conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
conda run -n CampusAgent pip check
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
if [ -x /tmp/gitleaks ]; then /tmp/gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner; fi
```

不要提交，不要推送。
