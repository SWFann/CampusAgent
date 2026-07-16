---
task_id: P3-06
task_name: 实现当前用户上下文
status: in_review
started_at: 2026-07-16T22:05:00+08:00
completed_at: 2026-07-16T22:20:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P3-06 开发日志：实现当前用户上下文

## 1. 背景

P3-06 提供认证依赖和 `GET /api/v1/auth/me`，作为后续 P4～P10 权限判断的基础。当前阶段采用 HttpOnly Cookie 承载 access token，读接口不要求 CSRF，写接口由 P3-05/P3-07 强制 CSRF。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/auth/dependencies.py` | 新增 | `get_current_user`，解析 access_token cookie |
| `apps/api/src/modules/auth/api.py` | 修改 | 实现 `/auth/me` |
| `apps/api/tests/unit/test_auth_me.py` | 新增 | 当前用户、缺失、篡改、过期、禁用测试 |

## 3. 核心行为

- 从 `access_token` Cookie 读取 JWT。
- 校验 token 类型必须为 access。
- 用户不存在、禁用或删除时返回 `AUTH_INVALID_TOKEN`。
- 响应体只包含 id/email/display_name/global_role，不包含 password_hash、token 或 session 信息。

## 4. 验证

- `test_auth_me.py` 覆盖 6 个用例。
- Codex 全量验证：`324 passed`，ruff/mypy 通过。

## 5. 边界声明

- Bearer token 支持未作为 P3 主路径实现。
- 管理员/组织角色依赖留到 P4。
