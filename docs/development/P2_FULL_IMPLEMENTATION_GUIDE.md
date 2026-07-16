# P2 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P2 执行指令和审计追踪资料。P2-01～P2-14 已在 2026-07-16 完成并进入 Codex 全量审计；后续新任务不得把本文当作待执行的当前任务单，应以 `docs/development/DEVELOPMENT_PLAN.md` 的最新进度和 Codex 审计结论为准。

## 0. 项目背景

项目名称：CampusAgent

项目路径：

```text
/root/CampusAgent
```

当前分支：

```text
main
```

当前基准提交：

```text
5124c09 docs(project): record remote CI completion
```

远程仓库：

```text
git@github.com:SWFann/CampusAgent.git
```

当前状态：

- P0 契约已冻结。
- P1 工程骨架已完成。
- R1-32～R1-36 已由 Codex 收口并推送至 `origin/main`。
- R3-25/R4-19 已观察到远端 GitHub Actions 绿色。
- 后续开发都以 `/root/CampusAgent` 为基准。

当前 P2 状态：

- P2-01 Docker Compose 基线已通过 Codex 审计。
- P2-02 配置对象已通过 Codex 审计。
- P2-03 PostgreSQL 接入已完成 Codex 整改审计。
- P2-04～P2-14 已由 Claude 执行完成，当前等待 Codex 全量审计、修复和提交。
- 当前工作树已有 P2-01～P2-14 未提交修改，必须完整保留，不得回滚、删除或覆盖。

P0/P1 权威口径：

- API 契约：`v1.0-frozen`
- HTTP API：68 MVP + 3 internal = 71 个总文档化端点
- WebSocket 契约：`v1.0-frozen`
- 威胁模型：T-01～T-09，共 9 个威胁
- 控制状态：`planned=9 / implemented=0 / verified=0`
- 隐私测试：`defined=100 / not_run=100`

禁止：

- 不修改 P0/P1 冻结契约，除非先记录新审计问题并停止等待确认。
- 不修改 `docs/api/API_CONTRACT.md`。
- 不修改 `docs/api/WEBSOCKET_CONTRACT.md`。
- 不修改 `docs/security/THREAT_MODEL.md`。
- 不修改 `docs/privacy/PRIVACY_TEST_MATRIX.md`。
- 不把 `planned` 控制写成 `implemented` 或 `verified`。
- 不新增、删除或重编号隐私测试 ID。
- 不提交。
- 不推送。

## 1. 必读文件

开始前必须阅读：

1. `docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md`
2. `docs/project/README.md`
3. `docs/project/P0_P1_REMEDIATION_PLAN.md`
4. `docs/development/DEVELOPMENT_PLAN.md`
5. `README.md`
6. `.env.example`
7. `compose.yaml`
8. `apps/api/src/config.py`
9. `apps/api/src/main.py`
10. `apps/api/src/dependencies.py`
11. `apps/api/src/middleware/env_validation.py`
12. `apps/api/tests/conftest.py`
13. `development-logs/in-progress/P2-01-compose.md`
14. `development-logs/in-progress/P2-02-config-object.md`
15. `development-logs/in-progress/P2-03-postgresql.md`，如果已存在

阅读后先确认：

- 当前路径是 `/root/CampusAgent`。
- 当前分支是 `main`。
- P2-01～P2-14 修改仍然存在。
- P2-03 PostgreSQL DBAPI 驱动问题已通过 `psycopg2-binary` 整改。
- Docker 在当前机器可能不可用，不要因为 Docker 不可用而跳过非 Docker 测试。
- 所有任务完成后不提交、不推送，等待 Codex 审计。

## 2. P2 总目标

P2 阶段名称：基础设施与后端公共内核

P2 总目标：

- Docker Compose 基线
- 分环境安全配置
- PostgreSQL engine/session
- Alembic 迁移基线
- Redis 客户端
- API Envelope
- 请求上下文中间件
- 敏感日志过滤
- 时间和 ID 工具
- 领域事件总线
- Repository / Unit of Work 基线
- 测试数据库夹具
- OpenAPI 导出基线
- 基础可观测性

P2 完成后必须满足：

