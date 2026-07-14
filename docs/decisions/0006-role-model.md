# ADR-006：领域角色模型

**状态**：Accepted
**日期**：2026-07-14
**决策者**：开发团队
**相关决策**：D-001（GlobalRole 权威枚举），D-002（COUNSELOR 和 ORG_ADMIN 角色定位）

---

## 背景

在 P0 阶段定义了 CampusAgent 的权限体系，需要明确：
- 全局角色与组织内角色的边界
- COUNSELOR（心理支持人员）应属于哪类角色
- ORG_ADMIN（组织管理员）应属于哪类角色

## 问题

早期讨论中曾出现角色模型的两种方案：

**方案 A（4 角色）**：
- STUDENT, TEACHER, ADMIN, SYSTEM_ADMIN
- 简单但覆盖不足

**方案 B（6 角色）**：
- STUDENT, TEACHER, COUNSELOR, ORG_ADMIN, SCHOOL_ADMIN, SYSTEM_ADMIN
- 覆盖所有场景，略有复杂度

## 决策

**采用方案 B（6 角色系统）**

### GlobalRole（全局角色）

用户在系统中的全局权限级别，一个用户只能有一个 GlobalRole。

| 角色 | 定位 | 权限范围 |
|------|------|---------|
| STUDENT | 基础用户 | 使用通讯、智能体、场景和个人记忆 |
| TEACHER | 教育者 | 创建课程组织、发布讨论、管理课程成员 |
| COUNSELOR | 支持人员 | 管理被授权的支持场景，不可读取默认私有数据 |
| ORG_ADMIN | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
| SCHOOL_ADMIN | 学校管理员 | 管理学校组织、账号、模型和节点 |
| SYSTEM_ADMIN | 系统管理员 | 系统配置、运维和安全审计 |

**关键决策**：
- **COUNSELOR 属于全局角色**：需要跨组织可见性以支持被授权的场景
- **ORG_ADMIN 属于全局角色**：管理权限需在组织创建时全局授予，便于审计
- **与 OrganizationRole 独立**：组织内角色（OWNER, ADMIN, MEMBER, GUEST）与全局角色并行

### OrganizationRole（组织内角色）

用户在特定组织内的权限级别，一个用户在同一组织内只能有一个 OrganizationRole。

| 角色 | 说明 |
|------|------|
| OWNER | 组织所有者，拥有全部权限 |
| ADMIN | 组织管理员，可管理成员和设置 |
| MEMBER | 普通成员，参与组织活动 |
| GUEST | 访客，仅可查看公开内容 |

## 后果

### 积极后果
- ✅ 权限边界清晰：全局 vs 组织内
- ✅ Counselor 可见性与隐私保护平衡：可管理授权场景，但不可读取默认私有数据
- ✅ 支持跨组织场景： Counselor 和 TEACHER 均可跨组织工作
- ✅ 审计友好：GlobalRole 变更全局可见

### 消极后果
- ⚠️ 角色数量增加：6 个全局角色比 4 角色略复杂
- ⚠️ 理解成本：需要理解双重角色体系（GlobalRole + OrganizationRole）

### 中立后果
- ORG_ADMIN 需全局授权：组织管理员权限在创建组织时授予，而非成员加入时
- COUNSELOR 需显式授权： Counselor 不能自动访问所有支持场景

## 权威文档

- **领域词汇表**：`docs/domain/DOMAIN_VOCABULARY.md` - 术语定义
- **权限矩阵**：`docs/architecture/PERMISSION_MATRIX.md` - 权限规则
- **API 合同**：`docs/api/API_CONTRACT.md` - 端点权限
- **数据清单**：`docs/architecture/DATA_INVENTORY.md` - 角色相关字段

## 枚举对照

| 全局角色 | 数据库值 | API 值 | 中文名 |
|---------|---------|--------|--------|
| STUDENT | student | STUDENT | 学生 |
| TEACHER | teacher | TEACHER | 教师 |
| COUNSELOR | counselor | COUNSELOR | 心理支持人员 |
| ORG_ADMIN | org_admin | ORG_ADMIN | 组织管理员 |
| SCHOOL_ADMIN | school_admin | SCHOOL_ADMIN | 校方管理员 |
| SYSTEM_ADMIN | system_admin | SYSTEM_ADMIN | 系统管理员 |

| 组织角色 | 数据库值 | API 值 | 中文名 |
|---------|---------|--------|--------|
| OWNER | owner | OWNER | 所有者 |
| ADMIN | admin | ADMIN | 管理员 |
| MEMBER | member | MEMBER | 成员 |
| GUEST | guest | GUEST | 访客 |

---

**更新记录**：
- 2026-07-14：ADR-006 正式采用，记录 R1-A 整改决策
