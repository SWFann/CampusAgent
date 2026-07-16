---
task_id: P2-12
task_name: 测试数据库夹具
status: in_review
started_at: 2026-07-16T23:40:00+08:00
completed_at: 2026-07-16T23:50:00+08:00
actual_hours: 0.17
owner: Claude
auditor: Codex
---

# P2-12: 测试数据库夹具

## 修改文件列表
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/tests/conftest.py` | 重写 | 新增 test_engine/test_session_factory/test_db_session 夹具，保留原有 client 夹具 |

## 设计说明
- `test_engine`: 每个测试独立的 SQLite in-memory engine
- `test_session_factory`: 绑定到 test_engine 的 sessionmaker
- `test_db_session`: 每测试 yield session，测试后 rollback+close 确保隔离
- 保留原有 async client 夹具

## 验证结果
| 命令 | 结果 |
|---|---|
| ruff | All checks passed! |
| mypy | 167 source files, no issues |
| pytest | 222 passed |

## 边界声明
- 未修改 P0/P1 冻结契约
- 未提交、未推送
