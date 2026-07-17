# P6 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P6「智能体、记忆、授权与审计」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P6-01～P6-16；不得跳任务、不得执行 P7+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。

## 0. 项目背景

项目路径：`/root/CampusAgent`

P6 前置条件：

- P5 必须已由 Codex 审计、修复、提交、推送，并且远端 CI 绿色。
- 如果 P5 仍未提交或工作树不干净，停止并报告。

P6 阶段名称：智能体、记忆、授权与审计。

P6 总目标：

- 让每个用户拥有隔离的个人智能体。
- 所有 Memory 正文加密存储。
- 所有 Memory 访问通过 Consent 和 Memory Service。
- 管理员无正文读取接口。
- 敏感访问有审计记录，但审计记录不含正文。
- 加密、授权或审计关键路径故障时失败关闭。

## 1. 开始前检查

```bash
cd /root/CampusAgent
git status --short --branch
git log -5 --oneline
```

预期：

- `main` 分支。
- 工作树干净。
- 最新提交为 P5 Codex 收口提交。

## 2. 必读文件

1. `docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md`
2. `docs/development/DEVELOPMENT_PLAN.md`
3. `docs/development/P5-COMPLETION-REPORT.md`
4. `docs/api/API_CONTRACT.md`
5. `docs/privacy/PRIVACY_TEST_MATRIX.md`
6. `docs/security/THREAT_MODEL.md`
7. `docs/architecture/PERMISSION_MATRIX.md`
8. `docs/domain/DOMAIN_VOCABULARY.md`
9. `apps/api/src/config.py`
10. `apps/api/src/events/bus.py`
11. `apps/api/src/utils/redaction.py`
12. `apps/api/src/modules/users/models.py`
13. `apps/api/src/modules/auth/dependencies.py`
14. `apps/api/src/modules/conversations/`
15. `apps/api/tests/conftest.py`

## 3. 安全不可变要求

必须满足：

- 管理员无 Memory 正文读取接口。
- 数据库中 Memory 正文必须是加密值。
- `repr()`、日志、metrics、事件不得包含 Memory 明文或密文。
- 每次 Memory 查询必须校验 owner、purpose、category/scope、consent、expiry、deleted_at。
- consent revoke 后立即失效。
- 加密 key 缺失、解密失败、consent service 失败时拒绝请求。
- 不允许其他模块绕过 Memory Service 直接读取 MemoryRepository。

## 4. 文件结构规划

Agents：

```text
apps/api/src/modules/agents/models.py
apps/api/src/modules/agents/schemas.py
apps/api/src/modules/agents/repository.py
apps/api/src/modules/agents/service.py
apps/api/src/modules/agents/events.py
apps/api/src/modules/agents/exceptions.py
apps/api/src/modules/agents/api.py
```

Memories：

```text
apps/api/src/modules/memories/models.py
apps/api/src/modules/memories/schemas.py
apps/api/src/modules/memories/repository.py
apps/api/src/modules/memories/service.py
apps/api/src/modules/memories/encryption.py
apps/api/src/modules/memories/consent.py
apps/api/src/modules/memories/cleanup.py
apps/api/src/modules/memories/exceptions.py
apps/api/src/modules/memories/api.py
```

Audit：

```text
apps/api/src/modules/audit/models.py
apps/api/src/modules/audit/schemas.py
apps/api/src/modules/audit/repository.py
apps/api/src/modules/audit/service.py
apps/api/src/modules/audit/api.py
```

Migration：

```text
apps/api/alembic/versions/0005_agent_memory_consent_audit_tables.py
```

Frontend：

```text
apps/web/src/app/agents/page.tsx
apps/web/src/app/memories/page.tsx
apps/web/src/app/audit/page.tsx
apps/web/src/lib/agents.ts
apps/web/src/lib/memories.ts
apps/web/src/lib/audit.ts
```

Tests：

```text
apps/api/tests/unit/test_agent_models.py
apps/api/tests/unit/test_agent_personal_creation.py
apps/api/tests/unit/test_agent_config.py
apps/api/tests/unit/test_memory_models.py
apps/api/tests/unit/test_memory_encryption.py
apps/api/tests/unit/test_memory_crud.py
apps/api/tests/unit/test_consent_records.py
apps/api/tests/unit/test_consent_service.py
apps/api/tests/unit/test_memory_query_policy.py
apps/api/tests/unit/test_memory_boundary.py
apps/api/tests/unit/test_audit_logs.py
apps/api/tests/unit/test_agent_run_metadata.py
apps/api/tests/unit/test_memory_cleanup.py
apps/api/tests/unit/test_privacy_memory.py
```

## 5. 数据模型

### Agent

枚举：

- `PERSONAL`
- `GROUP`
- `ORG`

Delegation level：

- `L0`
- `L1`
- `L2`
- `L3`

P6 禁用 `L4`。

字段：

- `id`
- `owner_user_id`
- `type`
- `name`
- `avatar_url`
- `public_persona`
- `private_config_encrypted`
- `delegation_level`
- `status`
- timestamps

### MemoryItem

字段：

- `id`
- `owner_user_id`
- `agent_id`
- `category`
- `sensitivity_level`
- `source`
- `content_encrypted`
- `content_hash`
- `encryption_key_version`
- `expires_at`
- `deleted_at`
- timestamps

