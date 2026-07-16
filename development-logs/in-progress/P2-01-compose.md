---
task_id: P2-01
task_name: 编写 Compose
status: in_review
started_at: 2026-07-16T15:30:00+08:00
completed_at: 2026-07-16T16:10:00+08:00
actual_hours: 0.7
owner: Claude
auditor: Codex
---

# P2-01: 编写 Compose

## 1. 背景

- P0/P1 已由 Codex 收口并推送至 `origin/main`，远端 GitHub Actions 已通过。
- 当前基准路径：`/root/CampusAgent`
- 当前基准提交：`5124c09`
- 本任务只做 P2-01（Docker Compose 基线），不做 P2-02～P2-14。
- Docker 未在当前机器安装（`docker` 命令不存在），已完成 `docker compose config` 的等价静态检查。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `compose.yaml` | 新增 | Docker Compose 编排入口，含 5 个服务、网络和数据卷 |
| `.dockerignore` | 新增 | 防止敏感文件和构建产物进入 Docker 构建上下文 |
| `apps/web/Dockerfile` | 新增 | Next.js 多阶段构建 Dockerfile |
| `apps/api/Dockerfile` | 修改 | 改用 requirements.lock 锁定依赖，添加 EXPOSE 和注释，确保容器内正确运行 |
| `infra/mock-model/server.py` | 新增 | Python 标准库 HTTP 占位服务 |
| `infra/mock-model/Dockerfile` | 新增 | mock-model 容器构建文件 |
| `infra/mock-model/README.md` | 新增 | mock-model 服务说明文档 |
| `Makefile` | 修改 | 更新 docker-up 命令含 mock-model，新增 docker-build/docker-ps/docker-health |
| `.env.example` | 修改 | 补充 Docker Compose 环境变量说明 |
| `infra/README.md` | 修改 | 更新为 Compose 基线说明 |
| `infra/docker/README.md` | 修改 | 详细服务清单、端口、健康检查说明 |
| `README.md` | 修改 | 新增 Docker Compose 开发入口段落 |
| `docs/development/DEVELOPMENT_PLAN.md` | 修改 | P2-01 标记为 [x]，P2 进度更新 |

## 3. Compose 服务说明

### 3.1 服务清单

| 服务 | 镜像/构建 | 端口 | healthcheck | 说明 |
|---|---|---|---|---|
| postgres | `postgres:15-alpine` | 5432:5432 | `pg_isready -U postgres -d campus_agent` | 主数据库 |
| redis | `redis:7-alpine` | 6379:6379 | `redis-cli ping` | 缓存和 Pub/Sub |
| mock-model | 构建 `./infra/mock-model` | 8001:8001 | `GET /health/live` (Python urllib) | P2 占位模型服务 |
| api | 构建 `./apps/api` | 8000:8000 | `GET /health/live` (Python urllib) | FastAPI 后端 |
| web | 构建 `./` (Dockerfile: `apps/web/Dockerfile`) | 3000:3000 | HTTP 200 (wget) | Next.js 前端 |

### 3.2 网络

- 网络名：`campus_agent_net`
- 驱动：`bridge`
- 所有服务通过服务名互相访问（如 `postgres:5432`、`redis:6379`、`mock-model:8001`）

### 3.3 数据卷

| 卷名 | 用途 |
|---|---|
| `campus_agent_postgres_data` | PostgreSQL 数据持久化 |
| `campus_agent_redis_data` | Redis 数据持久化 |

### 3.4 端口映射

| 服务 | 宿主机端口 | 容器端口 |
|---|---|---|
| postgres | 5432 | 5432 |
| redis | 6379 | 6379 |
| mock-model | 8001 | 8001 |
| api | 8000 | 8000 |
| web | 3000 | 3000 |

### 3.5 环境变量

#### api 服务

