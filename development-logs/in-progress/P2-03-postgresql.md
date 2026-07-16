---
task_id: P2-03
task_name: 接入 PostgreSQL
status: in_review
started_at: 2026-07-16T17:30:00+08:00
completed_at: 2026-07-16T18:30:00+08:00
actual_hours: 1.0
owner: Claude
auditor: Codex
---

# P2-03: 接入 PostgreSQL

## 1. 背景

- P2-01 Docker Compose 基线已通过 Codex 审计。
- P2-02 配置对象已通过 Codex 审计。
- 当前路径：`/root/CampusAgent`
- 当前分支：`main`，基准提交 `5124c09 docs(project): record remote CI completion`
- P2-01/P2-02 未提交修改完整保留。
- 本次任务只做 P2-03：接入 PostgreSQL 数据库连接底座。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/config.py` | 修改 | 新增 DB_POOL_SIZE、DB_MAX_OVERFLOW、DB_POOL_TIMEOUT_SECONDS、DB_POOL_RECYCLE_SECONDS、DB_ECHO_SQL 字段及校验 |
| `apps/api/src/db/__init__.py` | 新增 | db 包初始化 |
| `apps/api/src/db/base.py` | 新增 | DeclarativeBase，为 P2-04 Alembic 预留 |
| `apps/api/src/db/session.py` | 新增 | engine factory、sessionmaker factory、get_db_session、check_database_connection |
| `apps/api/src/db/time.py` | 新增 | utc_now() 返回 timezone-aware UTC datetime |
| `apps/api/src/db/types.py` | 新增 | new_uuid() 返回 UUID v4、uuid_to_str() |
| `apps/api/src/main.py` | 修改 | lifespan 创建/销毁 engine 和 sessionmaker；/health/ready 接入数据库检查 |
| `apps/api/src/dependencies.py` | 修改 | 新增 get_db_session FastAPI dependency |
| `.env.example` | 修改 | 补充 DB pool 配置字段 |
| `compose.yaml` | 修改 | api.environment 补充 DB pool 环境变量 |
| `apps/api/tests/unit/test_db_session.py` | 新增 | 22 个测试覆盖 Settings DB 字段、engine factory、sessionmaker、get_db_session、check_database_connection |
| `apps/api/tests/unit/test_db_utils.py` | 新增 | 10 个测试覆盖 utc_now 和 UUID 工具 |
| `apps/api/tests/unit/test_config.py` | 修改 | _SETTINGS_ENV_VARS 和 .env.example 对齐测试补充 DB 字段 |

## 3. DB engine/session 设计说明

### Engine factory

`create_engine_from_settings(settings: Settings) -> Engine`

- SQLite URL：使用 `StaticPool` + `check_same_thread=False`，支持 `:memory:` 测试
- PostgreSQL URL：使用连接池参数（pool_size、max_overflow、pool_timeout、pool_recycle），`pool_pre_ping=True` 惰性验证连接
- **不在 import 时连接数据库**：engine 创建时不发起连接，首次 checkout 时才验证

### Sessionmaker factory

`create_sessionmaker(engine: Engine) -> sessionmaker[Session]`

- `expire_on_commit=False`：commit 后对象仍可用
- 绑定到传入的 engine

### Dependency

`get_db_session(request: Request) -> Iterator[Session]`（在 `dependencies.py`）

- 从 `request.app.state.db_sessionmaker` 获取 sessionmaker
- yield session
- 异常时 rollback
- finally close

### Import 时是否连接

否。engine 在 lifespan 中创建，但 `pool_pre_ping=True` 确保首次使用才验证连接。

## 4. 事务边界说明

- **正常路径**：yield session → 调用方使用 session → 调用方显式 `session.commit()`（如需要）→ finally `session.close()`
- **异常路径**：异常传播 → `session.rollback()` → re-raise → finally `session.close()`
- **close 策略**：`finally` 块中始终 `session.close()`
- **是否自动 commit**：否。服务层或 repository 显式 commit。当前无业务写入。

## 5. UTC/UUID 约定

### utc_now

- `utc_now() -> datetime`
- 返回 `datetime.now(UTC)`，timezone-aware
- 所有数据库时间字段统一使用此函数

### new_uuid

- `new_uuid() -> UUID`
- 返回 `uuid4()`，UUID v4
- API request_id 仍由现有中间件生成，不改变契约

## 6. Health readiness 行为

### database

- lifespan 中创建 engine 并存入 `app.state.db_engine`
- `/health/ready` 调用 `check_database_connection(engine)` 执行 `SELECT 1`
- 连接成功：`database: ok`
- 连接失败：`database: unavailable`（不抛异常，安全返回）
- engine 未初始化：`database: not_configured`

### redis

- 仍为 `not_configured`，因为 P2-05 未执行

### 是否依赖真实 Postgres

否。单元测试使用 SQLite `:memory:`。`/health/ready` 在无数据库时返回 `degraded` 而非崩溃。

## 7. 新增测试列表

| 测试文件 | 用例 | 覆盖点 |
|---|---|---|
| `test_db_session.py` | `TestDbSettingsDefaults` (5 cases) | DB pool 默认值合法 |
| `test_db_session.py` | `TestDbSettingsValidation` (6 cases) | 非法 pool 值失败、production DB_ECHO_SQL 校验 |
| `test_db_session.py` | `TestEngineFactory::test_engine_not_connected_on_creation` | engine 创建不连接 |
| `test_db_session.py` | `TestEngineFactory::test_sqlite_memory_engine` | SQLite 内存库可用 |
| `test_db_session.py` | `TestEngineFactory::test_engine_echo_flag` | echo 标志 |
| `test_db_session.py` | `TestSessionmaker` (3 cases) | sessionmaker 创建、Session 类型、expire_on_commit |
| `test_db_session.py` | `TestGetDbSession::test_session_is_closed_after_normal_use` | 正常完成后 close |
| `test_db_session.py` | `TestGetDbSession::test_session_rollback_on_exception` | 异常时 rollback + close |
| `test_db_session.py` | `TestGetDbSession::test_get_db_session_without_factory_raises` | 无 factory 报错 |
| `test_db_session.py` | `TestCheckDatabaseConnection::test_check_returns_ok_for_sqlite` | 连接检查成功 |
| `test_db_session.py` | `TestCheckDatabaseConnection::test_check_returns_unavailable_for_bad_url` | 连接检查失败安全返回 |
| `test_db_utils.py` | `TestUtcNow` (4 cases) | 返回 datetime、timezone-aware、UTC、偏移为零 |
| `test_db_utils.py` | `TestNewUuid` (3 cases) | UUID 实例、v4、唯一性 |
| `test_db_utils.py` | `TestUuidToStr` (3 cases) | 字符串、匹配 str()、小写 |

## 8. 验证命令结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 146 source files | |
| `python -m pytest apps/api/tests -q -p no:cacheprovider` | 98 passed in 0.41s | |
| `DEBUG=release python -c "...import src.main..."` | API_IMPORT_OK | 关键复现命令 |
| `corepack pnpm lint` | All checks passed! | |
| `corepack pnpm typecheck` | Success: no issues found in 146 source files | |
| `corepack pnpm test` | 98 passed (API) + 2 passed (Web) | |
| `docker --version` | Command 'docker' not found | Docker 不可用，未执行 Docker 实跑 |

## 9. 边界声明

- 未执行 P2-04 Alembic
- 未执行 P2-05 Redis
- 未执行 P2-06 API Envelope
- 未创建业务表
- 未修改 P0/P1 冻结契约
- 未提交、未推送，等待 Codex 审计

---

## 10. Codex 审计整改（第一次）

### 10.1 阻塞问题

Codex 审计发现：项目缺少 PostgreSQL DBAPI 驱动（`psycopg2`），导致以下命令失败：

```bash
python -c "...from src.db.session import create_engine_from_settings; ..."
# ModuleNotFoundError: No module named 'psycopg2'
```

FastAPI lifespan 也会因同一原因崩溃。

### 10.2 整改措施

#### 10.2.1 补充 PostgreSQL DBAPI 依赖

- 在 `apps/api/requirements.txt` 新增 `psycopg2-binary>=2.9.0`
- 在 `apps/api/requirements.lock` 新增 `psycopg2-binary==2.9.12`（按字母序插入 `pluggy` 与 `pydantic` 之间）
- 在 conda 环境 `CampusAgent` 安装 `psycopg2-binary==2.9.12`
- `pip check` 确认无冲突

选择 `psycopg2-binary` 而非 psycopg v3 的原因：当前 URL 使用 `postgresql://...`，SQLAlchemy 默认查找 psycopg2，最小改动方案。

