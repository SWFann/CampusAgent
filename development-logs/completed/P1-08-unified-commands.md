---
task_id: P1-08
status: completed
stage: P1
title: 建立统一命令
started_at: 2026-07-14T10:30:00+09:00
completed_at: 2026-07-14T10:45:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# P1-08：建立统一命令

## 目标

建立统一的开发命令，确保所有开发者使用相同的命令执行常见操作。

**来自开发计划**：P1-08 - 建立统一命令

**产物**：
- 统一命令脚本（Makefile）
- 命令文档

**依赖**：P1-06（质量工具 ✅）、P1-07（测试框架 ✅）

## 验收标准

- [x] `make dev` - 启动开发环境
- [x] `make test` - 运行所有测试
- [x] `make lint` - 代码检查
- [x] `make typecheck` - 类型检查
- [x] `make build` - 构建项目
- [x] `make clean` - 清理
- [x] 命令文档

## 可用命令

### 开发命令

| 命令 | 描述 |
|------|------|
| `make help` | 显示帮助信息 |
| `make dev` | 启动所有开发服务（Web + API） |
| `make test` | 运行所有测试 |
| `make test-watch` | 测试监视模式 |

### 代码质量

| 命令 | 描述 |
|------|------|
| `make lint` | 运行所有 lint 检查（ESLint + Ruff） |
| `make typecheck` | 运行所有类型检查（tsc + mypy） |
| `make format` | 格式化所有代码（Prettier + Ruff） |

### 构建

| 命令 | 描述 |
|------|------|
| `make build` | 构建所有应用 |
| `make clean` | 清理构建产物 |

### 安装

| 命令 | 描述 |
|------|------|
| `make install` | 安装所有依赖 |
| `make setup` | 初始项目设置 |

### Docker（待 Docker 安装后可用）

| 命令 | 描述 |
|------|------|
| `make docker-up` | 启动 Docker 服务（PostgreSQL + Redis） |
| `make docker-down` | 停止 Docker 服务 |
| `make docker-logs` | 查看 Docker 日志 |

### 数据库（待实现后可用）

| 命令 | 描述 |
|------|------|
| `make db-migrate` | 运行数据库迁移 |

## 设计决策

### 为什么选择 Makefile？

1. **跨平台**：支持 Windows/macOS/Linux
2. **易读性**：命令一目了然
3. **依赖管理**：Makefile 原生支持
4. **标准工具**：开发者普遍熟悉

### 命令设计原则

1. **简单明了**：`make dev` 而非复杂的 npm scripts
2. **一致性**：前后端命令统一
3. **文档化**：`make help` 自动生成文档
4. **渐进增强**：Docker 未安装时不影响基本命令

## 使用示例

```bash
# 首次设置
make setup

# 启动开发
make dev

# 运行测试
make test

# 代码检查
make lint

# 格式化代码
make format

# 构建项目
make build

# 查看帮助
make help
```

## 修改的文件

### 新增文件
- `Makefile` - 统一命令文件

### 修改文件
- （暂无）

### 删除文件
- （无）

## 注意事项

### Docker 未安装

当前环境 Docker 未安装，以下命令暂时无法使用：
- `make docker-up`
- `make docker-down`
- `make docker-logs`

### 后续增强

- P2 阶段：完善 Docker 相关命令
- P8 阶段：添加场景管理命令
- P11 阶段：添加演示数据命令

## 下一步

- **后续任务**：P1-09 建立环境变量校验
- **注意事项**：Makefile 中的 Docker 命令需要 Docker 安装后才能使用

## 提交信息

- Commit: `chore(makefile): add unified development commands`