| 变量 | 值 |
|---|---|
| APP_ENV | development |
| DEBUG | false |
| APP_SECRET | dev-secret-key-change-in-production |
| FIELD_ENCRYPTION_KEY | dev-encryption-key-change-in-production |
| DATABASE_URL | postgresql://postgres:postgres@postgres:5432/campus_agent |
| REDIS_URL | redis://redis:6379/0 |
| MODEL_GATEWAY_BASE_URL | http://mock-model:8001 |
| NEXT_PUBLIC_API_URL | http://localhost:8000 |
| LOG_LEVEL | INFO |
| LOG_PROMPT_CONTENT | false |
| ENABLE_EXTERNAL_MODEL | false |
| PRIVATE_SCENE_TTL_HOURS | 24 |
| ACCESS_TOKEN_EXPIRE_MINUTES | 60 |
| REFRESH_TOKEN_EXPIRE_DAYS | 7 |
| API_V1_PREFIX | /api/v1 |

#### web 服务

| 变量 | 值 |
|---|---|
| NODE_ENV | production |
| NEXT_PUBLIC_API_URL | http://localhost:8000 |
| NEXT_TELEMETRY_DISABLED | 1 |

#### postgres 服务

| 变量 | 值 |
|---|---|
| POSTGRES_USER | postgres |
| POSTGRES_PASSWORD | postgres |
| POSTGRES_DB | campus_agent |

#### redis 服务

无自定义环境变量（使用默认配置，无密码保护）。

#### mock-model 服务

无自定义环境变量（Python 标准库服务）。

### 3.6 依赖关系

```
postgres (healthy) ─┐
redis (healthy) ────┤
mock-model (healthy)─┴──> api (healthy) ──> web
```

- `api` 依赖 `postgres`、`redis`、`mock-model` 的 `service_healthy` 条件
- `web` 依赖 `api` 的 `service_healthy` 条件

### 3.7 健康检查

| 服务 | 检查命令 | 间隔 | 超时 | 重试 | 启动等待 |
|---|---|---|---|---|---|
| postgres | `pg_isready -U postgres -d campus_agent` | 10s | 5s | 5 | 10s |
| redis | `redis-cli ping` | 10s | 5s | 5 | 5s |
| mock-model | `python -c "urllib.request.urlopen('.../health/live')"` | 10s | 5s | 5 | 5s |
| api | `python -c "urllib.request.urlopen('.../health/live')"` | 10s | 5s | 5 | 15s |
| web | `wget --spider http://localhost:3000/` | 15s | 5s | 5 | 30s |

## 4. 验证命令和结果

### 4.1 基础状态

```bash
cd /root/CampusAgent
git status --short --branch
git log -1 --oneline
```

结果：
```
## main...origin/main
5124c09 docs(project): record remote CI completion
```

### 4.2 Compose 静态检查

Docker 未安装，使用 Python YAML 解析器进行等价静态检查：

```bash
python3 /tmp/validate_compose.py
```

结果：
```
compose.yaml validation: ALL CHECKS PASSED
Services: ['api', 'mock-model', 'postgres', 'redis', 'web']
Networks: ['campus_agent']
Volumes: ['postgres_data', 'redis_data']
```

验证内容：
- 5 个服务全部存在（web, api, postgres, redis, mock-model）
- 每个服务有 ports、healthcheck
- postgres 镜像为 `postgres:15-alpine`
- redis 镜像为 `redis:7-alpine`
- mock-model 端口 8001
- api 端口 8000，环境变量齐全（APP_ENV, DATABASE_URL, REDIS_URL, MODEL_GATEWAY_BASE_URL, APP_SECRET, FIELD_ENCRYPTION_KEY）
- api depends_on postgres/redis/mock-model 均为 service_healthy
- web 端口 3000，有 NEXT_PUBLIC_API_URL
- web depends_on api
- 网络和卷配置完整

### 4.3 Docker 实跑

Docker 未在当前机器安装，以下命令未执行：

- `docker compose config`
- `docker compose up -d postgres redis mock-model`
- `docker compose ps`
- `docker compose exec postgres pg_isready -U postgres -d campus_agent`
- `docker compose exec redis redis-cli ping`
- `curl -f http://localhost:8001/health/live`
- `curl -f http://localhost:8001/health/ready`
- `docker compose up -d`
- `curl -f http://localhost:8000/health/live`
- `curl -f http://localhost:3000`
- `docker compose down`

