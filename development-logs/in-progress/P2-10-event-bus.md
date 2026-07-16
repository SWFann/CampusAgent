---
task_id: P2-10
task_name: 领域事件总线
status: in_review
started_at: 2026-07-16T23:10:00+08:00
completed_at: 2026-07-16T23:25:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P2-10: 领域事件总线

## 修改文件列表
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/events/__init__.py` | 新增 | events 包初始化 |
| `apps/api/src/events/bus.py` | 新增 | DomainEvent 基类、EventHandler Protocol、EventBus |
| `apps/api/tests/unit/test_event_bus.py` | 新增 | 7 个测试覆盖 subscribe/publish、多 handler、隔离、失败策略、clear、handler_count |

## 设计说明
- 进程内同步发布/订阅
- 按 event type 隔离
- handler 失败被捕获并记录，不阻断其他 handler
- EventBus 不参与数据库事务（由 UoW 管理事务后发布）

## 验证结果
| 命令 | 结果 |
|---|---|
| ruff | All checks passed! |
| mypy | 167 source files, no issues |
| pytest | 222 passed |

## 边界声明
- 未修改 P0/P1 冻结契约
- 未提交、未推送
