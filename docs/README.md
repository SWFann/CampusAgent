# CampusAgent 文档中心

本文档是仓库文档的总入口。开发时优先阅读“权威文档”，开发日志只作为过程证据，不作为当前口径。

## 阅读顺序

1. 产品和范围：[项目概览](product/PROJECT_OVERVIEW.md)、[MVP 范围](product/MVP_SCOPE.md)、[完整项目计划书](product/CampusAgent_Project_Plan.md)
2. 当前状态：[P0/P1 整改计划](project/P0_P1_REMEDIATION_PLAN.md)、[P0 复审记录](project/P0_REVIEW_RECORD.md)、[P1 完成总结](project/P1_COMPLETION_SUMMARY.md)
3. 架构边界：[模块边界](architecture/MODULE_BOUNDARIES.md)、[数据流](architecture/DATA_FLOW.md)、[权限矩阵](architecture/PERMISSION_MATRIX.md)
4. API 契约：[API 文档入口](api/README.md)、[HTTP API 契约](api/API_CONTRACT.md)、[WebSocket 契约](api/WEBSOCKET_CONTRACT.md)
5. 开发执行：[快速开始](development/QUICK_START.md)、[Conda 环境](development/CONDA_ENV.md)、[工具链](development/TOOLING.md)、[开发计划](development/DEVELOPMENT_PLAN.md)
6. Demo 和 UI：[Demo 规范](demo/DEMO_SPEC.md)、[UI 设计指南](design/UI_DESIGN_GUIDE.md)

## 分类规则

| 目录 | 定位 | 是否权威 | 使用方式 |
|---|---|---:|---|
| `product/` | 产品定位、MVP 边界、用户旅程 | 是 | 判断要不要做、做到什么程度 |
| `domain/` | 领域词汇和统一命名 | 是 | 命名、枚举、文案以此为准 |
| `architecture/` | 模块、数据、权限、状态机 | 是 | 判断代码边界和跨模块依赖 |
| `api/` | HTTP、WebSocket、事件契约 | 是 | 前后端、测试和 Mock 的共同依据 |
| `privacy/` | 隐私基线和测试矩阵 | 是 | 隐私优先约束和验收依据 |
| `security/` | 威胁模型和安全要求 | 是 | 安全审计和风险整改依据 |
| `demo/` | 比赛 Demo 流程和验收 | 是 | P2 之后实现演示闭环 |
| `design/` | UI 设计方向和自然语言规范 | 是 | 指导界面设计和交互风格 |
| `development/` | 环境、命令、协作规范 | 是 | 本地开发、CI、工具链执行 |
| `decisions/` | ADR 架构决策记录 | 是 | 解释关键技术和产品决策 |
| `project/` | 阶段状态、审计、整改计划 | 是 | 判断当前阶段能否进入下一阶段 |

## 非权威记录

`development-logs/` 是开发过程证据库，记录每个任务的执行过程、验证命令和历史结论。它可以帮助审计，但不能覆盖 `docs/` 下的当前权威文档。

如果两类文档冲突，以 `docs/` 中对应分类的文档为准；如果 `docs/project/` 的审计结论与完成总结冲突，以最新复审记录和整改计划为准。

## 维护原则

- 新增长期有效文档时，放入 `docs/` 的对应分类目录。
- 新增任务过程记录时，放入 `development-logs/in-progress/`，完成后归入 `development-logs/completed/` 的阶段子目录。
- 不在多个文档中重复维护同一份事实；需要引用时链接到权威文档。
- 阶段状态只能由 `docs/project/` 维护，开发日志不得单独宣布 P0/P1 已完成。
- 进入 P2 前，先确认 `P0_P1_REMEDIATION_PLAN.md` 和 `P0_REVIEW_RECORD.md` 没有互相矛盾。
