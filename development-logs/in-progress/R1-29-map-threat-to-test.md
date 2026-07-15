---
task_id: R1-29
status: in_progress
stage: R1
title: 建立威胁—控制—测试双向映射
started_at: 2026-07-15
completed_at:
estimated_hours: 3
actual_hours:
---

# R1-29：建立威胁—控制—测试双向映射

## 任务目标

建立双向追踪：

- 威胁 → 计划控制 → 正式测试 ID → 测试定义
- 测试 ID → 对应威胁 → 验证的计划控制

## 验收要求

1. T-01～T-09 每个威胁至少有一个真实测试 ID。
2. 严重/高风险 7 个威胁均至少有拒绝、失败关闭或泄露检测测试。
3. 所有测试 ID 在 PRIVACY_TEST_MATRIX.md 中唯一且完整定义。
4. 最终 78 个测试 ID 全部至少映射一个威胁。
5. R1-29 权威映射不得出现"待补充"。
6. 定义状态统一为 `defined`。
7. 执行状态统一为 `not_run`。
8. 不得出现 passed、executed、verified、全部通过、零缺陷等结论。

## 任务边界

- 只修改文档和开发日志，不写业务代码和测试代码。
- R1-30、R1-31 不得执行。
- 不提交、不推送，等待 Codex 审计。
- 保留当前所有未提交修改；禁止 reset、restore、checkout、clean、stash 或覆盖现有文件。
- 当前威胁为 T-01～T-09，共 9 个。
- 控制状态必须保持 planned=9，implemented=0，verified=0。
- THREAT_MODEL.md 中 ST-01～ST-08 必须删除；ST-09 不得恢复。
- PRIVACY_TEST_MATRIX.md 中 ST-001～ST-005 是正式 ID，必须保留。

## 开始前 Git 状态（2026-07-15）

- 分支：main
- HEAD：aedd8c228f120d74d50c1986ff5bdf1b567e3391
- 提交：docs(security): normalize threat model status and counts
- 工作树：大量未提交修改（R1-25～R1-28 整改产物，含 CRLF 规整修改）
- 未跟踪：`development-logs/in-progress/R1-28-supplement-edge-node-threat.md`
- `git diff HEAD --check`：已存在的非本次修改文件（`.github/dependabot.yml` 等）存在 trailing whitespace 报告，属于历史 CRLF 规整产物，不在本次整改范围。

## 旧文件处理

1. `development-logs/completed/remediation-r1/R1-29-map-threat-to-test.md`
   → 重命名为 `R1-29-map-threat-to-test-2026-07-14-historical.md`，front matter 后增加历史记录说明。
2. `development-logs/in-progress/R1-29-map-threat-to-test.py`
   → 移动并改名为 `development-logs/completed/remediation-r1/R1-29-map-threat-to-test-legacy.py.txt`，开头增加 HISTORICAL TOOL — DO NOT EXECUTE 警告。
3. `development-logs/in-progress/R1-29-map-threat-to-test-v2.py`
   → 移动并改名为 `development-logs/completed/remediation-r1/R1-29-map-threat-to-test-v2-legacy.py.txt`，开头增加 HISTORICAL TOOL — DO NOT EXECUTE 警告。
4. 新建当前日志 `development-logs/in-progress/R1-29-map-threat-to-test.md`。

## 执行步骤

1. 处理旧 R1-29 文件（重命名、移动、加警告）
2. 验证修改前 51 个测试基线
3. 在 PRIVACY_TEST_MATRIX.md 增加 27 个正式测试定义（PI/RP/MR/EN）
4. 修正现有测试矩阵问题（PT-203、PT-305、LG 表、Node 权限）
5. 建立权威双向追踪矩阵（正向表 + 反向表）
6. 修改 THREAT_MODEL.md（删除 ST-01～ST-08、更新 T-01～T-09 测试信息、变更记录）
7. 归档 R1-28 日志到 completed
8. 更新项目文档（P0_REVIEW_RECORD、P0_COMPLETION_SUMMARY、P0_P1_REMEDIATION_PLAN）
9. 执行全部自动自检并报告

## 修改前测试基线

- PT=25
- ST=5
- CL=5
- LG=9
- REV=4
- EXP=3
- 总计=51

## 未执行的任务范围

- R1-30（检查隐私失败关闭）：未执行
- R1-31（复核保留策略）：未执行

## 修改文件清单

