---
task_id: P1-11
status: completed
stage: P1
title: 配置依赖更新策略
started_at: 2026-07-14T11:30:00+09:00
completed_at: 2026-07-14T11:40:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# P1-11：配置依赖更新策略

## 目标

配置自动化依赖更新，确保依赖安全和最新。

**来自开发计划**：P1-11 - 配置依赖更新策略

**产物**：
- Dependabot 配置
- 锁文件评审规则

**依赖**：P1-10（CI ✅）

## 验收标准

- [x] Dependabot 配置文件
- [x] 锁文件评审规则文档
- [x] 依赖更新策略文档

## Dependabot 配置

### 更新包类型

| 包类型 | 生态 | 目录 | 频率 |
|--------|------|------|------|
| npm | 前端 | `apps/web` | 每周一 9:00 |
| npm | Root | `/` | 每周一 9:00 |
| pip | 后端 | `apps/api` | 每周一 9:00 |
| Docker | Dockerfile | `/` | 每周 |

### 分组策略

**前端**：
- `dev-dependencies`：开发依赖（ESLint, Testing 等）
- `production-dependencies`：生产依赖（React, Next.js 等）

**后端**：
- `all-dependencies`：所有 pip 包

### PR 限制

- 最多 10 个开放 PR（防止 PR 轰炸）
- 自动创建 PR
- CI 验证后自动可合并

## 锁文件策略

### pnpm-lock.yaml

- **提交到 Git**：是
- **评审规则**：PR 中必须审查锁文件变更

### requirements.txt

- **提交到 Git**：是
- **评审规则**：PR 中必须审查锁文件变更

## 版本升级政策

### 主版本（Major）

- 仔细阅读 Breaking Changes
- 在独立分支测试
- 团队评审

### 次版本（Minor）

- 阅读 Release Notes
- 本地测试

### 补丁版本（Patch）

- 可以安全快速更新

## 安全更新

### 优先级

1. **Critical**：24 小时内
2. **High**：1 周内
3. **Medium**：1 个月内
4. **Low**：常规更新

## 修改的文件

### 新增文件
- `.github/dependabot.yml` ✅ - Dependabot 配置
- `docs/development/DEPENDENCY_UPDATE_POLICY.md` ✅ - 更新策略文档

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **后续任务**：P1-12 更新启动文档
- **注意事项**：Dependabot 需要在 GitHub 仓库中生效

## 提交信息

- Commit: `chore(deps): configure Dependabot for automated updates`
