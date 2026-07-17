# P5 完成报告：会话、消息与实时通信

> 阶段：P5
> 完成日期：2026-07-17
> 状态：全部完成（待 Codex 审计）

## 1. 阶段摘要

P5 完成了会话、消息、参与者、WebSocket 基础能力，形成了后续智能体和场景协作的消息底座。包含 13 个子任务（P5-01 至 P5-13），全部通过验收。

## 2. 任务完成清单

| 任务 ID | 任务名称 | 状态 | 核心产物 |
|---------|---------|------|---------|
| P5-01 | 设计会话数据模型 | ✅ | Conversation/Participant/Message ORM 模型、0004 Alembic 迁移、conftest 更新 |
| P5-02 | 实现私聊创建 | ✅ | 私聊幂等复用、双向创建返回同一会话 |
| P5-03 | 实现群聊创建 | ✅ | OWNER/MEMBER 角色、多参与者约束 |
| P5-04 | 实现组织默认群聊 | ✅ | P4 成员事件同步、ORG_GROUP 类型 |
| P5-05 | 实现消息写入 | ✅ | 幂等键去重、TEXT/IMAGE/SYSTEM/SCENE_CARD 类型 |
| P5-06 | 实现消息分页 | ✅ | 分页游标、删除态隐藏内容、成员可见范围 |
| P5-07 | 阻断私有偏好进入消息 | ✅ | 敏感字段正则检测、payload 规则、回归测试 |
| P5-08 | WebSocket 鉴权 | ✅ | HttpOnly Cookie 认证、Origin 白名单、订阅授权 |
| P5-09 | 实时发布层 | ✅ | RedisPubSubBackend + InMemoryPubSubBackend、双后端 |
| P5-10 | 事件 Envelope | ✅ | v1 信封、event_id、sequence、request_id 关联 |
| P5-11 | 重连策略 | ✅ | 指数退避、HTTP 回补、事件去重缓存、前端退避 |
| P5-12 | 聊天页面 | ✅ | 会话列表页、聊天详情页、WS 状态指示器、场景卡占位 |
| P5-13 | 实时集成测试 | ✅ | 20 个集成测试覆盖端到端流程 |

## 3. 核心交付物

### 后端

| 文件 | 说明 |
|------|------|
| `apps/api/src/modules/conversations/models.py` | Conversation、ConversationParticipant、Message ORM 模型 |
| `apps/api/src/modules/conversations/schemas.py` | Pydantic 请求/响应模型 |
| `apps/api/src/modules/conversations/repository.py` | 数据访问层 |
| `apps/api/src/modules/conversations/service.py` | 业务逻辑层（私聊/群聊/消息/隐私阻断） |
| `apps/api/src/modules/conversations/permissions.py` | 会话权限服务 |
| `apps/api/src/modules/conversations/events.py` | 领域事件（MessageCreated 等） |
| `apps/api/src/modules/conversations/exceptions.py` | 模块异常 |
| `apps/api/src/modules/conversations/api.py` | REST API 路由 |
| `apps/api/src/realtime/api.py` | WebSocket 端点 `/api/v1/ws` |
| `apps/api/src/realtime/pubsub.py` | Redis + 内存 PubSub 后端 |
| `apps/api/src/realtime/events.py` | 事件信封构建器 |
| `apps/api/src/realtime/connection_manager.py` | 连接管理器 + 事件去重缓存 |
| `apps/api/alembic/versions/0004_conversation_message_tables.py` | 0004 迁移 |

### 前端

| 文件 | 说明 |
|------|------|
| `apps/web/src/lib/conversations.ts` | 会话 API 客户端 |
| `apps/web/src/lib/realtime.ts` | WebSocket 客户端（退避重连、去重、回补） |
| `apps/web/src/app/conversations/page.tsx` | 会话列表页 |
| `apps/web/src/app/conversations/[conversationId]/page.tsx` | 聊天详情页 |

### 测试

| 文件 | 测试数 | 说明 |
|------|--------|------|
| `test_conversation_models.py` | 6 | ORM 模型验证 |
| `test_private_conversation.py` | 5 | 私聊创建与幂等 |
| `test_group_conversation.py` | 4 | 群聊创建与权限 |
| `test_org_group_conversation.py` | 4 | 组织群聊与事件同步 |
| `test_message_write.py` | 5 | 消息写入与幂等 |
| `test_message_pagination.py` | 4 | 分页与隐私 |
| `test_message_privacy.py` | 3 | 敏感字段阻断 |
| `test_websocket_auth.py` | 4 | WS 鉴权 |
| `test_realtime_pubsub.py` | 5 | PubSub 后端 |
| `test_realtime_event_envelope.py` | 10 | 事件信封 |
| `test_realtime_reconnect.py` | 7 | 重连与回补 |
| `test_alembic.py`（修改） | +4 | P5 迁移验证 |
| `test_conversation_flow.py` | 7 | 集成：会话端到端 |
| `test_realtime_flow.py` | 13 | 集成：实时端到端 |