- 后端可 import。
- 后端测试通过。
- 前端 lint/typecheck/test/build 不被破坏。
- 不依赖真实生产密钥。
- 日志不泄露 secret / token / prompt / 私有内容。
- Docker 不可用时，所有非 Docker 可验证项必须通过。
- P2-03～P2-14 均有开发日志。
- `docs/development/DEVELOPMENT_PLAN.md` 中 P2-01～P2-14 状态准确。
- 不修改 P0/P1 冻结契约。

## 3. 执行方式

必须按顺序执行：

1. P2-03 接入 PostgreSQL
2. P2-04 初始化 Alembic
3. P2-05 接入 Redis
4. P2-06 统一 API Envelope
5. P2-07 请求上下文中间件
6. P2-08 敏感日志过滤
7. P2-09 统一时间与 ID 工具
8. P2-10 领域事件总线
9. P2-11 Repository / Unit of Work 基线
10. P2-12 测试数据库夹具
11. P2-13 OpenAPI 生成基线
12. P2-14 基础可观测性

每个子任务完成时必须：

- 更新或创建对应 development log。
- 增加或更新测试。
- 跑该任务相关测试。
- 不提交。
- 不推送。
- 当前任务自检通过后再进入下一任务。

如果某个任务阻塞：

- 停止继续后续任务。
- 写清阻塞原因。
- 不要绕过。
- 不要靠删除测试通过。

## 4. P2-03：接入 PostgreSQL

当前已知阻塞：

SQLAlchemy PostgreSQL URL 需要 DBAPI 驱动，但项目没有 `psycopg` / `psycopg2` / `asyncpg`。

必须先修复：

- 在 `apps/api/requirements.txt` 增加 `psycopg2-binary`。
- 在 `apps/api/requirements.lock` 增加锁定版本。
- 当前 conda 环境安装 `requirements.lock`。

建议版本：

- 使用 pip 能解析的稳定版本，例如 `psycopg2-binary==2.9.11` 或当前 pip resolver 选出的版本。必须写入 lock。

P2-03 目标：

- SQLAlchemy engine factory
- sessionmaker factory
- FastAPI DB session dependency
- PostgreSQL URL 可创建 engine
- 不在 import 时连接数据库
- session 异常 rollback，finally close
- UTC 时间工具
- UUID v4 工具
- `/health/ready` 可检查 database，Redis 仍 `not_configured`

必须验证：

```bash
conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
conda run -n CampusAgent python -m pip check

conda run -n CampusAgent python -c "import sys; sys.path.insert(0, 'apps/api'); from src.config import Settings; from src.db.session import create_engine_from_settings; s=Settings(_env_file=None, DATABASE_URL='postgresql://postgres:postgres@localhost:5432/campus_agent'); print('settings ok'); engine=create_engine_from_settings(s); print('engine ok', engine.url.drivername)"
```

必须新增测试：

- PostgreSQL URL engine 创建成功，不 connect。
- 默认 `create_app` lifespan 不因缺 DBAPI 崩溃。
- `/health/live` 返回 200。
- `/health/ready` 在无真实 Postgres 时返回 `degraded` 或 database `unavailable`，不抛异常。

禁止：

- 不创建业务表。
- 不创建 Alembic 迁移。
- 不做 Redis。
- 不做 API Envelope。

开发日志：

```text
development-logs/in-progress/P2-03-postgresql.md
```

## 5. P2-04：初始化 Alembic

前置：P2-03 通过自检。

目标：建立 Alembic 基线，但不创建业务表。

允许新增：

- `apps/api/alembic.ini` 或其他合理位置，但命令和文档必须一致
- `apps/api/alembic/env.py`
- `apps/api/alembic/script.py.mako`
- `apps/api/alembic/versions/.gitkeep` 或 README
- Makefile `db-migrate` / `db-downgrade` / `db-revision` 命令修正
- migration config tests

要求：

- Alembic 使用 `apps/api/src/db/base.py` 中的 `Base.metadata`。
- 支持从 `Settings.DATABASE_URL` 读取数据库 URL。
- 不自动读取生产数据库。
- 空库回放测试可用 SQLite 或临时 URL。
- 不创建业务表。
- baseline migration 可以为空 migration，或者只建立版本表，必须说明。
- downgrade 策略明确：空 baseline 可 downgrade 到 base。

