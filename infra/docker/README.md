# Docker 基础设施

存放 Docker Compose 编排和应用镜像构建相关说明。

## Compose 文件

根目录的 `compose.yaml` 是 Docker Compose 编排入口文件。

## 服务清单

### postgres

| 属性 | 值 |
|---|---|
| 镜像 | `postgres:15-alpine` |
| 端口 | `5432:5432` |
| 环境变量 | `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=campus_agent` |
| 健康检查 | `pg_isready -U postgres -d campus_agent` |
| 数据卷 | `campus_agent_postgres_data:/var/lib/postgresql/data` |

### redis

| 属性 | 值 |
|---|---|
| 镜像 | `redis:7-alpine` |
| 端口 | `6379:6379` |
| 健康检查 | `redis-cli ping` |
| 数据卷 | `campus_agent_redis_data:/data` |
| 说明 | 本地开发无密码保护，生产环境必须启用认证 |

### mock-model

| 属性 | 值 |
|---|---|
| 构建 | `./infra/mock-model` |
| 端口 | `8001:8001` |
| 健康检查 | `GET /health/live` |
| 说明 | P2 Compose 占位服务，非真实模型网关，将在 P7 替换 |

### api

| 属性 | 值 |
|---|---|
| 构建 | `./apps/api` |
| 端口 | `8000:8000` |
| 健康检查 | `GET /health/live` |
| 依赖 | postgres (healthy), redis (healthy), mock-model (healthy) |
| 说明 | FastAPI 后端，数据库/Redis readiness 未接入（P2-03/P2-05 之后） |

### web

| 属性 | 值 |
|---|---|
| 构建 | `./` (context), `apps/web/Dockerfile` |
| 端口 | `3000:3000` |
| 健康检查 | HTTP 200 |
| 依赖 | api (healthy) |
| 说明 | Next.js 前端生产模式 |

## 网络

- 网络名：`campus_agent_net`
- 驱动：`bridge`
- 所有服务通过服务名互相访问

## 数据卷

| 卷名 | 用途 |
|---|---|
| `campus_agent_postgres_data` | PostgreSQL 数据持久化 |
| `campus_agent_redis_data` | Redis 数据持久化 |

## 启动/停止命令

```bash
# 静态检查（不需要 Docker 运行）
docker compose config

# 启动核心依赖
docker compose up -d postgres redis mock-model

# 启动全部服务
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止并删除容器（保留卷）
docker compose down

# 停止并删除容器和卷（慎用）
docker compose down -v
```

## 环境变量

API 服务的环境变量在 `compose.yaml` 中直接定义，均为开发默认值：

| 变量 | 值 |
|---|---|
| `APP_ENV` | `development` |
| `DEBUG` | `false` |
| `APP_SECRET` | `dev-secret-key-change-in-production` |
| `FIELD_ENCRYPTION_KEY` | `dev-encryption-key-change-in-production` |
| `DATABASE_URL` | `postgresql://postgres:postgres@postgres:5432/campus_agent` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `MODEL_GATEWAY_BASE_URL` | `http://mock-model:8001` |

Web 服务的环境变量：

| 变量 | 值 |
|---|---|
| `NODE_ENV` | `production` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |

## 安全说明

- ⚠️ 所有密码和密钥均为开发默认值，**不得用于生产环境**
- ⚠️ Redis 在本地开发中无密码保护，生产环境必须启用认证
- ⚠️ `mock-model` 是 P2 Compose 占位服务，不代表 P7 模型网关已实现
- `.env` 文件被 `.dockerignore` 排除，不会进入 Docker 构建上下文