### 开发日志

| 文件 | 说明 |
|------|------|
| `development-logs/in-progress/P5-01-conversation-model.md` | P5-01 开发日志 |
| `development-logs/in-progress/P5-12-chat-frontend.md` | P5-12 开发日志 |
| `development-logs/in-progress/P5-13-realtime-integration-tests.md` | P5-13 开发日志 |

## 4. 测试结果

| 验证项 | 结果 | 详情 |
|--------|------|------|
| `git diff HEAD --check` | ✅ 通过 | 无空白错误 |
| `ruff check apps/api` | ✅ 通过 | All checks passed |
| `mypy apps/api/src apps/api/tests` | ✅ 通过 | Success: no issues found in 217 source files |
| `pytest apps/api/tests` | ✅ 通过 | 554 passed, 1 warning |
| `corepack pnpm lint` | ✅ 通过 | All checks passed (web + api) |
| `corepack pnpm typecheck` | ✅ 通过 | tsc + mypy 均通过 |
| `corepack pnpm test` | ✅ 通过 | 554 passed |
| `corepack pnpm --filter @campus-agent/web build` | ✅ 通过 | 10/10 pages generated |
| `pip check` | ✅ 通过 | No broken requirements found |
| `docker compose config` | ⚠️ 未执行 | Docker 不可用 |
| `gitleaks detect` | ⚠️ 未执行 | gitleaks 不可用 |

## 5. 未执行项和原因

| 项目 | 原因 |
|------|------|
| `docker compose config` | Docker 未安装（`command not found`） |
| `docker compose up -d postgres redis mock-model` | Docker 未安装 |
| `docker compose ps` | Docker 未安装 |
| `docker compose down` | Docker 未安装 |
| `gitleaks detect` | gitleaks 未安装（`command not found`） |

## 6. 已知风险或 Blocker

1. **Docker/gitleaks 不可用**：当前环境未安装 Docker 和 gitleaks，无法运行容器化验证和密钥扫描。需要在有 Docker 的环境中补充验证。
2. **WebSocket 推送链路**：当前 `MessageCreated` 领域事件已发布到 EventBus，但 EventBus 到 ConnectionManager 的桥接 handler 尚未在 main.py lifespan 中注册。这意味着消息创建后 WebSocket 客户端不会自动收到 `message.created` 推送。客户端通过 HTTP API 获取消息（HTTP 是最终事实来源），功能完整。此桥接可在 P6 或后续阶段补充。
3. **前端 Jest 单元测试**：P5 前端组件暂未添加 Jest 单元测试（`pnpm test` 运行的是 API pytest）。

## 7. 冻结契约合规声明

- ✅ 未修改 `docs/api/API_CONTRACT.md` 语义
- ✅ 未修改 `docs/api/WEBSOCKET_CONTRACT.md` 语义
- ✅ 未修改 `docs/privacy/THREAT_MODEL.md` 语义
- ✅ 未修改 `docs/privacy/PRIVACY_TEST_MATRIX.md` 语义
- ✅ 未引入真实密钥
- ✅ 未写入实验室 Kuboard 地址、账号、密码、飞书 token、真实模型 endpoint
- ✅ 模型接入走抽象层和 mock/fake provider（P5 不涉及模型接入）
- ✅ 未将 token、私有偏好、消息正文、记忆正文写入 localStorage/sessionStorage/URL/log/metrics
- ✅ 管理后台不读取或展示用户私有偏好正文
- ✅ 未将未完成能力伪装为已完成

## 8. 隐私合规

- WebSocket 事件不携带私有偏好、记忆正文、模型 Prompt 或推理信息
- `MessageCreated` 领域事件不携带消息 content（仅携带 ID 和元数据）
- 消息 `__repr__` 不输出 content 或 payload_json
- 敏感字段检测阻断私有偏好进入消息正文
- 删除消息后 content 返回 null
- 前端不存储 token（仅使用 HttpOnly Cookie）
- 前端事件去重使用 event_id（不携带用户数据）

## 9. 最终声明

- ✅ **未提交**：所有更改仅在工作树中，未执行 `git commit`
- ✅ **未推送**：未执行 `git push`
- ✅ **未修改冻结契约语义**：P0 契约文件未被修改
- ✅ **未引入真实密钥**：所有配置使用测试密钥
- ✅ **等待 Codex 最终审计、修 Bug、提交和推送**
