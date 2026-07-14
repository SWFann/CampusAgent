---
task_id: P0-04
status: completed
stage: P0
title: 建立角色权限矩阵
started_at: 2026-07-14T01:15:00+09:00
completed_at: 2026-07-14T02:15:00+09:00
estimated_hours: 2.5
actual_hours: 1.0
---

# P0-04：建立角色权限矩阵

## 目标

建立全局角色、组织角色、资源动作、默认拒绝规则的完整权限矩阵。

**来自开发计划**：P0-04 - 建立角色权限矩阵

**产物**：角色-资源-动作矩阵、默认拒绝规则、权限服务设计说明

**依赖**：P0-01（领域词汇表 ✅）、P0-02（MVP范围 ✅）

## 验收标准

- [x] 列出所有全局角色及其权限
- [x] 列出所有组织角色及其权限
- [x] 列出所有资源类型
- [x] 列出所有动作类型
- [x] 建立完整的角色-资源-动作矩阵
- [x] 定义默认拒绝规则
- [x] 定义权限检查流程
- [x] 文档已提交

## 实现过程

### 2026-07-14 01:15 - 02:15

基于文档：
- DOMAIN_VOCABULARY.md（P0-01产出）
- MVP_SCOPE.md（P0-02产出）
- PRIVACY_BASELINE.md
- PROJECT_OVERVIEW.md

### 权限模型设计

#### 全局角色（6个）
STUDENT, TEACHER, COUNSELOR, ORG_ADMIN, SCHOOL_ADMIN, SYSTEM_ADMIN

#### 组织角色（4个）
OWNER, ADMIN, MEMBER, GUEST

#### 资源类型（12个）
user, agent, memory, organization, conversation, message, scene,
private_submission, consent, node, model, audit

#### 动作类型（9个）
create, read, update, delete, list, search, execute, manage, admin

### 核心权限设计

#### 私有提交访问（核心隐私控制）
- 只有提交者可读取自己的私有提交
- **所有管理角色均无权限**
- 这是隐私控制的基石

#### 记忆访问
- 通过 MemoryService 四重检查：owner + purpose + category + consent
- 任何角色不能绕过 MemoryService

#### 审计日志
- 结构化元数据，无敏感内容
- 所有角色只能查看自己相关的记录（或脱敏记录）

## 修改的文件

### 新增文件
- `docs/architecture/PERMISSION_MATRIX.md` - 角色权限矩阵主文档（6,500+字）

### 修改文件
- （暂无）

### 删除文件
- （无）

## 测试结果

- ✅ 权限矩阵完整性检查：通过
- ✅ 隐私控制点覆盖率检查：通过
- ✅ 默认拒绝规则一致性检查：通过
- ✅ 测试用例覆盖度检查：通过（17个测试用例）

## 问题与解决

| 问题 | 解决方案 | 耗时 |
|------|---------|------|
| COUNSELOR权限边界 | 独立域，默认无权限，需额外授权 | 20分钟 |
| SYSTEM_ADMIN是否完全控制 | 否，即使SYSTEM_ADMIN也不能读取P2/P3正文 | 15分钟 |
| 最后一个OWNER如何保护 | 必须转让所有权或删除组织，不能直接退出 | 10分钟 |

## 关键决策

### 决策1：私有提交访问控制

**决定**：只有提交者本人可读取，所有管理角色均无权限
**理由**：这是隐私控制的基石，不能妥协

### 决策2：默认拒绝原则

**决定**：所有访问默认拒绝，必须明确授权
**理由**：安全基线，防止越权

### 决策3：记忆访问四重检查

**决定**：owner + purpose + category + consent 全部匹配
**理由**：确保每次访问都有明确目的和授权

### 决策4：审计日志脱敏

**决定**：只记录结构化元数据，不记录敏感内容
**理由**：审计目的是追踪访问，不是存储敏感内容

## 下一步

- **依赖任务**：P0-05（建立数据清单）、P0-09（草拟HTTP契约）、P0-11（隐私测试矩阵）
- **注意事项**：
  - 权限矩阵是API设计和测试设计的基础
  - P0-11的隐私测试矩阵将基于本矩阵生成

## 提交信息

- Commit: `docs(architecture): establish permission matrix`
- PR: （待创建）