必须测试：

- Alembic 配置可加载。
- `env.py` 可导入。
- metadata 是 `Base.metadata`。
- 在 SQLite 临时库上 `upgrade head` 成功。
- `downgrade base` 成功。
- 没有业务表被创建。

建议命令：

```bash
conda run -n CampusAgent alembic -c apps/api/alembic.ini upgrade head
conda run -n CampusAgent alembic -c apps/api/alembic.ini downgrade base
```

开发日志：

```text
development-logs/in-progress/P2-04-alembic.md
```

## 6. P2-05：接入 Redis

目标：建立 Redis 客户端基础设施。

允许新增：

- `apps/api/src/cache/redis.py`
- `apps/api/src/cache/__init__.py`
- `apps/api/tests/unit/test_redis_client.py`

要求：

- 使用 redis-py，当前 `requirements.lock` 已有 redis。
- 从 `Settings.REDIS_URL` 读取。
- 不在 import 时连接。
- 提供 client factory。
- 提供 ping/check 函数，失败返回 `unavailable`，不抛给 health endpoint。
- 支持命名空间前缀，例如 `REDIS_NAMESPACE`，默认 `campus_agent`。
- 支持 TTL helper。
- Redis 不可用时，除明确需要 Redis 的功能外，不得导致 app import 失败。
- `/health/ready` 可把 redis 从 `not_configured` 改成 `ok` / `unavailable`。
- 不实现业务缓存。
- 不实现 Pub/Sub 或 Streams 决策。

可新增 Settings：

- `REDIS_NAMESPACE=campus_agent`
- `REDIS_SOCKET_TIMEOUT_SECONDS=5`
- `REDIS_CONNECT_TIMEOUT_SECONDS=5`
- `DEFAULT_CACHE_TTL_SECONDS=300`

必须测试：

- Redis client factory 不连接。
- namespace key helper 正确。
- TTL 值合法校验。
- ping 成功路径可 monkeypatch。
- ping 失败返回 `unavailable`。
- `/health/ready` Redis 不抛异常。

开发日志：

```text
development-logs/in-progress/P2-05-redis.md
```

## 7. P2-06：统一 API Envelope

目标：建立统一响应 envelope 基线，但不要改动所有 API 契约语义。

当前已有 `AppError` handler 返回 `success=false / error / request_id`。

要求：

- 定义标准成功 envelope。
- 定义标准错误 envelope。
- 定义稳定 error code 映射。
- request_id 来自请求上下文。
- 不破坏 `/health/live` 和 `/health/ready` 简单健康响应，除非明确记录健康端点例外。
- 不批量改所有未来 API，只建立工具和 handler。
- 保持现有 tests 通过。

建议新增：

- `apps/api/src/schemas/envelope.py`
- 扩展或保持兼容 `apps/api/src/utils/errors.py`
- `apps/api/tests/unit/test_api_envelope.py`

Envelope 建议：

```json
{
  "success": true,
  "data": {},
  "request_id": "uuid-or-null"
}
```

错误：

```json
{
  "success": false,
  "error": {
    "code": "STABLE_CODE",
    "message": "safe message",
    "details": {}
  },
  "request_id": "uuid-or-null"
}
```

必须测试：

- success envelope 构造。
- error envelope 构造。
- AppError handler 输出稳定。
- request_id 回填。
- 未知异常不泄露内部细节。
- validation error 映射稳定错误码。

开发日志：

```text
development-logs/in-progress/P2-06-api-envelope.md
```

## 8. P2-07：请求上下文中间件

目标：建立 request ID、耗时、actor 摘要、结构化日志上下文。

要求：

- 使用 `X-Correlation-ID` 或 `X-Request-ID`，保持现有 `X-Correlation-ID` 兼容。
- 如果客户端提供合法 UUID，则复用。
- 如果没有提供，则生成 UUID v4。
- `request.state.request_id` 或 `correlation_id` 明确。
- 响应 header 回传。
- 记录请求耗时。
- actor 摘要只能记录非敏感字段，例如 anonymous / user_id hash / role；当前未实现 auth 时只记录 anonymous。
- 不记录 Authorization header、cookie、body、prompt、private data。

