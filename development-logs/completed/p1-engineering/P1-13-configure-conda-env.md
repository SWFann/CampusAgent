---
task_id: P1-13
status: completed
stage: P1
title: 配置Conda虚拟环境作为Python入口
started_at: 2026-07-14T12:10:00+09:00
completed_at: 2026-07-14T12:15:00+09:00
estimated_hours: 0.5
actual_hours: 0.25
---

# P1-13：配置Conda虚拟环境

## 目标

创建并配置 Conda 虚拟环境作为项目 Python 代码的统一入口。

**产物**：
- CampusAgent Conda 环境
- 环境配置文档
- Makefile 更新

## 环境信息

- **环境名称**：CampusAgent
- **Python 版本**：3.11.15
- **环境位置**：`/root/miniconda3/envs/CampusAgent`

## 已安装的核心依赖

- fastapi 0.139.0
- uvicorn 0.51.0
- pydantic 2.13.4
- sqlalchemy 2.0.51
- alembic 1.18.5
- redis 8.0.1

## 使用方式

### 方法 1：直接激活

```bash
conda activate CampusAgent
# 执行后端命令
uvicorn src.main:app --reload
```

### 方法 2：通过 Makefile

```bash
# Makefile 已配置使用 conda run
make dev        # 自动使用 CampusAgent 环境
make test       # 自动使用 CampusAgent 环境
make lint       # 自动使用 CampusAgent 环境
```

## 修改的文件

- `Makefile` - 所有后端命令通过 `conda run -n CampusAgent` 执行
- `README.md` - 添加 Python 虚拟环境章节
- `docs/development/CONDA_ENV.md` - 环境使用说明
- `docs/development/QUICK_START.md` - 更新安装步骤

## 重要说明

⚠️ **所有后端 Python 代码必须在 CampusAgent 虚拟环境中运行**：

- 启动 FastAPI 服务前
- 运行测试前
- 安装 Python 依赖前
- 执行数据库迁移前

## 提交信息

- Commit: `chore(env): configure CampusAgent conda environment`
