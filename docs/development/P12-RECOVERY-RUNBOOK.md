# P12 Recovery Runbook

> 本手册描述 CampusAgent 在比赛演示和日常运维中遇到常见故障时的恢复操作。
> 对应 P12-13 恢复演练（`scripts/ops/recovery_drill.py`）。
>
> **适用范围**：development / test 环境。生产环境恢复需要额外审批，不在 P12 范围内。

## 0. 快速索引

| 场景 | 章节 | 关键命令 |
| --- | --- | --- |
| 服务整体不可用 | §1 | `curl /health/live` |
| 数据库不可用 | §2 | `curl /health/ready` |
| Redis 不可用 | §3 | `curl /health/ready` |
| 模型网关不可用 | §4 | `curl /internal/v1/model/health` |
| 演示数据损坏 | §5 | `python scripts/ops/recovery_drill.py --skip ...` |
| 过期数据堆积 | §6 | `python scripts/ops/cleanup_expired.py --dry-run` |
| 日志收集 | §7 | `docker compose logs` / `journalctl` |
| 紧急回滚 | §8 | `git revert` / `docker compose down` |

## 1. 确认服务状态

### 1.1 Liveness 探针

```bash
curl -s http://localhost:8000/health/live
# 期望: {"status":"ok","service":"CampusAgent API"}
```

- `/health/live` **不依赖**数据库或 Redis。
- 只要进程活着就返回 `ok`。
- 如果 `/health/live` 超时或 502，说明进程已崩溃或被 OOM Kill，需要重启。

### 1.2 Readiness 探针

```bash
curl -s http://localhost:8000/health/ready | python -m json.tool
```

期望输出：

```json
{
  "status": "ready",
  "service": "CampusAgent API",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

- `status=ready`：全量就绪，可接流量。
- `status=degraded`：部分依赖不可用，需进入 §2 或 §3 排查。
- `checks.database` / `checks.redis` 取值：
  - `ok`：正常
  - `unavailable`：连接失败
  - `not_configured`：未初始化（常见于启动早期或测试环境）

### 1.3 Metrics 面板

```bash
curl -s http://localhost:8000/metrics          # 应用 metrics
curl -s http://localhost:8000/metrics/model-gateway  # 模型网关 metrics
```

- `/metrics` 返回 Prometheus 文本格式。
- `/metrics/model-gateway` 返回模型调用计数、延迟、错误、provider 健康。
- **安全约束**：metrics 文本不得包含 `APP_SECRET`、`Bearer `、`sk-`、`field_encryption_key` 等敏感模式。P12-12 测试 `test_metrics_no_secret_patterns` 已验证。

## 2. 数据库不可用

### 2.1 症状

- `/health/ready` 返回 `degraded`，`checks.database=unavailable`。
- API 返回 500 或 `INTERNAL_ERROR`。
- 日志出现 `sqlalchemy.exc.OperationalError`。

### 2.2 恢复步骤

1. **确认数据库进程**：
   ```bash
   # Docker 环境
   docker compose ps postgres
   docker compose logs --tail=50 postgres
   ```
2. **重启数据库**：
   ```bash
   docker compose restart postgres
   ```
3. **等待健康**：
   ```bash
   # 轮询直到 ready
   until curl -s http://localhost:8000/health/ready | grep -q '"database":"ok"'; do
     echo "waiting for database...";
     sleep 2;
   done
   ```
4. **验证主路径**：
   ```bash
   curl -s http://localhost:8000/api/v1/health/ready
   ```
5. **演练验证**（可选，不依赖 Docker）：
   ```bash
   python scripts/ops/recovery_drill.py
   # database-unavailable drill 验证 degraded 行为
   ```

### 2.3 数据一致性检查

数据库恢复后，如果怀疑数据损坏：

```bash
# 检查 demo 数据完整性（仅 development/test）
curl -s -X POST http://localhost:8000/api/v1/internal/demo/reset   # 先登录获取 cookie
curl -s -X POST http://localhost:8000/api/v1/internal/demo/seed
```

- `reset_demo` 只删除 demo 命名空间数据，不影响真实用户。
- `seed_demo` 是幂等的，可安全重复执行。
- 生产环境 demo 路由不挂载，`assert_demo_env` 会 fail-closed。

## 3. Redis 不可用

### 3.1 症状

- `/health/ready` 返回 `degraded`，`checks.redis=unavailable` 或 `not_configured`。
- 缓存命中率下降，API 延迟上升，但主路径仍可用（Redis 不可用不阻断核心流程）。
- `/health/live` 仍返回 `ok`。

### 3.2 恢复步骤

1. **确认 Redis 进程**：
   ```bash
   docker compose ps redis
   docker compose logs --tail=50 redis
   ```
2. **重启 Redis**：
   ```bash
   docker compose restart redis
   ```
3. **验证**：
   ```bash
   curl -s http://localhost:8000/health/ready | grep '"redis"'
   ```
4. **演练验证**：
   ```bash
   python scripts/ops/recovery_drill.py
   # redis-unavailable drill 验证 degraded 但 health/live=ok
   ```

### 3.3 降级运行

如果 Redis 短期内无法恢复：
- 应用可继续运行，缓存穿透到数据库。
- 监控数据库连接池水位（`/metrics` 中的 `db_pool_*`）。
- 不要为了恢复 Redis 而重启应用进程——缓存预热成本高于降级运行。

## 4. 模型网关不可用

### 4.1 症状

- `/internal/v1/model/health` 返回 503 或 degraded 状态。
- `/metrics/model-gateway` 中 `provider_health` 显示 OFFLINE。
- 聚餐场景生成、Agent 对话返回 `MODEL_TIMEOUT` 或 `EXTERNAL_PROVIDER_ERROR`。
- 前端页面不白屏（错误边界捕获），显示降级提示。

### 4.2 恢复步骤

1. **确认模型节点状态**：
   ```bash
   # 管理后台（需 SYSTEM_ADMIN 登录）
   curl -s http://localhost:8000/api/v1/admin/nodes -b cookie.txt
   ```
2. **检查节点健康**：
   - 节点状态 `ONLINE` → 正常。
   - 节点状态 `DEGRADED` → 延迟高但可用。
   - 节点状态 `OFFLINE` → 电路熔断，需检查 vLLM/llama.cpp 进程。
3. **重启模型节点**（在 k8s/实验室平台上，不在本仓库范围）。
4. **验证**：
   ```bash
   curl -s http://localhost:8000/internal/v1/model/health
   curl -s http://localhost:8000/metrics/model-gateway
   ```
5. **演练验证**：
   ```bash
   python scripts/ops/recovery_drill.py
   # model-gateway-unavailable drill 验证 health 不 500
   ```

### 4.3 降级运行

- 如果所有外部模型不可用，`ENABLE_EXTERNAL_MODEL=false` 时路由策略自动拒绝外部调用。
- mock-model 模式下场景生成返回预设结果，不影响演示流程。
- **安全约束**：模型响应进入用户可见结果前必须经过 redaction（P12-05 已验证）。

## 5. 演示数据损坏 / 需要重置

### 5.1 适用场景

- demo 用户无法登录。
- demo 组织/会话/场景数据不一致。
- 演示前需要干净状态。

### 5.2 恢复步骤

1. **登录 SYSTEM_ADMIN 账号**（demo 环境用 `demo_admin@example.com` / `CampusAgentDemo2026!`）。
2. **重置 demo 数据**：
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/internal/demo/reset \
     -b cookie.txt \
     -H "X-CSRF-Token: <csrf-token>"
   ```
   - 只删除 demo 命名空间数据（`demo_` 前缀邮箱、`-demo-lab` 后缀组织）。
   - 非demo数据不受影响。
