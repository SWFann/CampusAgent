# Infrastructure

该目录承载 Docker Compose 编排、本地依赖服务、监控配置和运维脚本。

## 目录结构

```text
infra/
├── docker/           # Docker 相关文档和配置说明
├── mock-model/       # P2 Compose 占位模型服务（非真实模型网关）
│   ├── server.py     # Python 标准库 HTTP 服务
│   ├── Dockerfile    # 容器构建文件
│   └── README.md     # 服务说明
├── prometheus/       # Prometheus 监控配置（后续阶段）
└── scripts/          # 运维脚本（后续阶段）
```

## Docker Compose

根目录的 `compose.yaml` 是 Docker Compose 编排入口，包含以下服务：

| 服务 | 镜像/构建 | 端口 | 健康检查 | 说明 |
|---|---|---|---|---|
| postgres | `postgres:15-alpine` | 5432 | `pg_isready` | 主数据库 |
| redis | `redis:7-alpine` | 6379 | `redis-cli ping` | 缓存和 Pub/Sub |
| mock-model | 构建 `infra/mock-model/` | 8001 | `GET /health/live` | P2 占位模型服务 |
| api | 构建 `apps/api/` | 8000 | `GET /health/live` | FastAPI 后端 |
| web | 构建 `apps/web/` | 3000 | HTTP 200 | Next.js 前端 |

### 快速启动

```bash
# 启动核心依赖（postgres、redis、mock-model）
make docker-up

# 或直接使用 docker compose
docker compose up -d postgres redis mock-model

# 启动全部服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止全部服务
docker compose down
```

### 网络

- 默认网络：`campus_agent_net`（bridge 驱动）
- 所有服务通过服务名互相访问（如 `postgres:5432`、`redis:6379`）

### 数据卷

- `campus_agent_postgres_data`：PostgreSQL 数据持久化
- `campus_agent_redis_data`：Redis 数据持久化

### 安全说明

- 所有密钥均为开发默认值，不得用于生产环境
- Redis 在本地开发中无密码保护，生产环境必须启用认证
- `mock-model` 是 P2 Compose 占位服务，不代表 P7 模型网关已实现
- `.env` 文件不会进入 Docker 构建上下文（见 `.dockerignore`）

详细说明请参阅 [infra/docker/README.md](docker/README.md)。
