---
task_id: P3-08
task_name: 发布 UserRegistered
status: in_review
started_at: 2026-07-16T22:40:00+08:00
completed_at: 2026-07-16T22:55:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P3-08 开发日志：发布 UserRegistered

## 1. 背景

P3-08 在用户注册事务提交后发布 `UserRegistered` 领域事件，供 P6-02 自动创建个人智能体使用。事件必须保护隐私：不能携带明文 email，只能携带 email_hash。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/users/events.py` | 重写 | `UserRegistered` 和工厂函数 |
| `apps/api/src/events/bus.py` | 修改 | 增加共享 `default_event_bus` |
| `apps/api/src/modules/auth/service.py` | 修改 | 注册提交后发布事件 |
| `apps/api/tests/unit/test_users_api.py` | 修改 | 事件字段、唯一 ID、隐私和发布测试 |
| `apps/api/tests/conftest.py` | 修改 | 每个测试清理共享事件总线 |

## 3. 核心行为

- 事件字段：event_id、user_id、email_hash、occurred_at。
- email_hash 使用 SHA-256(normalised email)。
- event_id 每次唯一。
- 注册事务提交和 refresh 之后才发布。
- 使用共享 `default_event_bus`，避免创建一次性空 bus 使订阅者收不到事件。

## 4. Codex 审计修正

- 原实现 `EventBus().publish(event)` 会把事件发到一个没有订阅者的新 bus。已改为 `default_event_bus.publish(event)`。
- 补充测试：订阅 `default_event_bus` 后注册用户，必须收到且只收到一个 `UserRegistered`。

## 5. 验证

- `test_users_api.py::TestUserRegisteredEvent` 覆盖 4 个用例。
- Codex 全量验证：`324 passed`，ruff/mypy 通过。

## 6. 边界声明

- P3 只发布事件，不消费事件。
- P6-02 负责订阅事件并创建个人 Agent。
