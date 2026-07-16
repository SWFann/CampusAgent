---
task_id: P2-09
task_name: 统一时间与 ID 工具
status: in_review
started_at: 2026-07-16T22:55:00+08:00
completed_at: 2026-07-16T23:10:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P2-09: 统一时间与 ID 工具

## 修改文件列表
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/utils/clock.py` | 新增 | Clock/UuidFactory Protocol、DefaultClock、FrozenClock、DefaultUuidFactory、FrozenUuidFactory |
| `apps/api/tests/unit/test_clock.py` | 新增 | 10 个测试覆盖 DefaultClock/FrozenClock/DefaultUuidFactory/FrozenUuidFactory |

## 设计说明
- `Clock` Protocol: `now() -> datetime`
- `DefaultClock`: 使用 `utc_now()` (P2-03 已有)
- `FrozenClock`: 固定时间，可 advance
- `UuidFactory` Protocol: `new_uuid() -> UUID`
- `DefaultUuidFactory`: 使用 `uuid4()` (P2-03 已有)
- `FrozenUuidFactory`: 预定义 UUID 队列，耗尽后 fallback

## 验证结果
| 命令 | 结果 |
|---|---|
| ruff | All checks passed! |
| mypy | 167 source files, no issues |
| pytest | 222 passed |

## 边界声明
- 未修改 P0/P1 冻结契约
- 未提交、未推送
