# 快速开始指南

> 从空机器到运行 CampusAgent 的完整步骤。

**版本**：v1.0  
**最后更新**：2026-07-14

---

## 前提条件

### 必需工具

| 工具 | 最低版本 | 推荐版本 | 检查命令 |
|------|---------|---------|---------|
| Node.js | 18.x LTS | 20.x LTS | `node --version` |
| Python | 3.11 | 3.11 或 3.12 | `python3 --version` |
| Git | 2.40 | 最新稳定版 | `git --version` |
| pnpm | 8.x | 8.x | `pnpm --version` |

### 推荐工具

| 工具 | 用途 | 最低版本 |
|------|------|---------|
| Docker | PostgreSQL, Redis | 24.x |
| Docker Compose | 服务编排 | 2.20.x |

### 运行版本检查

```bash
./scripts/check-versions.sh
```

如果显示错误，请先安装缺失工具。

---

## 第一步：克隆仓库

```bash
git clone https://github.com/your-org/campus-agent.git
cd campus-agent
```

---

## 第二步：配置 Conda 虚拟环境

### 激活虚拟环境

```bash
conda activate CampusAgent
```

### 验证环境

```bash
python --version
# 应显示 Python 3.11.15
```

**重要**：所有后端 Python 代码必须在 `CampusAgent` 虚拟环境中运行。

详见：[Python 虚拟环境说明](../README.md#python-虚拟环境)

---

## 第三步：安装依赖

### 安装前端依赖

```bash
pnpm install
```

这会安装所有前端依赖（Next.js, React 等）。

### 安装后端依赖

**前提**：已激活 `CampusAgent` 虚拟环境

```bash
cd apps/api
pip install -r requirements.txt
```

或手动安装：

```bash
conda activate CampusAgent
cd apps/api
pip install fastapi uvicorn pydantic sqlalchemy alembic redis python-dotenv
```

这会安装所有后端依赖（FastAPI, SQLAlchemy 等）。

---

## 第三步：配置环境变量

### 1. 复制模板

```bash
cp .env.example .env
```

### 2. 编辑 .env

至少需要配置：

```bash
# 开发环境（通常不需要修改）
APP_ENV=development

# 数据库（Docker 启动后会自动配置）
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/campus_agent

# Redis（Docker 启动后会自动配置）
REDIS_URL=redis://localhost:6379/0

# 安全密钥（测试用，生产环境必须更改）
APP_SECRET=dev-secret-key-change-in-production
FIELD_ENCRYPTION_KEY=dev-encryption-key-change-in-production
```

### 可选配置

- `DEBUG=false` - 关闭调试模式
- `LOG_LEVEL=INFO` - 日志级别
- `ENABLE_EXTERNAL_MODEL=false` - 禁用外部模型

---

## 第四步：启动开发服务

### 选项 A：使用 Docker（推荐）

```bash
# 启动 PostgreSQL 和 Redis
make docker-up

# 启动开发服务
make dev
```

### 选项 B：本地安装服务

如果不想使用 Docker，可以本地安装 PostgreSQL 和 Redis。

```bash
# 启动开发服务
make dev
```

这会启动：
- **Next.js**：http://localhost:3000
- **FastAPI**：http://localhost:8000
- **API Docs**：http://localhost:8000/docs

---

## 第五步：验证安装

### 检查 Web

访问 http://localhost:3000 ，应该看到 "CampusAgent" 标题。

### 检查 API

访问 http://localhost:8000/health/live ，应该看到：

```json
{
  "status": "ok",
  "service": "CampusAgent API"
}
```

访问 http://localhost:8000/health/ready ，应该看到：

```json
{
  "status": "ready",
  "service": "CampusAgent API"
}
```

---

## 运行测试

### 所有测试

```bash
make test
```

### 仅前端测试

```bash
pnpm --filter @campus-agent/web test
```

### 仅后端测试

```bash
cd apps/api && pytest
```

---

## 代码质量

### Lint

```bash
make lint
```

### Typecheck

```bash
make typecheck
```

### 格式化

```bash
make format
```

---

## 常见问题

### 1. Docker 未安装

**问题**：`docker: command not found`

**解决**：参见 [工具版本规范](../TOOLING.md) 安装 Docker。

**临时方案**：本地安装 PostgreSQL 和 Redis。

### 2. 端口被占用

**问题**：`Error: listen EADDRINUSE: address already in use :::3000`

**解决**：
```bash
# 查找占用端口的进程
lsof -i :3000
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### 3. 数据库连接失败

**问题**：`could not connect to server: Connection refused`

**解决**：
- 确保 Docker 服务已启动：`make docker-up`
- 检查 `.env` 中的 `DATABASE_URL`

### 4. 依赖安装失败

**问题**：`pnpm install` 失败

**解决**：
```bash
# 清理缓存
pnpm store prune

# 重新安装
rm -rf node_modules
pnpm install
```

### 5. 环境变量未生效

**问题**：配置不生效

**解决**：
```bash
# 确认 .env 文件存在
ls -la .env

# 重启开发服务
make dev
```

---

## 目录结构

```
campus-agent/
├── apps/
│   ├── web/              # Next.js Web 应用
│   └── api/              # FastAPI 后端
├── docs/                 # 项目文档
├── scripts/              # 工具脚本
├── development-logs/     # 开发日志
├── Makefile              # 统一命令
├── package.json          # 根配置
├── pnpm-workspace.yaml   # Workspace 配置
├── .env.example          # 环境变量模板
└── README.md
```

---

## 下一步

- 阅读 [项目 README](README.md) 了解项目背景
- 阅读 [架构与模块边界](../architecture/MODULE_BOUNDARIES.md)
- 查看 [开发计划表](../development/DEVELOPMENT_PLAN.md)
- 开始第一个开发任务

---

## 获取帮助

- **Issues**：https://github.com/your-org/campus-agent/issues
- **文档**：`/docs` 目录
- **开发计划**：`docs/development/DEVELOPMENT_PLAN.md`

---

**祝开发愉快！** 🚀
