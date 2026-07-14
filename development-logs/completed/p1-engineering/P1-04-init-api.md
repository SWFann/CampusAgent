---
task_id: P1-04
status: completed
stage: P1
title: 初始化API工程
started_at: 2026-07-14T09:10:00+09:00
completed_at: 2026-07-14T09:25:00+09:00
estimated_hours: 1.5
actual_hours: 0.75
---

# P1-04：初始化API工程

## 目标

初始化 FastAPI 后端应用项目结构，建立应用工厂模式。

**来自开发计划**：P1-04 - 初始化 API 工程

**产物**：
- FastAPI 应用工厂
- `/health/live` 和 `/health/ready` 端点
- 基础项目结构

**依赖**：P1-01（工具版本确认 ✅）

## 验收标准

- [x] FastAPI 应用工厂模式
- [x] `/health/live` 端点（存活检查）
- [x] `/health/ready` 端点（就绪检查）
- [x] Pydantic 配置
- [x] 基础中间件设置
- [x] 项目可以在 `apps/api` 目录独立运行

## 项目结构

```
apps/api/
├── src/
│   ├── main.py              # 应用入口 + 工厂函数
│   ├── config.py            # 配置对象（pydantic-settings）
│   ├── dependencies.py      # 依赖注入
│   ├── middleware/          # 中间件
│   │   ├── __init__.py
│   │   └── correlation_id.py
│   ├── routers/             # 路由（占位）
│   │   └── __init__.py
│   ├── schemas/             # Pydantic 模型（占位）
│   │   └── __init__.py
│   └── utils/               # 工具函数
│       ├── __init__.py
│       └── errors.py        # 自定义错误类型
├── tests/                   # 测试目录
│   └── __init__.py
├── pyproject.toml           # Python 项目配置
├── requirements.txt         # 依赖（开发阶段）
├── .python-version          # Python 3.11
├── Dockerfile               # 容器镜像
└── README.md
```

## 设计决策

### 应用工厂模式

```python
def create_app() -> FastAPI:
    app = FastAPI(...)
    # 注册中间件
    # 注册路由
    return app

app = create_app()
```

**优点**：
- 支持多实例（测试、开发、生产）
- 配置隔离
- 便于测试

### 健康检查端点

- **`/health/live`**：K8s liveness probe，检查进程是否存活
- **`/health/ready`**：K8s readiness probe，检查依赖是否就绪（预留扩展）

### 配置管理

使用 `pydantic-settings`：
- 支持 `.env` 文件
- 类型安全
- 环境变量覆盖

### 错误处理

自定义错误类型：
- `AppError` - 基础错误
- `AuthenticationError` - 认证失败（401）
- `AuthorizationError` - 权限不足（403）
- `NotFoundError` - 资源不存在（404）

## 修改的文件

### 新增文件
- `apps/api/pyproject.toml` - Python 项目配置
- `apps/api/requirements.txt` - 依赖列表
- `apps/api/.python-version` - Python 3.11
- `apps/api/Dockerfile` - 容器镜像
- `apps/api/src/main.py` - 应用工厂 + 健康检查
- `apps/api/src/config.py` - 配置对象
- `apps/api/src/dependencies.py` - 依赖注入
- `apps/api/src/middleware/__init__.py`
- `apps/api/src/middleware/correlation_id.py` - 请求追踪
- `apps/api/src/routers/__init__.py`
- `apps/api/src/schemas/__init__.py`
- `apps/api/src/utils/__init__.py`
- `apps/api/src/utils/errors.py` - 自定义错误
- `apps/api/tests/__init__.py`

### 已存在文件
- `apps/api/README.md` ✅

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **后续任务**：P1-05 建立后端模块目录
- **注意事项**：不实现具体业务逻辑，只创建项目骨架

## 提交信息

- Commit: `feat(api): initialize FastAPI app with factory pattern`
