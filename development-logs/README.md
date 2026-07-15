# 开发日志系统

`development-logs/` 用于记录 CampusAgent 的开发过程和审计证据。它不是产品、架构、API 或项目状态的权威文档；权威文档统一放在 `docs/`。

## 目录结构

```text
development-logs/
├── README.md
├── PROGRESS.md
├── NEXT_STEPS.md
├── USAGE_GUIDE.md
├── in-progress/          # 正在执行的任务记录和临时检查脚本
├── completed/            # 已完成任务记录，按阶段归档
│   ├── p0-foundation/
│   ├── p1-engineering/
│   ├── remediation-r0/
│   ├── remediation-r1/
│   ├── remediation-r2/
│   ├── final-review-r4/
│   └── codex/
└── templates/            # 任务记录模板
```

## 使用规则

- 开始一个任务时，在 `in-progress/` 创建任务记录。
- 任务完成后，移动到 `completed/` 的对应阶段子目录。
- 日志必须记录修改文件、验证命令、验证结果和遗留问题。
- 日志不得单独宣布阶段完成；P0/P1 状态以 `docs/project/` 为准。
- 临时检查脚本可以放在 `in-progress/`，但任务完成后应删除、迁移到正式脚本目录，或在日志中说明保留原因。

## 阶段目录

| 阶段 | 归档目录 | 说明 |
|---|---|---|
| P0 | `completed/p0-foundation/` | 原始产品、隐私、架构和 API 契约规划 |
| P1 | `completed/p1-engineering/` | 工程骨架、工具链、CI 和环境初始化 |
| R0 | `completed/remediation-r0/` | 整改前基线、安全检查和工作树记录 |
| R1 | `completed/remediation-r1/` | P0 契约一致性整改 |
| R2 | `completed/remediation-r2/` | 后端和测试底座整改 |
| R4 | `completed/final-review-r4/` | 阶段验收、复审和最终门禁 |
| Codex | `completed/codex/` | Codex 独立补充整改记录 |

## 与 `docs/` 的关系

当日志与 `docs/` 冲突时，以 `docs/` 为准。日志只回答“当时做了什么、怎么验证”，不回答“现在项目是否已经完成某阶段”。