1. `docs/privacy/PRIVACY_TEST_MATRIX.md` — 新增 §1.1 测试 ID 注册规则；修正 PT-203、PT-305、LG 表；新增 §8 PI 测试、§9 RP 测试、§10 MR 测试、§11 EN 测试（共 27 个定义）；新增 §12 双向追踪矩阵（正向+反向+统计+覆盖）；更新变更记录
2. `docs/security/THREAT_MODEL.md` — 删除 §5.1 中 ST-01～ST-08，改为引用 PRIVACY_TEST_MATRIX.md §12；更新 T-01～T-09 测试覆盖章节（defined/not_run）；追加 R1-29 变更记录
3. `docs/architecture/PERMISSION_MATRIX.md` — 修正 §5.5 SCHOOL_ADMIN node 权限为 read/list/health-check；修正 §10.3 节点权限表（SCHOOL_ADMIN 不可创建/修改/删除节点）
4. `docs/project/P0_REVIEW_RECORD.md` — 更新测试数量为 78；删除"T-03、T-04、T-05、T-08 缺少测试"；更新 R1-25～R1-29 完成状态
5. `docs/project/P0_COMPLETION_SUMMARY.md` — 更新测试数量为 78（51+27）；更新测试分类明细
6. `docs/project/P0_P1_REMEDIATION_PLAN.md` — R1-29 标记 [x]；更新 R1-28 日志路径为 completed；追加 R1-29 完成摘要
7. `development-logs/completed/remediation-r1/R1-28-supplement-edge-node-threat.md` — 从 in-progress 移到 completed；更新 status: completed；追加 Codex 复审通过记录
8. `development-logs/completed/remediation-r1/R1-29-map-threat-to-test-2026-07-14-historical.md` — 旧日志重命名，追加历史记录说明
9. `development-logs/completed/remediation-r1/R1-29-map-threat-to-test-legacy.py.txt` — 旧脚本移动改名，追加 DO NOT EXECUTE 警告
10. `development-logs/completed/remediation-r1/R1-29-map-threat-to-test-v2-legacy.py.txt` — 旧脚本移动改名，追加 DO NOT EXECUTE 警告
11. `development-logs/in-progress/R1-29-map-threat-to-test.md` — 新建当前日志

## 自检结果

| 检查项 | 预期 | 实际 | 结果 |
|---|---|---|---|
| PT 定义 | 25 | 25 | OK |
| ST 定义 | 5 | 5 | OK |
| CL 定义 | 5 | 5 | OK |
| LG 定义 | 9 | 9 | OK |
| REV 定义 | 4 | 4 | OK |
| EXP 定义 | 3 | 3 | OK |
| PI 定义 | 5 | 5 | OK |
| RP 定义 | 5 | 5 | OK |
| MR 定义 | 5 | 5 | OK |
| EN 定义 | 12 | 12 | OK |
| 总计 | 78 | 78 | OK |
| 唯一 ID | 78 | 78 | OK |
| 重复定义 | 0 | 0 | OK |
| MATRIX 威胁 | 9 | 9 | OK |
| DETAIL 威胁 | 9 | 9 | OK |
| 集合差异 | 0 | 0 | OK |
| 严重 | 1 | 1 | OK |
| 高 | 6 | 6 | OK |
| 中 | 2 | 2 | OK |
| 低 | 0 | 0 | OK |
| 严重/高合计 | 7 | 7 | OK |
| planned | 9 | 9 | OK |
| implemented | 0 | 0 | OK |
| verified | 0 | 0 | OK |
| ST-0[1-9] in THREAT_MODEL | 0 | 0 | OK |
| ST-001～ST-005 保留 | 5 | 5 | OK |
| PT-205/PT-206 | 0 | 0 | OK |
| passed | 0 | 0 | OK |
| executed | 0 | 0 | OK |
| verified (状态词) | 0 | 0 | OK |
| 待补充 in 映射 | 0 | 0 | OK |
| §4.3.5 "待补充"清理 | 0 | 0 | OK |
| 有测试的威胁 | 9 | 9 | OK |
| 有映射的测试 | 78 | 78 | OK |
| 无映射的测试 | 0 | 0 | OK |
| in-progress R1-28 | 0 | 0 | OK |
| completed R1-28 | 1 | 1 | OK |
| in-progress R1-29 | 1 | 1 | OK |
| historical R1-29 | 1 | 1 | OK |
| legacy .py.txt | 2 | 2 | OK |
| R1-28=[x] | 是 | 是 | OK |
| R1-29=[x] | 是 | 是 | OK |
| R1-30=[ ] | 是 | 是 | OK |
| R1-31=[ ] | 是 | 是 | OK |
| git diff HEAD --check (R1-29 文件) | 通过 | 通过 | OK |
| .backup/.bak/.tmp/.copy | 0 | 0 | OK |
| 新 R1-29 .py 脚本 | 0 | 0 | OK |
| apps/packages/tests/infra 修改 | 0 | 0 | OK |

## Git 状态

- 未提交
- 未推送
- 等待 Codex 审计

## Codex 审计整改（2026-07-15）

R1-29 主体已通过 Codex 审计，但发现两个文档一致性问题，已做最小范围整改：

1. 删除当前权威文档中的"待补充"测试 ID 表述（THREAT_MODEL.md §4.3.5）；
2. 将 THREAT_MODEL.md §4.3.5 明确标注为 R1-30 范围，不属于 R1-29 权威追踪矩阵；补充"R1-29 的正式测试定义和双向追踪矩阵以 docs/privacy/PRIVACY_TEST_MATRIX.md §12 为唯一权威来源"；
3. 修正 P0_REVIEW_RECORD.md 中"整改验证通过（R1-A 到 R1-D）"的误导表述，改为"整改验证进行中：R1-A～R1-C 已通过，R1-D 已完成 R1-25～R1-29，R1-30～R1-31 待完成"；
4. R1-29 测试矩阵主体（78 个测试定义、正向/反向追踪矩阵）未修改；
5. R1-30、R1-31 仍未执行；
6. 未提交、未推送，等待 Codex 复审。