#### 10.2.2 新增 PostgreSQL URL engine 创建测试

在 `apps/api/tests/unit/test_db_session.py` 新增 `TestPostgresqlEngineCreation` 测试类（4 个用例）：

| 用例 | 覆盖点 |
|---|---|
| `test_postgresql_engine_created_without_connect` | `postgresql://` URL 可成功创建 Engine，`drivername == "postgresql"`，证明 psycopg2 DBAPI 已安装 |
| `test_postgresql_engine_does_not_connect_on_creation` | engine 创建不触发连接，`checkedout() == 0` |
| `test_postgresql_engine_pool_pre_ping` | PostgreSQL engine 使用 `pool_pre_ping=True` |
| `test_postgresql_engine_echo_flag` | `DB_ECHO_SQL=true` 传播到 engine.echo |

这些测试不依赖真实 PostgreSQL 服务，仅验证 engine 创建路径。

#### 10.2.3 新增 lifespan 默认配置测试

在 `apps/api/tests/unit/test_app_factory.py` 新增 `TestLifespanWithPostgresqlUrl` 测试类（3 个用例）：

| 用例 | 覆盖点 |
|---|---|
| `test_lifespan_postgresql_health_live_ok` | lifespan 启动后 `/health/live` 返回 200 |
| `test_lifespan_postgresql_health_ready_degraded` | `/health/ready` 返回 `degraded`，`database: unavailable`（不抛异常） |
| `test_lifespan_default_postgresql_url` | 默认 Settings（postgresql:// URL）下 lifespan 不崩溃，health 正常响应 |

