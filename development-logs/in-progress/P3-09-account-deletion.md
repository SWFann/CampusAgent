---
task_id: P3-09
task_name: 账号删除流程
status: in_review
started_at: 2026-07-16T22:55:00+08:00
completed_at: 2026-07-16T23:10:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P3-09 开发日志：账号删除流程

## 1. 背景

P3-09 实现账号软删除和会话撤销。P3 不做硬删除，避免破坏后续审计外键；删除后认证应失效，登录应失败，公开资料也不应继续暴露。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/users/service.py` | 修改 | `deactivate_user` 软删除并撤销会话 |
| `apps/api/src/modules/auth/service.py` | 修改 | `_revoke_family` 支持普通撤销/重放区分 |
| `apps/api/tests/unit/test_account_deletion.py` | 新增/修改 | 软删除、auth/me、login、会话撤销、公开资料 404 |

## 3. 核心行为

- 设置 `user.status = DELETED`。
- 设置 `deleted_at = utc_now()`。
- 撤销该用户所有 ACTIVE session 和 refresh token family。
- 删除后 `/auth/me` 返回 401。
- 删除后登录返回 `AUTH_INVALID_CREDENTIALS`。
- 删除后公开资料返回 404。

## 4. Codex 审计修正

- 普通删除撤销不再把 session 标记为 `COMPROMISED`，只有 refresh token 重放才使用 compromised。
- 补充删除后公开资料返回 404 的测试。

## 5. 验证

- `test_account_deletion.py` 覆盖 5 个用例。
- Codex 全量验证：`324 passed`，ruff/mypy 通过。

## 6. 边界声明

- 匿名化策略和异步清理任务留到 P9/P12。
- 本阶段不提供用户自助删除 API，仅保留服务层能力供后续接入。
