---
task_id: P2-04
task_name: 初始化 Alembic
status: in_review
started_at: 2026-07-16T19:00:00+08:00
completed_at: 2026-07-16T19:45:00+08:00
actual_hours: 0.75
owner: Claude
auditor: Codex
---

# P2-04: 初始化 Alembic

## 1. 背景

- P2-01 Docker Compose 基线已通过 Codex 审计。
- P2-02 配置对象已通过 Codex 审计。
- P2-03 PostgreSQL 接入已完成并通过 Codex 整改审计。
- 当前路径：`/root/CampusAgent`
- 当前分支：`main`，基准提交 `5124c09 docs(project): record remote CI completion`
- P2-01/P2-02/P2-03 未提交修改完整保留。
- 本次任务只做 P2-04：初始化 Alembic 迁移基线。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/alembic.ini` | 新增 | Alembic 配置文件，不硬编码数据库 URL |
| `apps/api/alembic/env.py` | 新增 | Alembic 环境脚本，使用 Base.metadata，从 DATABASE_URL 环境变量读取 URL |
| `apps/api/alembic/script.py.mako` | 新增 | 迁移脚本模板 |
| `apps/api/alembic/versions/0001_baseline.py` | 新增 | 基线迁移（空迁移，不创建业务表） |
| `apps/api/alembic/versions/README.md` | 新增 | versions 目录说明 |
| `apps/api/tests/unit/test_alembic.py` | 新增 | 13 个测试覆盖配置加载、env.py 结构、升级/降级/循环、离线模式 |
| `Makefile` | 修改 | 新增 `db-downgrade` 和 `db-revision` 命令，修正 `db-migrate` 使用 `alembic -c alembic.ini` |

## 3. Alembic 设计说明

### 3.1 配置文件 (alembic.ini)

- 位于 `apps/api/alembic.ini`
- `script_location = alembic`（相对于 alembic.ini 所在目录）
- 不在 ini 文件中硬编码数据库 URL
- 日志配置：root=WARNING, sqlalchemy=WARNING, alembic=INFO

### 3.2 环境脚本 (env.py)

- 将 `apps/api/` 加入 `sys.path`，确保 `from src.config import Settings` 可解析
- `target_metadata = Base.metadata`（来自 `src.db.base`）
- 数据库 URL 解析顺序：
  1. Alembic `-x database-url=...` CLI 选项
  2. `DATABASE_URL` 环境变量
  3. `Settings.DATABASE_URL` 默认值
- 支持在线模式和离线模式（SQL 生成）
- SQLite 使用 StaticPool 支持 `:memory:` 测试
- 不在 import 时连接数据库
- 当无 Alembic 上下文时（如被测试直接导入），安全跳过迁移执行

### 3.3 基线迁移 (0001_baseline.py)

- 空迁移（`upgrade()` 和 `downgrade()` 均为 `pass`）
- Alembic 自动创建 `alembic_version` 表
- 不创建任何业务表
- `downgrade base` 后 `alembic_version` 表保留但 0 行（Alembic 正常行为）

### 3.4 URL 解析策略

- 不自动读取生产数据库
- 测试使用 SQLite 临时文件
- 生产使用 `DATABASE_URL` 环境变量

## 4. 新增测试列表

| 测试类 | 用例 | 覆盖点 |
|---|---|---|
| `TestAlembicConfig` (5 cases) | ini 存在、目录存在、配置加载、versions 目录、基线迁移存在 | 基础配置 |
| `TestEnvMetadata` (3 cases) | 引用 Base.metadata、解析 DATABASE_URL、不硬编码 URL | env.py 结构 |
| `TestMigrationUpgradeDowngrade` (4 cases) | upgrade 创建表、downgrade 清空版本、无业务表、循环升级 | 迁移行为 |
| `TestOfflineMode` (1 case) | 离线模式 SQL 生成 | 离线迁移 |

## 5. 验证命令结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 147 source files | |
| `python -m pytest apps/api/tests -q -p no:cacheprovider` | 118 passed, 1 warning in 0.78s | 105(P2-03) + 13(P2-04) |
| `alembic -c alembic.ini upgrade head` (SQLite) | 成功，创建 alembic_version 表 | |
| `alembic -c alembic.ini downgrade base` (SQLite) | 成功，alembic_version 0 行 | |
| `docker --version` | docker command not found | Docker 不可用 |

## 6. 边界声明

- 未执行 P2-05～P2-14
- 未创建业务表
- 未修改 P0/P1 冻结契约
- 未提交、未推送，等待 Codex 审计
