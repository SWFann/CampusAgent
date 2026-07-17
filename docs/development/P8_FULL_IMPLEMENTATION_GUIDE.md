# P8 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P8「场景核心与插件框架」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P8-01～P8-14；不得跳任务、不得执行 P9+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。

## 0. 项目背景

P8 前置条件：

- P7 已由 Codex 审计、修复、提交、推送，远端 CI 绿色。
- 如果 P7 未提交或工作树不干净，停止并报告。

P8 目标：

- 建立与具体聚餐逻辑无关的 Scene Core。
- 建立插件协议。
- 插件不能绕过授权、记忆、聊天、模型网关边界。
- 空示例插件可走完整生命周期。
- 非法转换和越权访问失败。
- 公共事件无私有字段。
- 失败/取消/过期都会清理 P4 临时数据。

## 1. 必读文件

1. `docs/development/P7-COMPLETION-REPORT.md`
2. `docs/development/DEVELOPMENT_PLAN.md`
3. `docs/api/API_CONTRACT.md`
4. `docs/privacy/PRIVACY_TEST_MATRIX.md`
5. `docs/security/THREAT_MODEL.md`
6. `apps/api/src/modules/memories/service.py`
7. `apps/api/src/modules/model_gateway/service.py`
8. `apps/api/src/modules/conversations/service.py`
9. `apps/api/src/modules/agents/service.py`
10. `apps/api/src/events/bus.py`

## 2. 文件结构规划

新增/重写：

```text
apps/api/src/modules/scenes/plugin_protocol.py
apps/api/src/modules/scenes/registry.py
apps/api/src/modules/scenes/models.py
apps/api/src/modules/scenes/schemas.py
apps/api/src/modules/scenes/repository.py
apps/api/src/modules/scenes/state_machine.py
apps/api/src/modules/scenes/service.py
apps/api/src/modules/scenes/coordinator.py
apps/api/src/modules/scenes/events.py
apps/api/src/modules/scenes/privacy.py
apps/api/src/modules/scenes/cleanup.py
apps/api/src/modules/scenes/exceptions.py
apps/api/src/modules/scenes/api.py
apps/api/src/modules/scenes/test_plugins.py
apps/api/alembic/versions/0007_scene_core_tables.py
```

前端：

```text
apps/web/src/app/scenes/page.tsx
apps/web/src/app/scenes/[sceneInstanceId]/page.tsx
apps/web/src/lib/scenes.ts
```

测试：

```text
apps/api/tests/unit/test_scene_plugin_protocol.py
apps/api/tests/unit/test_scene_registry.py
apps/api/tests/unit/test_scene_models.py
apps/api/tests/unit/test_scene_private_submission.py
apps/api/tests/unit/test_scene_state_machine.py
apps/api/tests/unit/test_scene_participation.py
apps/api/tests/unit/test_scene_private_submission_api.py
apps/api/tests/unit/test_scene_coordinator.py
apps/api/tests/unit/test_scene_public_events.py
apps/api/tests/unit/test_scene_voting.py
apps/api/tests/unit/test_scene_cancel_expire.py
apps/api/tests/unit/test_scene_cleanup.py
apps/api/tests/unit/test_scene_boundary_plugin.py
apps/api/tests/integration/test_scene_core_flow.py
```

## 3. 数据模型

### SceneDefinition

- id
- scene_key
- version
- name
- description
- enabled
- capabilities_json
- created_at

### SceneInstance

- id
- definition_id
- conversation_id
- created_by
- status
- current_phase
- idempotency_key
- expires_at
- completed_at
- cancelled_at
- failed_reason_code
- timestamps

状态：

- DRAFT
- INVITING
- COLLECTING_PRIVATE_INPUT
- GENERATING_CANDIDATES
- VOTING
- CONFIRMING
- COMPLETED
- CANCELLED
- EXPIRED
- FAILED

### SceneParticipant

- id
- scene_instance_id
- user_id
- status: INVITED/ACCEPTED/DECLINED/LEFT
- consent_record_id
- joined_at

### PrivateSubmission

