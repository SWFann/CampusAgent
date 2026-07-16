---
task_id: P2-05
task_name: 接入 Redis
status: in_review
started_at: 2026-07-16T20:00:00+08:00
completed_at: 2026-07-16T20:40:00+08:00
actual_hours: 0.67
owner: Claude
auditor: Codex
---

# P2-05: 接入 Redis

## 1. 背景

- P2-01～P2-04 已完成。
- 当前路径：`/root/CampusAgent`
- 当前分支：`main`，基准提交 `5124c09`
- P2-01～P2-04 未提交修改完整保留。
- 本次任务只做 P2-05：Redis 客户端基础设施。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/config.py` | 修改 | 新增 REDIS_NAMESPACE、REDIS_SOCKET_TIMEOUT_SECONDS、REDIS_CONNECT_TIMEOUT_SECONDS、DEFAULT_CACHE_TTL_SECONDS 字段及校验 |
| `apps/api/src/cache/__init__.py` | 新增 | cache 包初始化 |
| `apps/api/src/cache/redis.py` | 新增 | Redis client factory、ping_redis、namespaced_key、validate_ttl |
| `apps/api/src/main.py` | 修改 | lifespan 创建/关闭 Redis client；/health/ready 接入 Redis 检查 |
| `.env.example` | 修改 | 补充 Redis namespace/timeout/TTL 配置 |
| `compose.yaml` | 修改 | api.environment 补充 Redis 配置环境变量 |
| `apps/api/tests/unit/test_redis_client.py` | 新增 | 18 个测试覆盖 client factory、namespace、TTL、ping、health ready |
| `apps/api/tests/unit/test_config.py` | 修改 | _SETTINGS_ENV_VARS 补充 Redis 字段 |

## 3. Redis 设计说明

### 3.1 Client Factory

`create_redis_client(settings: Settings) -> redis.Redis`

- 使用 `redis.Redis.from_url()` 创建客户端
- `decode_responses=True`：字符串解码
- `socket_timeout` 和 `socket_connect_timeout` 从 Settings 读取
- **不在创建时连接**：连接是惰性的，首次执行命令时才建立

### 3.2 Ping 健康检查

`ping_redis(client: redis.Redis | None) -> dict[str, Any]`

- 执行 `client.ping()`
- 成功返回 `{"status": "ok"}`
- 失败返回 `{"status": "unavailable", "error": str(e)}`
- **不抛异常**：所有异常被捕获并返回 unavailable 状态
- client 为 None 时返回 unavailable

### 3.3 Namespace 前缀

`namespaced_key(settings: Settings, key: str) -> str`

- 格式：`{namespace}:{key}`
- namespace 从 Settings.REDIS_NAMESPACE 读取
- 自动 strip 空白

### 3.4 TTL Helper

`validate_ttl(settings: Settings, ttl: int | None = None) -> int`

- ttl 为 None/0/负数时使用 DEFAULT_CACHE_TTL_SECONDS
- 返回正整数 TTL

### 3.5 Health Readiness 集成

- lifespan 中创建 Redis client 并存入 `app.state.redis_client`
- `/health/ready` 调用 `ping_redis(client)` 检查 Redis 状态
- Redis 不可用时返回 `redis: unavailable`，不抛异常
- Redis 未配置时返回 `redis: not_configured`
- 关闭时调用 `redis_client.close()`

## 4. 新增 Settings 字段

| 字段 | 类型 | 默认值 | 校验 |
|---|---|---|---|
| REDIS_NAMESPACE | str | campus_agent | 非空 |
| REDIS_SOCKET_TIMEOUT_SECONDS | float | 5.0 | > 0 |
| REDIS_CONNECT_TIMEOUT_SECONDS | float | 5.0 | > 0 |
| DEFAULT_CACHE_TTL_SECONDS | int | 300 | > 0 |

## 5. 新增测试列表

| 测试类 | 用例数 | 覆盖点 |
|---|---|---|
| TestRedisClientFactory | 3 | 不连接创建、URL 正确、decode_responses |
| TestNamespacedKey | 4 | 默认/自定义/空/strip |
| TestValidateTtl | 5 | None/0/负/显式/非法默认 |
| TestPingRedis | 4 | 成功/失败/None/False |
| TestHealthReadyRedis | 2 | unavailable/ok(mock) |

## 6. 验证命令结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 150 source files | |
| `python -m pytest apps/api/tests -q -p no:cacheprovider` | 136 passed, 1 warning in 0.71s | 118(P2-04) + 18(P2-05) |
| `docker --version` | docker command not found | Docker 不可用 |

## 7. 边界声明

- 未执行 P2-06～P2-14
- 未实现业务缓存
- 未实现 Pub/Sub 或 Streams
- 未修改 P0/P1 冻结契约
- 未提交、未推送，等待 Codex 审计
