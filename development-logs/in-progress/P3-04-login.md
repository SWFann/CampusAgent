---
task_id: P3-04
task_name: 实现登录
status: in_review
started_at: 2026-07-16T21:30:00+08:00
completed_at: 2026-07-16T21:45:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P3-04 开发日志：实现登录

## 1. 背景

P3-04 在 P3-03 的 token/cookie/auth service 基础上补齐 `POST /api/v1/auth/login`。登录必须复用统一认证失败响应，不能区分"用户不存在"、"密码错误"、"禁用/删除账号"，并且 token 只能通过 HttpOnly Cookie 下发，不能出现在响应体。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/auth/service.py` | 修改 | 实现 `login_user`，创建 AuthSession 和 RefreshToken |
| `apps/api/src/modules/auth/api.py` | 修改 | 实现 `POST /api/v1/auth/login` |
| `apps/api/src/modules/auth/schemas.py` | 修改 | `LoginRequest` 和响应用户字段 |
| `apps/api/tests/unit/test_auth_login.py` | 新增 | 登录成功、失败、安全响应测试 |

## 3. 核心行为

- 邮箱在服务层 lowercase + strip。
- 密码通过 bcrypt `verify_password` 校验。
- 用户不存在、密码错误、禁用、删除均返回 `AUTH_INVALID_CREDENTIALS`。
- 成功登录创建新的 `AuthSession`、`RefreshToken`，并设置 access/refresh/csrf cookie。
- 响应体只返回用户公开字段，不返回 access token、refresh token 或 jti。

## 4. 验证

- `test_auth_login.py` 覆盖成功登录、错误密码、未知用户、禁用用户、CSRF 豁免、响应体无 token。
- Codex 全量验证：`324 passed`，ruff/mypy 通过。

## 5. 边界声明

- 未实现管理员登录后台。
- 未实现外部 OAuth/统一身份认证。
- 未执行 P4+。
