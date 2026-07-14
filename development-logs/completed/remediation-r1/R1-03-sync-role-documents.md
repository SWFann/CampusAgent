---
task_id: R1-03
status: completed
stage: R1
title: 统一数据清单角色
completed_at: 2026-07-14T12:41:00+09:00
estimated_hours: 1
actual_hours: 0.25
---

# R1-03：统一数据清单角色

## 完成状态

✅ **角色文档已统一**

**完成时间**：2026-07-14T12:41:00+09:00

## 目标

同步所有文档中的角色名称，确保完全一致。

**来自整改计划**：R1-03 - 统一数据清单角色

## 验收标准

- [x] 计划书、词汇表、权限矩阵、API 示例中的角色名称完全一致
- [x] 所有文档使用标准角色名称（ORG_ADMIN，而非 OrganizationAdmin）

## 修改的文件

### docs/product/CampusAgent_Project_Plan.md

**位置**：第 285 行

**修改前**：
```markdown
| OrganizationAdmin | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
```

**修改后**：
```markdown
| ORG_ADMIN | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
```

## 验证结果

- [x] 搜索所有文档中的角色名称
- [x] 确认仅 CampusAgent_Project_Plan.md 有命名不一致（已修复）
- [x] 确认权威文档（DOMAIN_VOCABULARY.md, PERMISSION_MATRIX.md, API_CONTRACT.md）均已使用 ORG_ADMIN
- [x] 剩余 OrganizationAdmin 仅在整改计划中（R1-02 的验收检查说明）

## 文档一致性检查

### 权威文档（均使用 ORG_ADMIN）✅

- `docs/domain/DOMAIN_VOCABULARY.md` - ✅ ORG_ADMIN
- `docs/architecture/PERMISSION_MATRIX.md` - ✅ ORG_ADMIN
- `docs/api/API_CONTRACT.md` - ✅ ORG_ADMIN
- `docs/architecture/DATA_FLOW.md` - ✅ ORG_ADMIN
- `docs/security/THREAT_MODEL.md` - ✅ ORG_ADMIN
- `docs/privacy/PRIVACY_TEST_MATRIX.md` - ✅ ORG_ADMIN
- `docs/product/CampusAgent_Project_Plan.md` - ✅ 已修复

### 枚举值标准化

所有文档统一使用：
- `STUDENT`, `TEACHER`, `COUNSELOR`
- `ORG_ADMIN`, `SCHOOL_ADMIN`, `SYSTEM_ADMIN`
- `OWNER`, `ADMIN`, `MEMBER`, `GUEST`

## 下一步

- **R1-04**：清理待讨论术语

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
