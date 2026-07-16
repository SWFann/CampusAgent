---
task_id: P2-11
task_name: Repository / Unit of Work 基线
status: in_review
started_at: 2026-07-16T23:25:00+08:00
completed_at: 2026-07-16T23:40:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P2-11: Repository / Unit of Work 基线

## 修改文件列表
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/db/repositories.py` | 新增 | BaseRepository 泛型 CRUD、UnitOfWork 事务管理+事件发布 |
| `apps/api/tests/unit/test_repositories.py` | 新增 | 6 个测试覆盖 add/get/list/delete、commit/rollback、事件发布、session 上下文管理 |

## 设计说明
- BaseRepository: session-scoped，get_by_id/list/add/delete
- UnitOfWork: 上下文管理器，commit on success / rollback on exception
- 事件在 commit 成功后发布，异常时不发布
- session 在 finally 中关闭

## 验证结果
| 命令 | 结果 |
|---|---|
| ruff | All checks passed! |
| mypy | 167 source files, no issues |
| pytest | 222 passed |

## 边界声明
- 未定义业务模型
- 未修改 P0/P1 冻结契约
- 未提交、未推送
