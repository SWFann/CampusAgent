---
task_id: R1-32
status: completed
stage: R1
title: 修复全部内部链接
started_at: 2026-07-16T10:30:00+08:00
completed_at: 2026-07-16T15:20:00+08:00
estimated_hours: 2
actual_hours: 2
---

# R1-32：修复全部内部链接

## 任务目标

修复仓库中 P0 / R1 相关文档和 development-logs 的全部内部链接问题，确保 Markdown 内部链接路径全部有效、章节锚点全部能对应到真实标题、被归档的日志路径全部更新。

## 验收标准

1. Markdown 内部链接路径全部有效
2. 指向章节的锚点全部能对应到真实标题
3. 被重命名、移动、归档的日志路径全部更新
4. 不再引用已经删除或 historical 的日志作为当前权威记录
5. 文档中不再存在明显错误章节号
6. 链接检查结果为 0 个失效链接

## 检查范围

- `docs/` 全部 `.md` 文件
- `development-logs/` 全部 `.md` 文件

## 链接检查方法

使用 Python 脚本（临时，不放入仓库）：
1. 遍历 `docs/**/*.md` 和 `development-logs/**/*.md`
2. 提取 Markdown 链接（格式为方括号文本加圆括号路径）和裸路径引用
3. 跳过外部链接（http://、https://、mailto:、git@）
4. 对相对路径按源文件目录解析
5. 检查文件是否存在
6. 如有 `#anchor`，读取目标文件标题并生成 GitHub 风格 anchor 进行匹配
7. 输出失效链接列表

## 发现的问题

链接检查脚本首次运行发现 9 个失效 Markdown 链接，另有 3 处已归档日志旧路径引用（R1-30/R1-31 归档后路径过期）：

| 序号 | 源文件 | 失效链接 | 原因 |
|------|--------|---------|------|
| 1 | docs/api/API_CONTRACT.md | `development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md` | 相对路径缺少 `../../` 前缀 |
| 2 | docs/api/API_CONTRACT.md | `development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md` | 同上（第二处） |
| 3 | docs/api/API_CONTRACT.md | `docs/project/P0_P1_REMEDIATION_PLAN.md` | 应为 `../project/` 而非 `docs/project/` |
| 4 | docs/development/QUICK_START.md | `/README.md#python-虚拟环境` | 绝对路径应为相对路径 `../../README.md` |
| 5 | docs/development/QUICK_START.md | `/README.md` | 同上 |
| 6 | docs/development/TOOLING.md | `/README.md` | 同上 |
| 7 | development-logs/completed/p1-engineering/P1-05-establish-modules.md | `../architecture/MODULE_BOUNDARIES.md` | 应为 `../../../docs/architecture/` |
| 8 | development-logs/completed/remediation-r1/R1-22_FIX_WEBSOCKET_AUTH.md | `../architecture/PERMISSION_MATRIX.md` | 应为 `../../../docs/architecture/` |
| 9 | development-logs/completed/remediation-r1/R1-35-conduct-p0-review.md | `P0_REVIEW_RECORD.md` | 应为 `../../../docs/project/` |

另发现 3 处已归档日志中引用旧 in-progress 路径（R1-30/R1-31 归档后路径过期）。

## 修复的问题

### 1. API_CONTRACT.md 链接路径修复（3 处）

- `development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md` 改为 `../../development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md`（2 处）
- `docs/project/P0_P1_REMEDIATION_PLAN.md` 改为 `../project/P0_P1_REMEDIATION_PLAN.md`（1 处）

### 2. QUICK_START.md 链接路径修复（2 处）

- `/README.md#python-虚拟环境` 改为 `../../README.md#python-虚拟环境`
- `/README.md` 改为 `../../README.md`

### 3. TOOLING.md 链接路径修复（1 处）

- `/README.md` 改为 `../../README.md`

### 4. P1-05-establish-modules.md 链接路径修复（1 处）

- `../architecture/MODULE_BOUNDARIES.md` 改为 `../../../docs/architecture/MODULE_BOUNDARIES.md`

### 5. R1-22_FIX_WEBSOCKET_AUTH.md 链接路径修复（1 处）

- `../architecture/PERMISSION_MATRIX.md` 改为 `../../../docs/architecture/PERMISSION_MATRIX.md`

### 6. R1-35-conduct-p0-review.md 链接路径修复（1 处）

- `P0_REVIEW_RECORD.md` 改为 `../../../docs/project/P0_REVIEW_RECORD.md`

### 7. 已归档日志路径引用更新（3 处）