建议新增：

- `apps/api/src/middleware/request_context.py`
- `apps/api/src/utils/logging.py`
- `apps/api/tests/unit/test_request_context.py`

必须测试：

- 无 header 生成 request ID。
- 有 `X-Correlation-ID` 回传。
- 非 UUID header 处理策略明确。
- 响应包含 request ID header。
- `request.state` 有 request_id。
- 不记录敏感 header。

开发日志：

```text
development-logs/in-progress/P2-07-request-context.md
```

## 9. P2-08：敏感日志过滤

目标：建立敏感字段 denylist、脱敏器、日志回归测试。

敏感字段至少包括：

- password
- token
- access_token
- refresh_token
- authorization
- cookie
- set-cookie
- secret
- app_secret
- field_encryption_key
- api_key
- model_gateway_api_key
- prompt
- private_preference
- memory_content
- chain_of_thought

建议新增：

- `apps/api/src/utils/redaction.py`
- `apps/api/tests/unit/test_redaction.py`

要求：

- 支持 dict/list/nested dict 脱敏。
- key 大小写不敏感。
- header 脱敏。
- 保留非敏感字段。
- 不修改原对象，返回新对象。
- 日志测试证明敏感值不出现在输出。

开发日志：

```text
development-logs/in-progress/P2-08-sensitive-logging.md
```

## 10. P2-09：统一时间与 ID 工具

P2-03 可能已新增 `utc_now` / `new_uuid`。P2-09 要把它们提升为公共工具并补足可注入能力。

目标：

- Clock 接口 / Protocol
- SystemClock
- FixedClock for tests
- UUIDFactory 或函数注入
- DeterministicUUIDFactory for tests

建议路径：

- `apps/api/src/utils/time.py`
- `apps/api/src/utils/ids.py`

如果保留 `db/time.py` 和 `db/types.py`，必须解释原因。建议迁移到 utils，因为不只是数据库使用。

要求：

- timezone-aware UTC。
- UUID v4 默认。
- 测试可注入固定时间和固定 UUID。
- 不破坏 P2-03 已有导入，必要时保留 re-export。

必须测试：

- SystemClock 返回 aware UTC。
- FixedClock 返回固定值。
- new_uuid v4。
- deterministic factory 顺序输出。
- `db/time.py` 如果保留，应委托公共工具。

开发日志：

```text
development-logs/in-progress/P2-09-time-id.md
```

## 11. P2-10：领域事件总线

目标：建立进程内领域事件发布/订阅基线，支持事务后发布策略的接口，但不绑定业务模块。

建议新增：

- `apps/api/src/events/base.py`
- `apps/api/src/events/bus.py`
- `apps/api/src/events/outbox.py` 或 `deferred.py`，如需要
- `apps/api/tests/unit/test_event_bus.py`

要求：

- DomainEvent 基类/协议：
  - event_id UUID
  - event_type str
  - occurred_at UTC datetime
  - aggregate_id optional
  - payload dict
- InMemoryEventBus：
  - `subscribe(event_type, handler)`
  - `publish(event)`
  - `publish_many(events)`
- handler 异常策略明确：
  - 默认收集错误并继续，或 fail fast；必须测试
- 事务后发布：
  - 提供 PendingEvents / UnitOfWork hook 接口即可
  - 不实现真实 outbox 表，因为尚未业务表/迁移
- 不发布任何真实业务事件。

必须测试：

- 订阅后能收到事件。
- 多 handler 顺序/调用次数。
- 未订阅事件 no-op。
- handler 异常策略。
- event_id 是 UUID。
- occurred_at 是 UTC aware。
- pending events 可 collect/clear。

开发日志：

```text
development-logs/in-progress/P2-10-event-bus.md
```

## 12. P2-11：Repository / Unit of Work 基线

目标：建立 repository/uow 接口和事务用法基线，不实现业务仓库。

建议新增：

