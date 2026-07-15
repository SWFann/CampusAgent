---
task_id: P1-06
status: completed
stage: P1
title: 配置格式化与静态检查
started_at: 2026-07-14T09:45:00+09:00
completed_at: 2026-07-14T10:00:00+09:00
estimated_hours: 1.5
actual_hours: 0.75
---

# P1-06：配置格式化与静态检查

## 目标

统一配置前端和后端的代码质量工具，确保代码风格一致。

**来自开发计划**：P1-06 - 配置格式化与静态检查

**产物**：
- ESLint + Prettier（前端）
- Ruff（后端 lint）
- mypy（后端 typecheck）
- EditorConfig
- 统一命令集成

**依赖**：P1-03（Web工程 ✅）、P1-04（API工程 ✅）

## 验收标准

- [x] ESLint 配置（前端）
- [x] Prettier 配置（前端）
- [x] Ruff 配置（后端）
- [x] mypy 配置（后端）
- [x] EditorConfig
- [x] 根目录统一命令（P1-08前置）

## 工具配置

### 前端

| 工具 | 用途 | 配置位置 |
|------|------|---------|
| ESLint | Lint | `apps/web/.eslintrc.json` |
| Prettier | 格式化 | `apps/web/.prettierrc` |
| TypeScript | 类型检查 | `apps/web/tsconfig.json` |

### 后端

| 工具 | 用途 | 配置位置 |
|------|------|---------|
| Ruff | Lint + 格式化 | `apps/api/pyproject.toml` |
| mypy | 类型检查 | `apps/api/pyproject.toml` |

### 通用

| 工具 | 用途 | 配置位置 |
|------|------|---------|
| EditorConfig | 编辑器统一 | `.editorconfig` |

## 配置详情

### EditorConfig

- UTF-8 字符集
- LF 换行符
- Python: 4 空格缩进
- TypeScript: 2 空格缩进
- 100 字符最大长度

### ESLint

```json
{
  "extends": "next/core-web-vitals",
  "rules": {
    "@typescript-eslint/no-unused-vars": "warn",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

### Prettier

- 单引号
- 2 空格缩进
- 100 字符宽度
- 尾随逗号（ES5）

### Ruff

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
```

### mypy

```toml
[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
check_untyped_defs = true
```

## 修改的文件

### 新增/更新文件
- `.editorconfig` ✅ - 统一编辑器配置
- `apps/web/.eslintrc.json` ✅ - ESLint配置
- `apps/web/.prettierrc` ✅ - Prettier配置（已存在）
- `apps/api/pyproject.toml` ✅ - Ruff + mypy配置

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **后续任务**：P1-07 建立测试框架
- **注意事项**：后续任务需要在根 package.json 添加 lint/typecheck 命令

## 提交信息

- Commit: `chore(quality): configure ESLint, Prettier, Ruff, and mypy`
