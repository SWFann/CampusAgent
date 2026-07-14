---
task_id: P1-10
status: completed
stage: P1
title: 建立CI
started_at: 2026-07-14T11:10:00+09:00
completed_at: 2026-07-14T11:25:00+09:00
estimated_hours: 1.5
actual_hours: 0.75
---

# P1-10：建立CI

## 目标

建立持续集成流水线，自动化代码质量检查。

**来自开发计划**：P1-10 - 建立 CI

**产物**：
- GitHub Actions workflow
- CI 配置文档

**依赖**：P1-08（统一命令 ✅）

## 验收标准

- [x] CI 配置文件
- [x] 安装依赖步骤
- [x] lint 检查
- [x] typecheck 检查
- [x] test 运行
- [x] build 验证
- [x] secret scan（基础）

## CI Pipeline 设计

### 为什么选择 GitHub Actions？

1. **GitHub 原生集成**：无需额外服务
2. **免费额度**：开源项目足够用
3. **生态成熟**：大量 Actions 可用
4. **易于配置**：YAML 配置

### 触发条件

- Push 到 `main` 或 `develop` 分支
- Pull Request 到 `main` 分支

### Pipeline 步骤

#### Job 1: lint-and-test

| 步骤 | 描述 | 失败阻断 |
|------|------|---------|
| Checkout code | 检出代码 | 是 |
| Setup pnpm | 安装 pnpm 8.x | 是 |
| Setup Node.js | 安装 Node.js 18 | 是 |
| Setup Python | 安装 Python 3.11 | 是 |
| Install dependencies | pnpm install | 是 |
| Lint frontend | ESLint | 是 |
| Lint backend | Ruff | 是 |
| Typecheck frontend | tsc --noEmit | 是 |
| Typecheck backend | mypy . | 是 |
| Test frontend | Jest | 是 |
| Test backend | pytest | 是 |
| Build frontend | Next.js build | 是 |
| Secret scan | gitleaks | 否（警告） |

#### Job 2: e2e (Playwright)

- 需要 Job 1 通过
- 安装 Playwright 浏览器
- 运行 E2E 测试

### 服务容器

- **PostgreSQL 15**：测试数据库
- **Redis 7**：测试缓存

### 环境变量

```yaml
env:
  DATABASE_URL: postgresql://postgres:postgres@localhost:5432/campus_agent_test
  REDIS_URL: redis://localhost:6379/1
  SECRET_KEY: test-secret-key-for-ci
```

## 关键特性

### 1. 缓存依赖

```yaml
- uses: actions/setup-node@v4
  with:
    cache: "pnpm"

- uses: actions/setup-python@v5
  with:
    cache: "pip"
```

### 2. Secret Scan

使用 `gitleaks` 扫描敏感信息泄露：
- 不阻断构建（continue-on-error）
- 只产生警告

### 3. 测试数据库

CI 自动启动 PostgreSQL + Redis 容器

## 修改的文件

### 新增文件
- `.github/workflows/ci.yml` ✅ - GitHub Actions workflow

### 修改文件
- （暂无）

### 删除文件
- （无）

## 注意事项

### 本地无法测试

GitHub Actions 需要在 GitHub 仓库中运行。当前环境下无法验证 workflow 的有效性。

### 后续改进

- [ ] 添加代码覆盖率报告（Codecov）
- [ ] 添加性能测试
- [ ] 添加 Docker 构建和推送到 registry
- [ ] 添加自动部署到 staging 环境

## 下一步

- **后续任务**：P1-11 配置依赖更新策略
- **注意事项**：需要在 GitHub 仓库验证 CI 配置

## 提交信息

- Commit: `ci: add GitHub Actions workflow`
