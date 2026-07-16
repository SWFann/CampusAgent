---
task_id: P3-11
task_name: 完成认证测试
status: in_review
started_at: 2026-07-16T23:25:00+08:00
completed_at: 2026-07-16T23:45:00+08:00
actual_hours: 0.33
owner: Claude
auditor: Codex
---

# P3-11 开发日志：完成认证测试

## 1. 背景

P3-11 收拢 P3 认证相关测试，包括正常流程、重复注册、过期/撤销/禁用、越权、CSRF、安全回归和端到端流程。目标是确保 P3 的安全边界有自动化测试看守。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/tests/integration/test_auth_flow.py` | 新增 | 注册、me、refresh、logout 集成流程 |
| `apps/api/tests/unit/test_auth_security_regression.py` | 新增 | 密码/token/枚举/CSRF 安全回归 |
| `apps/api/tests/unit/test_app_factory.py` | 修改 | 路由注册和 app factory 测试 |
| `apps/api/tests/conftest.py` | 修改 | SQLite 隔离数据库和 db_client |

## 3. 覆盖范围

- 注册、登录、刷新、注销、/auth/me。
- 重复邮箱/学号、弱密码、禁用/删除账号。
- CSRF missing/mismatch。
- 响应体不含 password_hash/access_token/refresh_token。
- 账号枚举防护。
- 迁移升级/降级。

## 4. 验证

- Codex 审计修正后全量 API：`324 passed, 1 warning`。
- Web Jest：`2 passed`。
- ruff：All checks passed。
- mypy：Success, 185 source files。

## 5. 边界声明

- 真正并发 refresh 和分布式锁测试留到 P12。
- Docker Compose 真实 Postgres/Redis 实跑受当前环境限制未执行。