3. **重新 seed**：
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/internal/demo/seed \
     -b cookie.txt \
     -H "X-CSRF-Token: <csrf-token>"
   ```
4. **验证**：
   ```bash
   curl -s http://localhost:8000/api/v1/internal/demo/status -b cookie.txt
   ```
5. **演练验证**：
   ```bash
   python scripts/ops/recovery_drill.py
   # demo-reset-reseed drill 验证 reset→reseed 循环
   ```

### 5.3 安全约束

- demo 路由只在 `APP_ENV=development|test` 时挂载。
- `assert_demo_env` 在服务层 fail-closed。
- `DEMO_PASSWORD` 是公开常量，**不得**用于生产环境。
- demo 数据全部虚构，不含真实个人信息。

## 6. 过期数据堆积

### 6.1 适用场景

- 过期 refresh token 未清理。
- 过期 private submission 残留。
- 过期 memory 未删除。
- 撤销的 consent 仍存在。

### 6.2 恢复步骤

1. **Dry-run 预览**：
   ```bash
   python scripts/ops/cleanup_expired.py --dry-run --limit 100
   ```
   - 不提交任何变更，只报告将清理的行数。
2. **执行清理**：
   ```bash
   python scripts/ops/cleanup_expired.py --limit 100
   ```
3. **验证主路径**：
   ```bash
   curl -s http://localhost:8000/health/ready
   # 尝试用已过期的 refresh token → 应失败
   ```
4. **演练验证**：
   ```bash
   python scripts/ops/recovery_drill.py
   # cleanup-then-read drill 验证清理后主路径仍可用
   ```

### 6.3 清理范围

清理脚本处理以下数据，**不**删除用户、组织或会话：

| 数据类型 | 清理条件 | 函数 |
| --- | --- | --- |
| 场景实例 | 超过 TTL 且处于非终态 | `expire_stale_instances` |
| 私有提交 | 超过 `PRIVATE_SCENE_TTL_HOURS` | `cleanup_expired_submissions` |
| 记忆项 | `expires_at` 已过期 | `cleanup_expired_memories` |
| 已撤销同意 | `revoked_at` 非空 | `cleanup_revoked_consents` |

## 7. 日志收集

### 7.1 Docker 环境

```bash
# 全部服务日志（最近 200 行）
docker compose logs --tail=200

