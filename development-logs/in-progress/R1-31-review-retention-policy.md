---
task_id: R1-31
status: in_progress
stage: R1
title: 复核保留策略
started_at: 2026-07-15T14:00:00+09:00
completed_at:
estimated_hours: 2
actual_hours:
---

# R1-31：复核保留策略

## 任务目标

系统复核 CampusAgent 全部 P0-P4 数据的保留期限（TTL）、删除策略、清理触发器、可恢复性、可导出性，确保所有文档中的保留策略口径一致。

## 权威口径

保留策略以 `DATA_INVENTORY.md §13 数据保留策略矩阵（R1-31 权威口径）` 为准。

## 涉及文件

| 文件 | 修改内容 |
|------|---------|
| `docs/architecture/DATA_INVENTORY.md` | 新增 §13 保留策略矩阵（14 类数据对象）；修正 AuditLog 90天→180天 |
| `docs/decisions/0005-data-retention.md` | AuditLog 90天→180天；新增 R1-31 权威口径引用 |
| `docs/api/API_CONTRACT.md` | 修正 AuditLog 3 处冲突（30天/90天/永久→180天）；变更记录 |
| `docs/api/WEBSOCKET_CONTRACT.md` | 变更记录引用 R1-31 |
| `docs/security/THREAT_MODEL.md` | §5.1 覆盖表加 RT 测试；FC-012 引用更新；变更记录 |
| `docs/privacy/PRIVACY_TEST_MATRIX.md` | 新增 §13 RT-001～RT-010；双向追踪矩阵更新；统计 90→100；章节重编号 |
| `docs/project/P0_P1_REMEDIATION_PLAN.md` | R1-31 `[x]`；完成摘要 |
| `docs/project/P0_COMPLETION_SUMMARY.md` | 测试数 90→100；AuditLog 90→180天 |
| `docs/project/P0_REVIEW_RECORD.md` | 测试数 90→100；R1-D 状态到 R1-31 |

## AuditLog 保留期限统一

发现冲突：
- `API_CONTRACT.md` Agent 区域：30天
- `API_CONTRACT.md` Scene 清理表：永久
- `API_CONTRACT.md` Model Gateway 区域：90天
- `ADR-0005`：90天
- `DATA_INVENTORY.md`：90天

统一为：**180天**（合规要求）

## 新增测试

- RT-001：Scene 结束后临时私有数据删除验证
- RT-002：私有胶囊删除验证
- RT-003：导出文件过期删除验证
- RT-004：AgentRun 保留期限验证（180天）
- RT-005：AuditLog 保留期限验证（180天）
- RT-006：Memory 级联删除验证
- RT-007：评价数据归档/删除验证
- RT-008：Token/Session 失效验证
- RT-009：审计日志导出验证
- RT-010：日志脱敏导出验证

## 执行状态

- [x] 读取所有 11 个文档扫描保留策略冲突
- [x] DATA_INVENTORY.md 新增 §13 保留策略矩阵
- [x] ADR-0005 同步 180天
- [x] API_CONTRACT.md 修正 3 处 AuditLog 冲突
- [x] WEBSOCKET_CONTRACT.md 变更记录
- [x] THREAT_MODEL.md §5.1 覆盖表加 RT 测试
- [x] PRIVACY_TEST_MATRIX.md 新增 RT-001～RT-010
- [x] P0_P1_REMEDIATION_PLAN.md R1-31 勾选
- [x] P0_COMPLETION_SUMMARY.md 更新
- [x] P0_REVIEW_RECORD.md 更新
- [x] 创建本日志
- [ ] 自检通过
- [ ] 等待 Codex 审计

## Codex 审计整改（2026-07-16）

### 整改内容

1. **修正 THREAT_MODEL.md 中 PRIVACY_TEST_MATRIX.md 章节引用残留**：
   - T-01～T-09 每个威胁的"权威定义"字段：`PRIVACY_TEST_MATRIX.md §13` → `PRIVACY_TEST_MATRIX.md §14（威胁—控制—测试追踪矩阵；具体测试定义见对应测试 ID 所在章节）`（共 9 处）
   - §4.3.5 附近：`§12（FC 测试定义）和 §13（追踪矩阵）` → `§12（FC 测试定义）；双向追踪矩阵见 §14`
   - §5.1 附近：`§12（FC 测试定义）和 §13（追踪矩阵，R1-30 更新）` → 列出 §12 FC、§13 RT、§14 追踪矩阵三个权威章节
   - 历史变更记录中描述当时章节迁移过程的文字保持不变（R1-29、R1-30 变更记录）

2. **当前权威章节**：
   - FC 测试定义：`PRIVACY_TEST_MATRIX.md §12`
   - RT 测试定义：`PRIVACY_TEST_MATRIX.md §13`
   - 威胁—控制—测试追踪矩阵：`PRIVACY_TEST_MATRIX.md §14`

3. **修正 API_CONTRACT.md Memory 访问记录保留期限歧义**：
   - Memory 访问记录接口（`GET /api/v1/memory/{memory_id}/access-records`）隐私约束中 `保留 90 天后自动清理（ADR-005）` → `作为 AuditLog metadata 保留 180 天后自动清理；权威口径见 DATA_INVENTORY.md §13`
   - 该接口返回的是访问审计元数据（访问者、访问目的、时间、结果、IP 脱敏），属于 AuditLog metadata 范畴
   - 采用推荐方案：统一为 AuditLog metadata 180 天

4. **AuditLog metadata 180 天权威口径仍以 `DATA_INVENTORY.md §13` 为准**

5. **R1-32 未执行**

6. **未提交、未推送，等待 Codex 复审**

### 涉及文件

| 文件 | 修改内容 |
|------|---------|
| `docs/security/THREAT_MODEL.md` | 修正 9 处"权威定义"§13→§14；修正 §4.3.5 和 §5.1 章节引用 |
| `docs/api/API_CONTRACT.md` | Memory 访问记录保留期限 90天 ADR-005 → AuditLog metadata 180天 |
| `development-logs/in-progress/R1-31-review-retention-policy.md` | 追加 Codex 审计整改记录 |
| `development-logs/in-progress/R1-30-check-privacy-fail-closed.md` | 追加 FC-012 TTL 补齐说明 |
