---
task_id: R1-01
status: completed
stage: R1
title: 识别角色不一致
completed_at: 2026-07-14T12:37:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# R1-01：识别角色不一致

## 完成状态

✅ **角色不一致已识别并决策**

**完成时间**：2026-07-14T12:37:00+09:00

## 扫描范围

按照整改计划要求，检查以下文档中的角色定义：
- `docs/domain/DOMAIN_VOCABULARY.md` - 领域词汇表（权威源）
- `docs/architecture/PERMISSION_MATRIX.md` - 权限矩阵
- `docs/api/API_CONTRACT.md` - API 合同
- `docs/product/MVP_SCOPE.md` - MVP 范围
- `docs/product/CampusAgent_Project_Plan.md` - 项目计划

## 发现的不一致

### 1. ✅ 无 4-role vs 6-role 冲突

**当前状态**：
- 所有文档统一使用 **6 个全局角色**（GlobalRole）
- 权威源：`DOMAIN_VOCABULARY.md` 定义 6 角色

**GlobalRole 枚举（已统一）**：
```python
STUDENT        # 学生
TEACHER        # 教师
COUNSELOR      # 心理支持人员
ORG_ADMIN      # 组织管理员
SCHOOL_ADMIN   # 校方管理员
SYSTEM_ADMIN   # 系统管理员
```

**结论**：无需在 4-role 和 6-role 之间做选择，当前已统一为 6-role 系统 ✅

### 2. ⚠️ 发现命名不一致

**问题**：`CampusAgent_Project_Plan.md` 中使用 `OrganizationAdmin` 而非标准 `ORG_ADMIN`

**位置**：
- `docs/product/CampusAgent_Project_Plan.md:285`

**当前写法**：
```markdown
| OrganizationAdmin | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
```

**标准写法**（DOMAIN_VOCABULARY.md 和 PERMISSION_MATRIX.md）：
```markdown
| ORG_ADMIN | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
```

**影响范围**：
- 仅 1 处不一致（在旧版项目计划文档中）
- 其他所有 P0 文档（词汇表、权限矩阵、API 合同）均使用 `ORG_ADMIN` ✅

**修复优先级**：低（项目计划为非权威文档，不影响代码和 P0 契约）

## 决策

### D-001：确认 GlobalRole 权威枚举

**决策**：采用 6-role 系统（STUDENT, TEACHER, COUNSELOR, ORG_ADMIN, SCHOOL_ADMIN, SYSTEM_ADMIN）

**理由**：
1. DOMAIN_VOCABULARY.md 已明确 6 角色定义
2. PERMISSION_MATRIX.md 已为 6 角色建立详细权限规则
3. API_CONTRACT.md 已基于 6 角色定义端点权限
4. 6 角色覆盖所有必需场景，无需进一步拆分

**COUNSELOR 角色定位**：
- 属于 **全局角色**（GlobalRole），而非组织授权能力
- 全局可见但权限受限：可管理被授权的支持场景，不可读取默认私有数据
- 有 ADR-003 支持：独立于 OrganizationRole 的全局权限

**ORG_ADMIN 角色定位**：
- 属于 **全局角色**（GlobalRole），而非组织授权能力
- 管理指定组织（班级、社团、宿舍等），权限范围限于所管理的组织
- 与 OrganizationRole（组织内角色）并行，互不冲突

### D-002：COUNSELOR 和 ORG_ADMIN 均为全局角色

**决策**：两者均为 GlobalRole 枚举成员，不属于 OrganizationRole

**理由**：
- Counselor 需要跨组织可见性（支持场景可能跨多个组织）
- ORG_ADMIN 需要全局识别（管理权限需在组织创建时授予）
- 与 OrganizationRole（OWNER, ADMIN, MEMBER, GUEST）明确区分

## 验证结果

- [x] 扫描所有 P0 文档中的角色定义
- [x] 确认 6-role 系统已统一
- [x] 识别 1 处命名不一致（OrganizationAdmin → ORG_ADMIN）
- [x] 确认 COUNSELOR 和 ORG_ADMIN 均为全局角色
- [x] 决策已记录（D-001 和 D-002）

## 下一步

- **R1-02**：记录角色变更 ADR（确认 D-001 和 D-002）
- **R1-03**：同步角色文档（修复 CampusAgent_Project_Plan.md 中的命名不一致）

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
