---
task_id: P1-05
status: completed
stage: P1
title: 建立后端模块目录
started_at: 2026-07-14T09:30:00+09:00
completed_at: 2026-07-14T09:40:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# P1-05：建立后端模块目录

## 目标

建立后端模块化单体架构的目录骨架，明确模块边界约束。

**来自开发计划**：P1-05 - 建立后端模块目录

**产物**：
- core 模块骨架
- 13 个业务模块空骨架
- 模块约束说明文档

**依赖**：P1-04（API工程 ✅）

## 验收标准

- [x] core 模块（基础设施）
- [x] 13 个业务模块骨架（auth, users, organizations, directory, conversations, agents, memories, scenes, model_gateway, nodes, notifications, audit, admin）
- [x] 每个模块包含标准文件（api.py, schemas.py, models.py, repository.py, service.py）
- [x] 模块约束说明（禁止跨ORM访问）
- [x] __init__.py 文件

## 模块列表

### Core 模块

- ✅ core - 基础设施（config, events, logging, database）

### 业务模块（13个）

- ✅ auth - 认证模块
- ✅ users - 用户模块
- ✅ organizations - 组织模块
- ✅ directory - 校园目录模块
- ✅ conversations - 会话模块
- ✅ agents - 智能体模块
- ✅ memories - 记忆模块
- ✅ scenes - 场景模块
- ✅ model_gateway - 模型网关模块
- ✅ nodes - 节点管理模块
- ✅ notifications - 通知模块
- ✅ audit - 审计模块
- ✅ admin - 管理后台模块

## 标准模块结构

每个模块包含以下文件（占位）：

```
{module_name}/
├── __init__.py
├── api.py          # FastAPI 路由
├── schemas.py      # Pydantic 模型
├── models.py       # SQLAlchemy ORM
├── repository.py   # 数据访问层
└── service.py      # 业务逻辑层
```

### Core 模块额外文件

```
core/
├── __init__.py
├── config.py       # 配置对象（pydantic-settings）
├── events.py       # 领域事件总线
├── logging.py      # 日志配置
└── database.py     # 数据库连接
```

## 模块约束

### ✅ 允许的依赖

```
任何模块 → core
模块内部 → 自身的 schemas/models
```

### ❌ 禁止的依赖

```
模块A → 模块B 的 models.py（直接访问ORM）
模块A → 模块B 的 repository.py（绕过Service）
跨模块的业务逻辑调用
```

### ✅ 正确的跨模块调用

```python
# 通过 Service Interface
from modules.agents.service import AgentService

# ❌ 错误：直接导入 ORM
# from modules.agents.models import Agent  # 禁止！
```

## 通信方式

1. **同步调用**：通过 Service Interface（依赖注入）
2. **异步事件**：通过 Event Bus（Domain Events）

## 相关文档

- [MODULE_BOUNDARIES.md](../../../docs/architecture/MODULE_BOUNDARIES.md) - 详细的模块边界约束

## 修改的文件

### 新增文件

所有模块的占位文件：
- `apps/api/src/modules/core/{__init__,config,events,logging,database}.py`
- `apps/api/src/modules/{auth,users,organizations,...}/__init__.py` (13个)
- `apps/api/src/modules/{auth,users,organizations,...}/{api,schemas,models,repository,service}.py` (13x5=65个)

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **后续任务**：P1-06 配置格式化与静态检查
- **注意事项**：后续实现业务逻辑时，严格遵守模块边界

## 提交信息

- Commit: `feat(api): establish modular monolith directory structure`
