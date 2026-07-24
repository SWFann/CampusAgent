# 依赖更新策略

## 概述

本文档定义 CampusAgent 项目的依赖管理和更新策略。

**最后更新**：2026-07-20

---

## 自动化更新

### Dependabot

项目使用 GitHub Dependabot 自动化依赖更新。

**配置**：`.github/dependabot.yml`

**更新频率**：每周一上午 9:00

**分组策略**：

| 组 | 包含 | 描述 |
|----|------|------|
| dev-dependencies | 开发依赖 | ESLint, Prettier, Testing 库 |
| production-dependencies | 生产依赖 | React, Next.js 等 |
| all-dependencies | 所有 Python 包 | FastAPI, SQLAlchemy 等 |

---

## 手动更新流程

### 何时手动更新

1. **安全漏洞修复**：立即更新
2. **重大 bug 修复**：测试后立即更新
3. **性能改进**：评估后更新
4. **新功能需求**：计划更新

### 更新步骤

1. **检查当前版本**

   ```bash
   # 前端
   pnpm outdated

   # 后端
   uv tree --project apps/api --outdated
   ```

2. **更新依赖**

   ```bash
   # 前端
   pnpm update

   # 后端
   # 先修改 apps/api/pyproject.toml 中的版本范围，再更新锁文件
   uv lock --project apps/api --upgrade-package <package>
   uv sync --project apps/api --extra dev --frozen
   ```

3. **运行测试**

   ```bash
   make test
   make typecheck
   ```

4. **提交更新**

   ```bash
   git add pnpm-lock.yaml
   git add apps/api/pyproject.toml apps/api/uv.lock
   git commit -m "chore(deps): update <package> to v<version>"
   ```

---

## 锁文件策略

### pnpm-lock.yaml

- **提交到 Git**：是
- **何时更新**：每次依赖变更后
- **评审规则**：PR 中需要审查锁文件变更

### apps/api/uv.lock

- **提交到 Git**：是
- **何时更新**：每次依赖变更后
- **评审规则**：PR 中需要审查锁文件变更

`pyproject.toml` 声明直接依赖，`uv.lock` 锁定完整依赖图。禁止使用系统 `pip install` 修改宿主 Python 环境。

---

## 版本升级政策

### 主版本升级（Major）

**示例**：Next.js 14 → 15

**要求**：
- [ ] 仔细阅读 Breaking Changes
- [ ] 在独立分支测试
- [ ] 更新所有相关代码
- [ ] 更新文档
- [ ] 完整测试
- [ ] 团队评审

**时间**：计划升级，不立即合并

### 次版本升级（Minor）

**示例**：FastAPI 0.109 → 0.110

**要求**：
- [ ] 阅读 Release Notes
- [ ] 本地测试
- [ ] 更新文档（如有必要）

**时间**：可以较快合并

### 补丁版本升级（Patch）

**示例**：React 18.2.0 → 18.2.1

**要求**：
- [ ] 可以安全更新
- [ ] CI 通过

**时间**：可以快速合并

---

## 安全更新

### 优先级

1. **Critical**：立即处理（24 小时内）
2. **High**：尽快处理（1 周内）
3. **Medium**：计划处理（1 个月内）
4. **Low**：常规更新

### 处理流程

1. Dependabot 自动创建安全 PR
2. 运行 CI 验证
3. 手动测试（如必要）
4. 合并并部署

### 工具

- **GitHub Dependabot**：自动检测安全漏洞
- **Snyk**：（可选）深度安全扫描
- **npm audit**：前端依赖检查
- **uv**：后端依赖解析、锁定与环境同步

---

## 废弃依赖

### 识别废弃依赖

```bash
# 检查废弃的 npm 包
pnpm outdated

# 检查废弃的 pip 包
pip check
```

### 处理废弃依赖

1. 评估影响范围
2. 寻找替代方案
3. 计划迁移
4. 实现迁移
5. 删除旧依赖

---

## 依赖选择标准

### 添加新依赖前

1. **必要性**：是否可以自己实现？
2. **维护状态**：最近有更新吗？
3. **社区**：Star 数、下载量、Issue 响应
4. **许可证**：MIT/Apache-2.0 优先
5. **包体积**：是否太大？
6. **类型定义**：是否有 TypeScript 类型？

### 不推荐的依赖

- 长期未维护
- 存在安全漏洞
- 许可证不兼容
- 没有 TypeScript 类型（前端）

---

## 相关文档

- [开发计划表](../development/DEVELOPMENT_PLAN.md)
- [GitHub Dependabot 文档](https://docs.github.com/en/code-security/dependabot)

---

**维护者**：开发团队
