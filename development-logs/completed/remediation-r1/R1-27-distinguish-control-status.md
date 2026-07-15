---
task_id: R1-27
status: completed
stage: R1
title: 区分控制状态
started_at: 2026-07-15
completed_at: 2026-07-15
estimated_hours: 1.5
actual_hours: 1.5
---

# R1-27：区分控制状态

## 任务目标

消除 `docs/security/THREAT_MODEL.md` 中存在的控制状态矛盾，建立唯一、严格、可审计的控制状态体系，区分 `planned`、`implemented`、`verified` 三级状态。

**来自整改计划**：R1-27 - 区分控制状态

**产物**：
- 威胁控制状态标记
- 控制状态口径定义
- 矛盾表述清理

**依赖**：R1-26（已通过 Codex 审计，权威统计为严重 1、高 5、中 2、低 0）

## 控制状态定义

### planned（计划中）

- 控制已经在文档中设计；
- 尚无足够实现证据；
- 不得声称控制已经生效；
- 不得声称威胁已经缓解。

### implemented（已实施）

- 对应代码、配置、数据库迁移或运行组件已经实现；
- 有明确的实现证据；
- 尚未获得完整验证证据；
- `implemented` 不等于 `verified`；
- `implemented` 不得自动解释为威胁已经充分缓解。

### verified（已验证）

- `implemented` 控制已经通过对应测试或安全验证；
- 具备可追踪的测试记录、审计记录或验证证据；
- 只有 `verified` 才能作为更新实际残余风险的依据。
- 不规定必须"已经在生产环境运行"，测试环境中的正式验证也可构成验证证据；文档须记录验证环境和证据。

### 保守聚合规则

- 威胁级状态根据该威胁所需关键控制的最低成熟度确定；
- 只要任一必要控制仍为 `planned`，威胁级状态就不能高于 `planned`；
- 部分控制已经实现时，可以在控制明细中单独记录，但不得把整个威胁标记为 `implemented`；
- 状态升级必须有证据，不能仅凭文档描述升级；
- 本任务不创建 `partially_implemented` 等第四种状态。

### 状态升级证据要求

- `planned` → `implemented`：需要代码、配置、数据库迁移或运行组件的实现证据。
- `implemented` → `verified`：需要可追踪的测试记录、审计记录或验证证据，并记录验证环境。
- 不得仅凭文档描述升级状态。

## 威胁级状态统计

| 控制状态 | 威胁数量 | 威胁编号 |
|----------|---:|---------|
| `planned` | 8 | T-01～T-08 |
| `implemented` | 0 | 无 |
| `verified` | 0 | 无 |

## T-01～T-08 最终状态

| 威胁ID | 控制状态 | 计划实施阶段 |
|--------|---------|-------------|
| T-01 | `planned` | P2 |
| T-02 | `planned` | P2 |
| T-03 | `planned` | P2 |
| T-04 | `planned` | P3 |
| T-05 | `planned` | P2 |
| T-06 | `planned` | P2 |
| T-07 | `planned` | P3 |
| T-08 | `planned` | P2 |

## 语义修正内容

### 1. 计划措施与已实施措施的区分

- 将 **"缓解措施"** 改为 **"计划缓解措施"**；
- 将措施前的 ✅ 删除，替换为 **（planned）** 标识；
- 不得删除或重写控制措施的技术内容。

### 2. 检测机制语义修正

- 将 **"检测机制"** 改为 **"计划检测机制"**。

### 3. 测试描述语义修正

- 区分"测试用例已定义"与"测试已经执行并通过"；
- 将"全部覆盖"改为"已定义 N 个测试用例；计划在 P2/P3 阶段执行；本状态不代表测试已经运行或通过"；
- 不新增、删除或重新映射测试 ID（属于 R1-29）。

### 4. 残余风险语义修正

- 将 **"残余风险"** 改为 **"预计残余风险（计划控制完成并验证后）"**；
- 预计残余风险不是当前已经达到的风险状态；
- 只有必要控制达到 `verified`，才能将预计残余风险更新为经验证的实际残余风险；
- 本任务不接受任何新的残余风险；
- 本任务不修改风险等级。

## 修改文件

1. `docs/security/THREAT_MODEL.md`
   - §2.1 威胁矩阵：表头"状态"改为"控制状态"；T-01～T-08 全部从"🛡️ 已缓解"改为 `planned`
   - 新增 §2.2 控制状态口径（定义 planned/implemented/verified + 保守聚合规则）
   - 原 §2.2 重编号为 §2.3 威胁数量统计；修正措辞
   - T-01～T-08 详细分析：控制状态从 🔄 planned 改为 `planned`；✅ 改为 (planned)；"缓解措施"改为"计划缓解措施"；"检测机制"改为"计划检测机制"；"残余风险"改为"预计残余风险（计划控制完成并验证后）"；测试覆盖改为"已定义 N 个测试用例"
   - §4.1 状态说明："当前无"改为"当前为 0"
   - 新增威胁级控制状态统计表
   - §4.2 "未缓解威胁 / 所有威胁均已缓解" → "当前控制实施结论"
   - §6.1 T-04 "已最大限度缓解" → 条件性接受标准
   - 变更记录新增 R1-27 条目