- id
- scene_instance_id
- user_id
- encrypted_payload
- capsule_json
- expires_at
- deleted_at

### SceneCandidate / SceneResult

只保存公共候选和公共结果，不保存私有偏好正文。

## 4. P8-01 ScenePlugin Protocol

定义协议：

- `validate_private_submission`
- `build_private_capsule`
- `generate_candidates`
- `evaluate_candidate_privately`
- `aggregate_results`
- `build_public_result`
- `cleanup_private_data`

要求：

- 插件只能通过 SceneServiceFacade 调用 Memory/Model/Conversation。
- 插件不能直接 import repository。
- 协议类型可被 mypy 检查。

## 5. P8-02 场景注册表

实现：

- register(scene_key, version)
- enable/disable
- get plugin
- list enabled

测试：

- scene_key + version 唯一。
- disabled plugin 不可创建 instance。

## 6. P8-03 场景数据模型

实现 ORM + 迁移。

测试：

- definition。
- instance。
- participant。
- candidate。
- result。
- migration 回放。

## 7. P8-04 私有提交模型

要求：

- payload 加密。
- capsule 最小化。
- expires_at。
- deleted_at。
- response 不回显原文。

测试：

- 数据库无 plaintext。
- owner 可提交。
- 非 owner 不能读。
- admin 不能读。

## 8. P8-05 状态机

合法流：

```text
DRAFT -> INVITING -> COLLECTING_PRIVATE_INPUT -> GENERATING_CANDIDATES -> VOTING -> CONFIRMING -> COMPLETED
```

终止流：

```text
* -> CANCELLED
* -> EXPIRED
* -> FAILED
```

测试：

- 非法跳转失败。
- 终态不可跳。
- 重复 transition 幂等。
- 并发锁防止双执行。

## 9. P8-06 参与和授权

实现：

- invite
- accept
- decline
- scene-level consent

规则：

- 没 consent 不可提交私有输入。
- revoke 后后续阶段失败关闭。

## 10. P8-07 私有提交 API

API：

- POST submission
- GET submission status
- PATCH replace
- DELETE submission

禁止：

- 回显原文。
- admin 读取原文。
- 写入 message 表。

## 11. P8-08 执行协调器

Coordinator 可调用：

- plugin protocol
- Memory Service
- Model Gateway
- Conversation Service
- Cleanup Service

禁止：

- 直接查跨模块表。
- 直接读取 MemoryRepository。
- 直接调用外部模型。

## 12. P8-09 公开场景事件

事件只含：

- scene_instance_id
- phase
- submitted_count
- candidate_count
- public_result_id

不含：

- private payload。
- capsule。
- individual score。
- memory content。

## 13. P8-10 投票与确认框架

规则：

- 一人一票。
- 修改投票策略明确。
- 只有 scene participant 可投。
- 确认人权限必须校验。
- 重复 vote 幂等。

## 14. P8-11 取消/过期

要求：

- cancel。
- expire。
- failure。
- 触发 cleanup。
- 发布公共事件。

## 15. P8-12 清理编排

要求：

- 立即清理。
- 24h 兜底。
- 重复执行安全。
- 清理后 API 无法读取 private payload。

## 16. P8-13 边界测试插件

恶意插件尝试：

- 跨用户读 memory。
- 非法状态跳转。
- 返回敏感字段。
- import repository。
- 直接调用 model adapter。

全部必须失败。

## 17. P8-14 框架测试

覆盖：

- 并发提交。
- 重复请求。
- 撤销授权。
- 超时。
- 失败关闭。
- public event 无私有字段。

## 18. 前端页面

页面：

- `/scenes`
- `/scenes/[sceneInstanceId]`

要求：

- 展示可用场景。
- 创建场景 instance。
- 显示 phase。
- 显示 privacy notice。
- 不展示私有提交正文。

## 19. 文档和报告

新增：

- `docs/development/P8-COMPLETION-REPORT.md`
- P8-01～P8-14 logs。

更新：

- `docs/development/DEVELOPMENT_PLAN.md`
- P8 `[x]`。
- P9 未开始。

## 20. 全量验证

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
