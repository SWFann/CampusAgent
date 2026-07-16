---
task_id: P3-07
task_name: 实现资料读写 User API
status: in_review
started_at: 2026-07-16T22:20:00+08:00
completed_at: 2026-07-16T22:40:00+08:00
actual_hours: 0.33
owner: Claude
auditor: Codex
---

# P3-07 开发日志：实现资料读写 User API

## 1. 背景

P3-07 实现用户公开资料读取和本人资料更新。该阶段只开放安全字段，后续组织成员、目录搜索和管理员状态 API 留到 P4。公开资料接口不能泄露 email、student_no、password_hash 或 session 信息。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/users/api.py` | 新增 | `/api/v1/users/{id}` GET/PATCH 和占位端点 |
| `apps/api/src/modules/users/service.py` | 新增/修改 | 公开资料、本人更新、软删除辅助 |
| `apps/api/src/modules/users/schemas.py` | 修改 | 公开资料和更新请求 schema |
| `apps/api/src/modules/users/permissions.py` | 修改 | 本人权限检查 |
| `apps/api/tests/unit/test_users_api.py` | 新增/修改 | 公开字段、本人更新、越权、CSRF 测试 |

## 3. 核心行为

- `GET /users/{id}` 返回公开资料：id、display_name、avatar_url、profile_visibility。
- `PATCH /users/{id}` 只允许本人修改 display_name、avatar_url、bio、profile_visibility。
- PATCH 必须通过认证和 CSRF。
- 越权修改返回 `PERMISSION_DENIED`。
- 删除状态用户被视为不存在。

## 4. Codex 审计修正

- `get_user_public_profile` 增加 `UserStatus.DELETED` 判断，软删除用户公开资料返回 404。

## 5. 验证

- `test_users_api.py` 覆盖资料读取/更新/越权/CSRF。
- `test_account_deletion.py` 补充软删除后公开资料 404。
- Codex 全量验证：`324 passed`，ruff/mypy 通过。

## 6. 边界声明

- 管理员状态 API 和组织目录不在 P3 实现。
- 组织列表/个人 Agent 占位端点仅为后续阶段预留。