### ConsentRecord

字段：

- `id`
- `grantor_user_id`
- `grantee_agent_id`
- `purpose`
- `scope_json`
- `granted`
- `expires_at`
- `revoked_at`
- timestamps

### AuditLog

字段：

- `id`
- `actor_user_id`
- `action`
- `resource_type`
- `resource_id`
- `purpose`
- `result`
- `request_id`
- `metadata_json`
- `created_at`

### AgentRun

字段：

- `id`
- `agent_id`
- `actor_user_id`
- `purpose`
- `input_hash`
- `output_hash`
- `model_name`
- `token_count`
- `latency_ms`
- `status`
- timestamps

## 6. P6-01 设计 Agent 模型

目标：

- Agent ORM。
- Agent schema。
- Alembic 表。
- 模型测试。

测试：

- personal agent 创建成功。
- owner required。
- delegation L0-L3 有效。
- L4 拒绝。
- private_config 不出现在 repr。

## 7. P6-02 自动创建个人智能体

监听 P3 `UserRegistered`。

要求：

- 幂等。
- 一用户一个 personal agent。
- 重复事件不创建第二个。
- handler 异常不破坏注册流程。

测试：

- 注册后创建 personal agent。
- 重复 UserRegistered 不重复。
- 已存在 agent 时跳过。

## 8. P6-03 智能体配置

API：

- `GET /api/v1/agents/me`
- `GET /api/v1/agents/{agent_id}`
- `PATCH /api/v1/agents/{agent_id}`

权限：

- owner 可读写。
- 非 owner 不可读 private config。
- 管理员只能读 metadata，不读 private_config。

## 9. P6-04 MemoryItem

目标：

- MemoryItem ORM。
- 加密字段。
- TTL。
- soft delete。

测试：

- content_encrypted 非空。
- plaintext 不落库。
- expires_at 可设置。
- deleted_at 后查询排除。

## 10. P6-05 字段加密服务

实现：

```text
apps/api/src/modules/memories/encryption.py
```

要求：

- 使用 `FIELD_ENCRYPTION_KEY`。
- 认证加密，推荐 Fernet/AES-GCM。
- 支持 key version。
- 解密失败抛 AppError。
- production 缺 key 失败关闭。

测试：

- encrypt/decrypt roundtrip。
- 错 key 失败。
- 密文不包含明文。
- 日志不含密文/明文。

## 11. P6-06 Memory CRUD

API：

- `POST /api/v1/memories`
- `GET /api/v1/memories`
- `GET /api/v1/memories/{memory_id}`
- `PATCH /api/v1/memories/{memory_id}`
- `DELETE /api/v1/memories/{memory_id}`

规则：

- owner-only。
- 写请求 CSRF。
- 响应给 owner 可返回明文，但日志不含。
- 管理员无正文接口。

## 12. P6-07 ConsentRecord

purpose：

- `chat_reply`
- `scene_execution`
- `memory_review`
- `recommendation`

scope：

- category
- memory_id
- scene_instance_id
- expires_at

## 13. P6-08 授权服务

实现：

- grant
- check
- revoke
- expire

测试：

- grant 后 check true。
- revoked 后 false。
- expired 后 false。
- wrong purpose false。
- wrong category false。

## 14. P6-09 Memory 查询策略

所有查询必须匹配：

- owner。
- agent。
- purpose。
- category/scope。
- active consent。
- not expired。
- not deleted。

测试：

- A 不能查 B。
- A 的 agent 不能用错误 purpose 查。
- revoke 立即生效。

## 15. P6-10 禁止绕过 Memory Service

实现 architecture test：

- 禁止 `modules/*` 直接 import `MemoryRepository`。
- 允许 `modules/memories/service.py`。
- 允许 tests。

## 16. P6-11 审计模型

实现 AuditLog。

禁止：

- content。
- prompt。
- memory plaintext。
- encrypted content。

## 17. P6-12 审计写入与查询

自动审计：

- memory read。
- consent grant/revoke。
- agent config update。

API：

- `GET /api/v1/audit/me`

只返回用户自己的 audit metadata。

## 18. P6-13 AgentRun 元数据

只保存：

- hash。
- model。
- token。
- latency。
- status。

不保存 prompt/response。

## 19. P6-14 TTL 清理任务

实现可重入 cleanup。

测试：

- expired memory soft delete。
- repeated cleanup no-op。
- revoked consent cleanup。

## 20. P6-15 隐私测试

覆盖：

- A/B 隔离。
- 管理员拒绝正文。
- 撤销即时生效。
- 加密失败关闭。
- 审计无正文。
- metrics/log 无正文。

## 21. P6-16 前端页面

页面：

- `/agents`
- `/memories`
- `/audit`

要求：

- 配置 agent。
- 查看 memory。
- 删除 memory。
- grant/revoke consent。
- audit metadata。
- 不使用 localStorage 保存 memory。

## 22. 文档和报告

新增：

- `docs/development/P6-COMPLETION-REPORT.md`
- P6-01～P6-16 logs。

更新：

- `docs/development/DEVELOPMENT_PLAN.md`
- P6 全部 `[x]`。
- P7 保持未开始。

## 23. 全量验证

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