2. `docs/project/P0_COMPLETION_SUMMARY.md`
   - "8 个缓解策略"改为"8 个计划缓解策略，当前控制状态均为 `planned`，尚无 `implemented` 或 `verified` 控制"

3. `docs/project/P0_REVIEW_RECORD.md`
   - 威胁控制状态项补充明确数量"planned：8，implemented：0，verified：0"

4. `docs/project/P0_P1_REMEDIATION_PLAN.md`
   - R1-27 从 `[ ]` 改为 `[x]`
   - 新增 R1-27 完成摘要
   - R1-26 日志路径从 in-progress 更新为 completed

5. `development-logs/in-progress/R1-27-distinguish-control-status.md`（本文件）
   - 重写为完整执行日志

6. `development-logs/completed/remediation-r1/R1-27-distinguish-control-status.md`
   - 新增历史警告 blockquote

7. `development-logs/completed/remediation-r1/R1-26-fix-threat-count.md`
   - 从 in-progress 移动到 completed；状态改为 completed

8. `development-logs/completed/remediation-r1/R1-26-fix-threat-count-2026-07-14-historical.md`
   - 旧 completed 日志重命名加 historical 后缀；历史警告中当前权威路径更新

## 未修改的任务范围

- R1-28（边缘节点威胁或 T-14）：未执行
- R1-29（威胁—测试映射）：未执行，未新增、删除或重新映射测试 ID
- R1-30（fail-closed 策略）：未执行
- R1-31（数据保留期限）：未执行
- R1-33（API 数量等 P0 总结历史问题）：未执行

## 自动检查命令和结果

### 威胁矩阵状态检查
```bash
# 解析 §2.1 的 8 行威胁，验证控制状态全部为 planned
rg -n "planned" docs/security/THREAT_MODEL.md | head
```

### 详细威胁状态检查
```bash
rg -n "^\*\*控制状态\*\*.*planned" docs/security/THREAT_MODEL.md
# 必须恰好匹配 8 个
```

### 错误声明扫描
```bash
rg -n "已缓解|所有威胁均已缓解|已最大限度缓解|全部覆盖|已实施|已验证" \
  docs/security/THREAT_MODEL.md \
  docs/project/P0_COMPLETION_SUMMARY.md \
  docs/project/P0_REVIEW_RECORD.md
```

### 预计残余风险字段检查
```bash
rg -n "预计残余风险" docs/security/THREAT_MODEL.md
# 必须恰好匹配 8 个
```

### 风险数量回归检查
```bash
# 确认 R1-26 数量未变：严重 1、高 5、中 2、低 0、总计 8
rg -n "严重.*1|高.*5|中.*2|低.*0|总计.*8" docs/security/THREAT_MODEL.md
```

## Git 状态

- 未提交
- 未推送
- 等待 Codex 审计

---

## Codex 审计整改（2026-07-15）

Codex 审计发现两处问题，已做最小范围整改：

### 整改一：统一 implemented 定义

- **问题**：§4.1 重复定义了 `planned`/`implemented`/`verified`，且 `implemented` 写为"已实现并部署"，与 §2.2 权威定义不一致。
- **处理**：删除 §4.1 重复的三条状态定义，替换为引用 §2.2 作为唯一权威来源的说明。保留后面的威胁级控制状态统计表。
- **结果**：全文不再出现第二套 `implemented` 定义。

### 整改二：修正虚假的整改完成声明

- **问题**：`P0_REVIEW_RECORD.md` 第 13 条声称"R1-A 到 R1-D 所有整改任务已完成，数字准确性已验证"，但 R1-01～R1-07 在当前计划中仍未勾选。
- **处理**：改为"整改进行中：完成状态以 P0_P1_REMEDIATION_PLAN.md 的任务勾选结果为准；R1-D 当前已完成 R1-25～R1-27，R1-28～R1-31 尚未完成"。
- **结果**：不再宣称 R1-A、R1-B、R1-C 已全部完成。

### 整改范围

- R1-28～R1-31 仍未执行；
- 当前日志在复审通过后归档到 `completed/remediation-r1`；
- 本批次由 Codex 统一提交并推送。

---

## Codex 最终复审（2026-07-15）

- 复审结论：通过；
- §2.2 为控制状态定义的唯一权威来源，§4.1 不再重复定义；
- 威胁矩阵共 8 行，全部为 `planned`，`implemented` 和 `verified` 均为 0；
- 详细威胁 `planned` 字段和预计残余风险字段均为 8 个；
- 风险统计保持严重 1、高 5、中 2、低 0；
- `P0_REVIEW_RECORD.md` 已取消虚假的 R1-A～R1-D 全部完成声明；
- R1-28～R1-31 仍未执行；
- `git diff HEAD --check` 通过。

## 后续状态更新

- R1-27 完成时 planned 为 8
- R1-28 新增 T-09 后 planned 为 9
- implemented 和 verified 仍为 0
- 控制状态定义不变
