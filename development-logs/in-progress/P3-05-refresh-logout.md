---
task_id: P3-05
task_name: 实现刷新与注销
status: in_review
started_at: 2026-07-16T21:45:00+08:00
completed_at: 2026-07-16T22:05:00+08:00
actual_hours: 0.33
owner: Claude
auditor: Codex
---

# P3-05 开发日志：实现刷新与注销

## 1. 背景

P3-05 实现 refresh token 轮换、重放检测、注销和 Cookie 清除。该任务承接 P0/P1 冻结契约中的会话安全要求：refresh token 不进入响应体，旧 refresh token 只能使用一次，重放时撤销整个 family。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/auth/service.py` | 修改 | `refresh_token_rotation`、`logout_user`、`_revoke_family` |
| `apps/api/src/modules/auth/api.py` | 修改 | `POST /auth/refresh`、`POST /auth/logout` |
| `apps/api/src/modules/auth/csrf.py` | 新增 | double-submit CSRF 校验 |
| `apps/api/src/modules/auth/cookies.py` | 新增 | Cookie 设置和清除 |
| `apps/api/tests/unit/test_auth_refresh_logout.py` | 新增/修改 | 轮换、重放、CSRF、Cookie 清除测试 |

## 3. 核心行为

- `/auth/refresh` 必须同时携带 refresh cookie 和匹配的 `X-CSRF-Token`。
- 成功 refresh：旧 token 标记 `USED`，新 refresh token 入库，session_version 递增。
- 旧 token 再次使用：视为重放，family 下会话标记 `COMPROMISED`。
- `/auth/logout`：普通用户主动注销，family 下 token 撤销，会话标记 `REVOKED`。
- logout 返回 204，并使用同一个响应对象写入三类清除 Cookie 的 `Set-Cookie`。

## 4. Codex 审计修正

- 修复 logout 先清 Cookie 后返回新 `Response` 导致 `Set-Cookie` 丢失的问题。
- `_revoke_family` 增加 `mark_compromised` 参数，区分重放攻击和正常注销。
- 补充断言：logout 响应必须包含 access_token、refresh_token、csrf_token 的清除 Cookie。

## 5. 验证

- `test_auth_refresh_logout.py` 覆盖 9 个用例。
- Codex 全量验证：`324 passed`，ruff/mypy 通过。

## 6. 边界声明

- 未实现跨设备会话管理 UI。
- 未实现 Redis/数据库级分布式并发锁；真正并发刷新压力测试留到 P12。