- `apps/api/src/db/repository.py`
- `apps/api/src/db/uow.py`
- `apps/api/tests/unit/test_uow.py`

要求：

- Repository Protocol 或 BaseRepository 泛型。
- UnitOfWork 管理 session。
- commit / rollback / close。
- 支持收集 pending domain events。
- 与 P2-10 event bus 留接口。
- 不创建业务表。
- 不创建业务 repository。
- 不过度抽象。

必须测试：

- UoW 正常退出可 commit 或按设计不自动 commit，必须清楚。
- 异常退出 rollback。
- close 总会执行。
- pending events 可收集。
- commit 后可返回待发布事件或 clear，策略明确。
- 与 SQLAlchemy session mock/SQLite session 兼容。

开发日志：

```text
development-logs/in-progress/P2-11-repository-uow.md
```

## 13. P2-12：测试数据库夹具

目标：建立测试数据库夹具，为后续 P3+ 数据库测试提供隔离事务、迁移测试、Redis fixture 基线。

允许修改：

- `apps/api/tests/conftest.py`
- `apps/api/tests/fixtures/` 或 `apps/api/tests/support/`
- tests for fixtures

要求：

- 默认 unit tests 不依赖真实 Postgres。
- 提供 SQLite in-memory fixture。
- 提供 db_engine fixture。
- 提供 db_session fixture。
- 每个测试隔离事务或重建 schema。
- 提供 migration test helper，但不必须真实业务表。
- Redis fixture 可用 fake class，不依赖真实 Redis。
- 不要求 Docker。

必须测试：

- 两个测试之间数据库状态隔离。
- db_session 可执行 `SELECT 1`。
- fixture close/rollback。
- fake redis set/get/ttl 基础行为或 ping fake。
- 不污染全局 Settings。

开发日志：

```text
development-logs/in-progress/P2-12-test-db-fixtures.md
```

## 14. P2-13：OpenAPI 生成基线

目标：建立 OpenAPI schema 导出、差异检查、前端客户端生成的基线。

考虑当前项目还没有完整业务 API，不要声称契约实现完成。

建议新增：

- `scripts/export_openapi.py` 或 `apps/api/scripts/export_openapi.py`
- `docs/generated/openapi.json`
- `apps/api/tests/unit/test_openapi_export.py`

要求：

- 能导出当前 FastAPI app OpenAPI。
- 输出路径固定，例如 `docs/generated/openapi.json`。
- 导出内容稳定排序。
- CI 可运行检查：生成后 diff 不应变化。
- 不改 `API_CONTRACT.md` 的冻结契约。
- 前端客户端生成可以先建立命令占位，但如果不真实生成，不能标成已完成。更好是只生成 schema，不生成客户端，把客户端生成记录为后续任务。
- P2-13 完成标准至少是 Schema 导出和差异检查。

必须测试：

- export 脚本可执行。
- openapi 包含 `/health/live` 和 `/health/ready`。
- schema 有 title/version。
- 重复导出稳定。

Makefile 可新增：

- `openapi-export`
- `openapi-check`

开发日志：

```text
development-logs/in-progress/P2-13-openapi-baseline.md
```

## 15. P2-14：基础可观测性

目标：建立请求量、延迟、错误率、数据库池指标基础，不含敏感标签。

不要引入复杂 Prometheus 服务，除非轻量且测试稳定。

建议实现：

- `apps/api/src/observability/metrics.py`
- `apps/api/src/middleware/metrics.py`
- `/internal/metrics` 或 `/metrics` 路由，注意是否 internal
- `apps/api/tests/unit/test_metrics.py`

要求：

- 记录 request count。
- 记录 latency。
- 记录 error count。
- database health/pool 指标可暴露基础状态。
- 标签不得包含 user input、path param 原文、token、prompt、私有数据。
- route 标签应使用模板路径或归一化 path。
- 不泄露 query string。
- 指标端点不需要认证可先作为 local/internal，但必须文档说明后续生产要保护。

可选依赖：

- `prometheus-client`

如果新增依赖，必须更新 `requirements.txt` / `requirements.lock` 并 pip install。

如果不用依赖，也可实现简单内存指标和 JSON endpoint。

