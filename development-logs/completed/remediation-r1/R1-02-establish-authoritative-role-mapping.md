---
task_id: R1-02
status: completed
stage: R1
title: 建立权威角色映射
started_at: 2026-07-14T12:38:00+09:00
completed_at: 2026-07-14T12:39:00+09:00
estimated_hours: 1
actual_hours: 0.25
---

# R1-02：建立权威角色映射

## 完成状态

✅ **权威角色映射已建立**

**完成时间**：2026-07-14T12:39:00+09:00

## 目标

记录角色变更 ADR，解释 Counselor 和 OrganizationAdmin（现 ORG_ADMIN）属于全局角色还是组织授权能力。

**来自整改计划**：R1-02 - 记录角色变更 ADR

## 验收标准

- [x] 解释 COUNSELOR 属于全局角色还是组织授权能力
- [x] 解释 ORG_ADMIN 属于全局角色还是组织授权能力
- [x] ADR 已创建或更新

## 实现过程

### 创建 ADR-006

创建了新的 ADR-006（`docs/decisions/0006-role-model.md`），内容包括：

1. **背景**：P0 阶段定义权限体系时角色模型的选择
2. **问题**：4-role vs 6-role 方案对比
3. **决策**：采用 6-role 系统（R1-01 的 D-001 决策）
4. **角色定位**：
   - GlobalRole（全局角色）：STUDENT, TEACHER, COUNSELOR, ORG_ADMIN, SCHOOL_ADMIN, SYSTEM_ADMIN
   - OrganizationRole（组织内角色）：OWNER, ADMIN, MEMBER, GUEST
5. **关键决策**：
   - COUNSELOR 属于全局角色（跨组织可见性）
   - ORG_ADMIN 属于全局角色（全局授权便于审计）
6. **枚举对照表**：数据库值、API 值、中文名一一对应

## 权威角色映射

### GlobalRole 枚举

| 角色 | 定位 | 权限范围 |
|------|------|---------|
| STUDENT | 基础用户 | 使用通讯、智能体、场景和个人记忆 |
| TEACHER | 教育者 | 创建课程组织、发布讨论、管理课程成员 |
| COUNSELOR | 支持人员 | 管理被授权的支持场景，不可读取默认私有数据 |
| ORG_ADMIN | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
| SCHOOL_ADMIN | 学校管理员 | 管理学校组织、账号、模型和节点 |
| SYSTEM_ADMIN | 系统管理员 | 系统配置、运维和安全审计 |

### OrganizationRole 枚举

| 角色 | 说明 |
|------|------|
| OWNER | 组织所有者，拥有全部权限 |
| ADMIN | 组织管理员，可管理成员和设置 |
| MEMBER | 普通成员，参与组织活动 |
| GUEST | 访客，仅可查看公开内容 |

## 验证结果

- [x] COUNSELOR 角色定位已明确（全局角色）
- [x] ORG_ADMIN 角色定位已明确（全局角色）
- [x] ADR-006 已创建
- [x] 枚举对照表完整

## 下一步

- **R1-03**：统一数据清单角色（修复 CampusAgent_Project_Plan.md 中的命名不一致）

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
