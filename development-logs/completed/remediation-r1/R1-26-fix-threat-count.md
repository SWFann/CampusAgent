---
task_id: R1-26
status: completed
stage: R1
title: 修正威胁数量
started_at: 2026-07-15
completed_at: 2026-07-15
estimated_hours: 0.5
actual_hours: 0.5
---

# R1-26：修正威胁数量

## 当前执行信息

- **执行日期**：2026-07-15
- **复核范围**：根据当前 THREAT_MODEL.md 威胁矩阵重新计算威胁数量和风险等级统计
- **前置条件**：R1-25 已通过 Codex 审计并归档

## 任务目标

1. 根据当前 THREAT_MODEL.md 的威胁矩阵重新计算威胁数量
2. 修正项目文档中的威胁数量和风险等级统计
3. 建立唯一、明确、可自动验证的威胁数量权威口径
4. 清理旧日志中错误的风险等级统计
5. 不越界处理 R1-27～R1-31 的任务

## 阅读的权威文档

1. `docs/security/THREAT_MODEL.md` — 威胁矩阵（§2.1）
2. `docs/project/P0_COMPLETION_SUMMARY.md`
3. `docs/project/P0_REVIEW_RECORD.md`
4. `docs/project/P0_P1_REMEDIATION_PLAN.md`
5. `development-logs/completed/remediation-r1/R1-25-fix-threat-numbers.md`
6. `development-logs/completed/remediation-r1/R1-25-fix-threat-numbers-2026-07-14-historical.md`
7. `development-logs/completed/remediation-r1/R1-26-fix-threat-count.md`（旧 completed 日志）
8. `development-logs/in-progress/R1-26-fix-threat-count.md`（旧 in-progress 日志）

## 矩阵实际统计

唯一权威数据源：`docs/security/THREAT_MODEL.md` §2.1 威胁矩阵的「风险等级」列。

逐行读取结果：

| 威胁ID | 风险等级（原始值） | 风险等级（去除格式后） |
|--------|------------------|---------------------|
| T-01 | **严重** | 严重 |
| T-02 | **高** | 高 |
| T-03 | **高** | 高 |
| T-04 | **高** | 高 |
| T-05 | **中** | 中 |
| T-06 | **高** | 高 |
| T-07 | **中** | 中 |
| T-08 | **高** | 高 |

## 权威统计结果

| 风险等级 | 数量 | 威胁编号 | 英文映射 |
|---------|---:|---------|---------|
| 严重 | 1 | T-01 | Critical |
| 高 | 5 | T-02、T-03、T-04、T-06、T-08 | High |
| 中 | 2 | T-05、T-07 | Medium |
| 低 | 0 | 无 | Low |
| **总计** | **8** | **T-01～T-08** | - |

**严重和高风险合计**：6 个（T-01、T-02、T-03、T-04、T-06、T-08）

## 旧日志错误统计

旧版 R1-26 日志中存在以下错误统计：

- Critical：2（T-01, T-02）
- High：4（T-03, T-04, T-06, T-08）

该统计不符合当前威胁矩阵。正确统计为：

- 严重（Critical）：1（T-01）
- 高（High）：5（T-02, T-03, T-04, T-06, T-08）

## 修改的文件

| # | 文件路径 | 修改内容 |
|---|---------|---------|
| 1 | `docs/security/THREAT_MODEL.md` | §2.2 新增「威胁数量统计（R1-26 权威口径）」小节；变更记录新增 R1-26 记录 |
| 2 | `docs/project/P0_COMPLETION_SUMMARY.md` | 威胁模型描述从"8 个威胁识别，6 个 critical/high 级别"改为精确口径"8 个威胁：严重（Critical）1 个、高（High）5 个、中（Medium）2 个、低（Low）0 个；严重/高风险合计 6 个" |
| 3 | `docs/project/P0_REVIEW_RECORD.md` | 通过项第 7 条从"6 个 critical/high 级别"改为精确口径 |
| 4 | `docs/project/P0_P1_REMEDIATION_PLAN.md` | R1-26 从 `[ ]` 改为 `[x]`；新增 R1-26 完成摘要；R1-25 日志路径更新为 completed |
| 5 | `development-logs/completed/remediation-r1/R1-26-fix-threat-count.md` | 旧 completed 日志增加历史警告 |
| 6 | `development-logs/in-progress/R1-26-fix-threat-count.md` | 本文件，整理为当前执行日志 |

## 未修改的内容

- ❌ 未修改威胁定义（编号、名称、描述）
- ❌ 未修改风险等级（可能性、影响、风险等级本身）
- ❌ 未修改控制状态（planned/implemented/verified/已缓解）
- ❌ 未新增或删除威胁
- ❌ 未修改 API 端点统计
- ❌ 未修改 WebSocket 统计
- ❌ 未修改测试映射
- ❌ 未修改业务代码、数据库模型、测试代码

## 自动检查命令和结果

### 1. 从矩阵自动提取风险等级

```
Total rows: 8
严重: 1 -> ['T-01']
高: 5 -> ['T-02', 'T-03', 'T-04', 'T-06', 'T-08']
中: 2 -> ['T-05', 'T-07']
低: 0 -> []
严重+高 = 6
```

### 2. 错误统计扫描

在 `docs/security/THREAT_MODEL.md`、`docs/project/P0_COMPLETION_SUMMARY.md`、`docs/project/P0_REVIEW_RECORD.md` 中扫描"Critical 2 / High 4"等错误统计：

- 当前权威文档中不存在"Critical 2、High 4"作为有效统计

### 3. 任务状态

- R1-25：`[x]`
- R1-26：`[x]`
- R1-27～R1-31：`[ ]`

## 后续任务状态

- R1-27：未执行
- R1-28：未执行
- R1-29：未执行
- R1-30：未执行
- R1-31：未执行

## 提交信息

- 已通过 Codex 审计
- 权威统计为严重 1、高 5、中 2、低 0
- 严重/高合计为 6
- 当前日志已经归档到 completed

## 后续状态更新

- R1-26 完成时统计为 8
- R1-28 新增 T-09 后，当前统计为 9
- 当前风险分布为严重 1、高 6、中 2、低 0
- R1-26 日志保留为任务完成时证据
