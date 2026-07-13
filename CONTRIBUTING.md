# 贡献指南

## 开始之前

1. 阅读根目录 README、完整项目计划书和隐私工程基线；
2. 确认改动属于当前里程碑，不擅自扩大 MVP；
3. 涉及跨模块契约、数据保留或隐私边界的变更先提交 ADR；
4. 禁止在 Issue、提交、日志、种子数据或截图中放入真实学生信息和真实密钥。

## 分支与提交

分支格式：

```text
feature/<module>-<description>
fix/<module>-<description>
docs/<topic>-<description>
```

提交信息遵循 Conventional Commits，例如：

```text
feat(scene): add private meal submission contract
fix(memory): reject access after consent revocation
docs(privacy): clarify temporary data retention
```

## 模块交付要求

每个模块交付都应说明：目标、新增文件、数据模型、API、权限、事件、测试、验证命令、已知限制和对外公开契约。

Pull Request 至少满足：

- 变更范围清楚，关联 Issue 或 ADR；
- 测试与隐私回归通过；
- OpenAPI/事件契约同步更新；
- 数据库变更提供迁移；
- 不跨模块导入 ORM Model 或直接修改其他模块的数据表；
- 日志、错误和示例中没有敏感内容；
- 至少一名评审者批准后再合并。

更完整的约束见 [仓库协作规范](docs/development/REPOSITORY_CONVENTIONS.md)。