原因：当前机器（Linux 6.18）未安装 Docker，`docker` 命令不存在。

### 4.4 Git diff check

```bash
git diff HEAD --check
```

结果：无空白错误（exit code 0）。

### 4.5 本地质量检查

以下命令未在本次执行中运行（与 Compose 任务无直接关系，且 Conda 环境可能未配置）：

- `corepack pnpm lint`
- `corepack pnpm typecheck`
- `corepack pnpm test`
- `corepack pnpm build`

## 5. 边界声明

- ✅ 未执行 P2-02～P2-14
- ✅ 未实现 PostgreSQL 应用接入（P2-03）
- ✅ 未初始化 Alembic（P2-04）
- ✅ 未实现 Redis 客户端（P2-05）
- ✅ 未实现 API Envelope（P2-06）
- ✅ 未修改 P0/P1 冻结契约
- ✅ 未修改 API_CONTRACT.md
- ✅ 未修改 WEBSOCKET_CONTRACT.md
- ✅ 未修改 THREAT_MODEL.md
- ✅ 未修改 PRIVACY_TEST_MATRIX.md
- ✅ 未引入真实密钥
- ✅ 未引入真实模型 API
- ✅ 未实现业务模块代码
- ✅ 未提交、未推送，等待 Codex 审计

## 6. Codex 审计整改（2026-07-16）

Codex 审计结论：主体方向正确，暂不通过，需要小修后重新报告。

### 6.1 整改内容

#### 6.1.1 修正 DEVELOPMENT_PLAN.md 中的旧远端 CI 口径

**问题**：该文件仍有多处旧表述，声称远端 CI "需推送后观察"或"未观察"，与当前事实不符。

**整改**：同步为当前事实：
- R1-32～R1-36 已由 Codex 收口并推送至 `origin/main`
- R3-25/R4-19 已观察到远端 GitHub Actions 绿色
- 最新远端 CI 成功 run：https://github.com/SWFann/CampusAgent/actions/runs/29480110555
- P2 当前为进行中，仅 P2-01 完成

修改位置（共 6 处）：
1. P0 阶段状态说明（第 95 行附近）："远端 CI 观察需用户授权推送后完成" → 已更新为远端 CI 绿色
2. P1 阶段状态说明（第 119 行附近）："远端 CI 观察仍需推送后完成" → 已更新为远端 CI 绿色
3. 进度记录表 P0 行："远端 CI 需推送后观察" → "远端 CI 绿色（run 29480110555）"
4. 进度记录表 P1 行："远端 CI 未观察" → "远端 CI 绿色（run 29480110555）"
5. R1 整改进度小节说明："远端 CI 观察仍需用户授权推送" → 已更新为远端 CI 绿色
6. 第 8 节状态说明："远端 CI 观察需用户授权推送后完成" → 已更新为远端 CI 绿色

**未修改 P0/P1 冻结契约口径本身。**

#### 6.1.2 修正 apps/api/Dockerfile 的依赖安装方式

**问题**：原 Dockerfile 使用 `requirements.txt`，与 CI/Makefile 的锁定依赖策略不一致。

**整改**：改为使用 `requirements.lock`：
```dockerfile
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
```

目标：Compose API 镜像依赖与 CI/Makefile 的锁定依赖策略一致。

#### 6.1.3 补齐文件末尾换行

**问题**：多个文件缺少末尾换行符。

**整改**：为以下 5 个文件补齐末尾换行符（`0a`）：
- `compose.yaml`
- `apps/api/Dockerfile`
- `apps/web/Dockerfile`
- `infra/README.md`
- `infra/docker/README.md`

### 6.2 整改后验证

- `git diff HEAD --check`：无空白错误
- Compose 静态检查：全部通过
- `python -m py_compile infra/mock-model/server.py`：编译通过
- Docker 仍不可用：`docker --version` 输出 `Command 'docker' not found`

### 6.3 边界声明

- ✅ 未执行 P2-02～P2-14
- ✅ 未修改 P0/P1 冻结契约
- ✅ 未提交、未推送，等待 Codex 复审