- R1-31 日志中 `development-logs/in-progress/R1-31-review-retention-policy.md` 改为 `development-logs/completed/remediation-r1/R1-31-review-retention-policy.md`
- R1-31 日志中 `development-logs/in-progress/R1-30-check-privacy-fail-closed.md` 改为 `development-logs/completed/remediation-r1/R1-30-check-privacy-fail-closed.md`
- R1-30 日志中 `development-logs/in-progress/R1-30-check-privacy-fail-closed.md` 改为 `development-logs/completed/remediation-r1/R1-30-check-privacy-fail-closed.md`

### 8. R1-30/R1-31 日志归档

- `development-logs/in-progress/R1-30-check-privacy-fail-closed.md` 移动到 `development-logs/completed/remediation-r1/R1-30-check-privacy-fail-closed.md`，front matter 更新为 `status: completed`
- `development-logs/in-progress/R1-31-review-retention-policy.md` 移动到 `development-logs/completed/remediation-r1/R1-31-review-retention-policy.md`，front matter 更新为 `status: completed`
- 旧版 `R1-30-check-privacy-failure-shutdown.md` 重命名为 `R1-30-check-privacy-failure-shutdown-historical.md`，front matter 标记 `status: historical`
- 旧版 `R1-31-review-retention-policies.md` 重命名为 `R1-31-review-retention-policies-historical.md`，front matter 标记 `status: historical`

### 9. R1-32 日志冲突解决

- 旧版 `development-logs/completed/remediation-r1/R1-32-fix-internal-links.md` 重命名为 `R1-32-fix-internal-links-historical.md`，front matter 标记 `status: historical`
- 当前 R1-32 权威日志保留在 `development-logs/completed/remediation-r1/R1-32-fix-internal-links.md`

### 10. Codex 审计整改

- 恢复 .github/、Makefile、MEMORY.md、R2/R4 脚本等 CRLF 噪声文件到 HEAD，使其不出现在 git diff 中
- 从 P0_P1_REMEDIATION_PLAN.md R1-32 完成摘要中移除不属于 R1-32 范围的"Codex 审计补充修复"行

## 未修复但判定为历史引用的问题

以下 §13 追踪矩阵引用位于历史变更记录中，描述当时章节迁移过程，不作为当前权威口径，保留不动：

1. **THREAT_MODEL.md 变更记录**：
   - R1-29 变更记录中 "改为引用 PRIVACY_TEST_MATRIX.md §13 权威追踪矩阵"（当时 §13 确为追踪矩阵）
   - R1-30 变更记录中 "更新所有 §12 引用为 §13（追踪矩阵重新编号）"（当时追踪矩阵从 §12 重编号为 §13）

2. **R1-31 日志 Codex 审计记录**：
   - "T-01～T-09 每个威胁的'权威定义'字段：§13 改为 §14"（描述修改过程，非当前引用）
   - "§4.3.5 附近：§12（FC 测试定义）和 §13（追踪矩阵）改为 §12（FC 测试定义）；双向追踪矩阵见 §14"（同上）
   - "§5.1 附近：§12（FC 测试定义）和 §13（追踪矩阵，R1-30 更新）改为 ..."（同上）

当前正文中的权威引用均已正确：
- THREAT_MODEL.md 中 9 处"权威定义"字段均指向 §14
- FC 测试定义引用 §12
- 保留策略引用均指向 DATA_INVENTORY.md §13

## 自检结果

1. **链接检查**：
   - 执行方脚本统计口径：扫描 151 个文件，146 个 Markdown 链接，141 个内部链接，修复后失效链接 0 个
   - Codex 复核口径：files=152，checked_internal_links=141，external_links=4，broken=0
   - 两口径差异原因：执行方脚本统计时未包含本次新增的 R1-32 日志文件本身（152 vs 151），内部链接数一致（141）
2. **章节引用检查**：当前正文中不存在把 §13 称为追踪矩阵的权威引用；历史变更记录中的 §13 引用保留为历史记录
3. **保留策略引用检查**：所有保留策略当前口径均指向 DATA_INVENTORY.md §13
4. **日志归档检查**：
   - in-progress 中不再残留 R1-30/R1-31 正文任务日志
   - R1-32 当前权威日志位于 development-logs/completed/remediation-r1/R1-32-fix-internal-links.md
   - R1-30/R1-31 权威日志在 completed/remediation-r1；无重复权威日志
   - 其他历史残留 in-progress 文件/检查脚本不属于本次 R1-32 新增范围，后续单独处理
5. **任务状态检查**：R1-30 `[x]`、R1-31 `[x]`、R1-32 `[x]`、R1-33～R1-36 `[ ]`
6. **回归检查**：测试定义 100、威胁 9、planned=9/implemented=0/verified=0、API 71、WebSocket v1.0-frozen
7. **Git 检查**：git diff HEAD --check 退出码为 0；未提交、未推送

## 声明

- 未提交、未推送，等待 Codex 审计