必须测试：

- 请求后计数增加。
- 500 错误计数增加。
- latency 有记录。
- query string 不进入标签。
- Authorization header 不进入指标。
- 指标 endpoint 返回非敏感内容。

开发日志：

```text
development-logs/in-progress/P2-14-observability.md
```

## 16. P2 完成后的总收口

完成 P2-03～P2-14 后，必须更新：

1. `docs/development/DEVELOPMENT_PLAN.md`
   - P2-01～P2-14 全部 `[x]`
   - P2 阶段状态更新为“完成，等待 Codex 审计”
   - P3 仍未开始

2. 新建：

```text
development-logs/in-progress/P2-COMPLETION-SUMMARY.md
```

P2 summary 必须包含：

- 每个 P2 子任务状态
- 修改文件总览
- 新增模块说明
- 新增依赖说明
- 所有自检命令结果
- Docker 是否可用
- 未执行项
- 风险清单
- 明确未提交、未推送

## 17. 全量自检命令

P2 完成后必须执行：

```bash
cd /root/CampusAgent

git status --short --branch
git diff HEAD --check

conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
conda run -n CampusAgent python -m pip check

conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider

DEBUG=release conda run -n CampusAgent python -c "import sys; sys.path.insert(0, 'apps/api'); import src.main; print('API_IMPORT_OK')"

corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build

python - <<'PY'
from pathlib import Path
from collections import Counter

keys = []
for line in Path(".env.example").read_text().splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    keys.append(stripped.split("=", 1)[0])

counts = Counter(keys)
assert counts["APP_ENV"] == 1, counts
assert counts["APP_DEBUG"] == 1, counts
assert counts["DEBUG"] == 0, counts
print("ENV_EXAMPLE_KEYS_OK")
PY
```

如果 Docker 可用：

```bash
docker compose config
docker compose up -d postgres redis mock-model
docker compose ps
docker compose exec postgres pg_isready -U postgres -d campus_agent
docker compose exec redis redis-cli ping
curl -f http://localhost:8001/health/live
docker compose down
```

如果 Docker 不可用：

- 写明 `docker --version` 失败。
- 写明未执行 Docker 实跑。

## 18. 最终完成报告格式

完成全部 P2 后，按以下格式报告：

```text
P2 完整完成报告

1. 基准信息
- 项目路径：
- 当前分支：
- 基准提交：
- 是否保留 P2-01/P2-02 修改：

2. P2 子任务状态
| 任务 | 状态 | 日志路径 | 说明 |
|---|---|---|---|

3. 修改文件总览
| 文件 | 操作 | 属于任务 | 说明 |
|---|---|---|---|

4. 新增依赖
| 依赖 | 版本 | 原因 |
|---|---|---|

5. 后端基础设施说明
- PostgreSQL：
- Alembic：
- Redis：
- API Envelope：
- Request Context：
- Redaction：
- Time/ID：
- Event Bus：
- Repository/UoW：
- Test Fixtures：
- OpenAPI：
- Observability：

6. 验证命令结果
| 命令 | 结果 | 备注 |
|---|---|---|

7. Docker 验证
- Docker 是否可用：
- 执行了哪些命令：
- 未执行原因：

8. 边界声明
- 未开始 P3
- 未创建业务表
- 未实现 Auth/User/Organization/Conversation 等业务模块
- 未修改 P0/P1 冻结契约
- 未修改 API_CONTRACT.md / WEBSOCKET_CONTRACT.md / THREAT_MODEL.md / PRIVACY_TEST_MATRIX.md
- 未提交、未推送，等待 Codex 全量审计

9. 风险和待 Codex 重点审计项
- 列出你认为最需要审计的 5～10 个点

10. git status --short
粘贴完整输出
```

## 19. 最重要的边界

可以完成整个 P2，但不能跨入 P3。

P3 包括 Auth、User、StudentProfile、注册、登录、刷新、注销等，全部禁止。

如果某个 P2 任务为了测试需要示例对象，只能使用测试内局部 fake/model，不得引入正式业务模型或迁移。

不要提交，不要推送。完成后等待 Codex 审计。
