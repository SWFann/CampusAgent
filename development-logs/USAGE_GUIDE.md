# 开发日志使用指南

开发日志只记录任务过程证据，不作为当前项目状态的权威来源。

## 基本流程

1. 从 `development-logs/templates/task-template.md` 复制任务模板。
2. 将新任务记录放入 `development-logs/in-progress/`。
3. 在任务过程中记录修改文件、关键决策、验证命令和遗留问题。
4. 任务完成后，移动到 `development-logs/completed/` 下对应阶段子目录。
5. 如涉及 P0/P1 状态变化，同步更新 `docs/project/P0_P1_REMEDIATION_PLAN.md`，并保留验证证据。

## 阶段归档

| 任务前缀 | 完成后目录 |
|---|---|
| `P0-*` | `development-logs/completed/p0-foundation/` |
| `P1-*` | `development-logs/completed/p1-engineering/` |
| `R0-*` | `development-logs/completed/remediation-r0/` |
| `R1-*` | `development-logs/completed/remediation-r1/` |
| `R2-*` | `development-logs/completed/remediation-r2/` |
| `R4-*` | `development-logs/completed/final-review-r4/` |
| `CODEX_*` | `development-logs/completed/codex/` |

## 权威口径

- 文档分类和阅读顺序：`docs/README.md`
- 项目状态和整改门禁：`docs/project/README.md`
- 日志系统说明：`development-logs/README.md`