这些测试证明：即使没有真实 PostgreSQL 服务，lifespan 也能正常启动并响应健康检查。

### 10.3 修改文件列表（本次整改）

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/requirements.txt` | 修改 | 新增 `psycopg2-binary>=2.9.0` |
| `apps/api/requirements.lock` | 修改 | 新增 `psycopg2-binary==2.9.12` |
| `apps/api/tests/unit/test_db_session.py` | 修改 | 新增 `TestPostgresqlEngineCreation` 测试类（4 个用例） |
| `apps/api/tests/unit/test_app_factory.py` | 修改 | 新增 `TestLifespanWithPostgresqlUrl` 测试类（3 个用例）、`_make_settings` helper |

### 10.4 PostgreSQL DBAPI 依赖版本

- `psycopg2-binary==2.9.12`
- 安装位置：conda 环境 `CampusAgent`

### 10.5 关键复现命令结果

```bash
# 命令 1：PostgreSQL engine 创建
python -c "...from src.db.session import create_engine_from_settings; s=Settings(_env_file=None, DATABASE_URL='postgresql://...'); engine=create_engine_from_settings(s); print('engine ok', engine.url.drivername)"
# 输出：
# settings ok
# engine ok postgresql

# 命令 2：lifespan 默认配置
APP_DEBUG=false python /tmp/verify_lifespan.py
# 输出：
# created
# 200 {'status': 'degraded', 'service': 'CampusAgent API', 'checks': {'database': 'unavailable', 'redis': 'not_configured'}}

# 命令 3：P2-02 回归
DEBUG=release python -c "...import src.main; print('API_IMPORT_OK')"
# 输出：API_IMPORT_OK
```

### 10.6 完整自检命令结果

| 命令 | 结果 |
|---|---|
| `git status --short --branch` | `## main...origin/main`（未提交） |
| `git diff HEAD --check` | 无错误 |
| `pip install -r apps/api/requirements.lock` | 所有依赖已满足 |
| `pip check` | No broken requirements found. |
| `ruff check apps/api --no-cache` | All checks passed! |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 146 source files |
| `pytest apps/api/tests -q -p no:cacheprovider` | 105 passed, 1 warning in 0.51s |
| `corepack pnpm lint` | All checks passed! |
| `corepack pnpm typecheck` | Success: no issues found in 146 source files |
| `corepack pnpm test` | 105 passed (API) + 2 passed (Web) |
| `corepack pnpm --filter @campus-agent/web build` | 构建成功 |
| `docker --version` | docker command not found |

### 10.7 边界声明（本次整改）

- 未执行 P2-04 Alembic
- 未执行 P2-05 Redis
- 未执行 P2-06 API Envelope
- 未创建业务表
- 未修改 P0/P1 冻结契约
- 未提交、未推送