# 单个服务
docker compose logs --tail=200 api
docker compose logs --tail=200 postgres
docker compose logs --tail=200 redis

# 带时间范围
docker compose logs --since 30m api

# 导出到文件
docker compose logs --tail=1000 api > /tmp/api-logs.txt 2>&1
```

### 7.2 结构化日志格式

CampusAgent 使用 JSON 结构化日志，每行包含：

```json
{
  "timestamp": "2026-07-18T07:36:44.557Z",
  "level": "INFO",
  "logger": "campus_agent.request",
  "message": "request.end",
  "request_id": "ffd52f89-...",
  "method": "GET",
  "path": "/health/live",
  "status_code": 200,
  "duration_ms": 0.39,
  "actor": "anonymous"
}
```

### 7.3 日志脱敏约束

**以下内容不得出现在日志中**（P12-06 已验证）：

- `Authorization` header
- `Cookie` / `Set-Cookie` header
- 消息正文（message body）
- 私有偏好（private preference）
- 记忆内容（memory content）
- `password_hash`
- `access_token` / `refresh_token`
- `api_key` / `api_secret`
- `field_encryption_key`

如果发现敏感数据泄漏，立即：
1. 截取日志片段（去除敏感值后）。
2. 在 `docs/development/P12-RISK-REGISTER.md` 登记。
3. 修补 `apps/api/src/utils/redaction.py` 的 denylist。

## 8. 紧急回滚

### 8.1 代码回滚

```bash
# 查看最近提交
git log --oneline -10

# 回滚到指定提交（不推送，需审批）
git revert <commit-hash>
```

### 8.2 容器回滚

```bash
# 停止所有服务
docker compose down

# 使用上一个镜像版本启动
docker compose up -d --no-build
```

### 8.3 数据库迁移回滚

```bash
cd apps/api
conda run -n CampusAgent alembic downgrade -1
# 验证
conda run -n CampusAgent alembic current
```

- 迁移回滚有数据丢失风险，必须先备份。
- demo 环境可直接 `reset_demo` + `seed_demo` 重建。

## 9. 不可贴到公开 Issue 的数据

以下数据**禁止**贴到 GitHub Issue、PR、聊天群或公开报告：

| 类型 | 示例 | 处理方式 |
| --- | --- | --- |
| 真实用户邮箱 | `zhang.san@university.edu.cn` | 替换为 `user@example.com` |
| 真实学生学号 | `20230101` | 替换为 `<student_no>` |
| 数据库连接串 | `postgresql://user:pass@host` | 替换为 `<DATABASE_URL>` |
| JWT token | `eyJhbGciOi...` | 替换为 `<redacted-jwt>` |
| API key | `sk-xxxx` | 替换为 `<api_key>` |
| 实验室平台地址 | `http://10.x.x.x:port` | 替换为 `<lab-endpoint>` |
| 飞书 disposable token | `t-xxxx` | 替换为 `<feishu-token>` |
| Kuboard 凭据 | `admin / password` | 不得记录 |

如果 Issue 必须包含错误日志，先用 `scripts/security/check_no_secrets.py` 扫描。

## 10. 恢复演练脚本

```bash
# 运行全部演练（不需要 Docker/Redis/PostgreSQL）
python scripts/ops/recovery_drill.py

# 详细输出
python scripts/ops/recovery_drill.py --verbose

# 跳过特定演练
python scripts/ops/recovery_drill.py --skip demo-reset-reseed
```

### 10.1 演练清单

| 演练 | 验证内容 | 期望结果 |
| --- | --- | --- |
| `database-unavailable` | DB 不可用时 `/health/ready` degraded，`/health/live` ok | PASS |
| `redis-unavailable` | Redis 未配置时 `/health/ready` degraded，`/health/live` ok | PASS |
| `model-gateway-unavailable` | 模型网关无 provider 时不 500，metrics 可达 | PASS |
| `demo-reset-reseed` | `seed_demo` → `reset_demo` → `seed_demo` 循环正常 | PASS |
| `cleanup-then-read` | 清理过期数据后主读取路径仍 200 | PASS |

### 10.2 演练频率

- **每次发布前**：运行一次完整演练。
- **演示前**：运行 `demo-reset-reseed` + `cleanup-then-read`。
- **故障后**：运行完整演练确认恢复。

## 11. 联系升级

| 场景 | 升级路径 |
| --- | --- |
| 数据库损坏且无备份 | 停止写入，联系 DBA，登记 blocker |
| 生产环境密钥泄漏 | 轮换 `APP_SECRET` + `FIELD_ENCRYPTION_KEY`，全量 token 失效 |
| 安全漏洞（OWASP 级别） | 创建 private issue，不公开讨论细节 |
| 演示前 30 分钟故障 | 降级到 mock-model 模式，跳过真实模型调用 |

---

**最后更新**：P12-13 恢复演练
**维护者**：CampusAgent 团队
**关联文档**：`docs/development/P12-COMPLETION-REPORT.md`、`docs/development/P12-RISK-REGISTER.md`
