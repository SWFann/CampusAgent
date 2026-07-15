---
task_id: P0-01
status: completed
stage: P0
title: 建立领域词汇表
started_at: 2026-07-13T22:00:00+09:00
completed_at: 2026-07-13T23:30:00+09:00
estimated_hours: 3
actual_hours: 1.5
---

# P0-01：建立领域词汇表

## 目标

为 CampusAgent 项目建立统一的中英文领域词汇表，确保团队对核心概念有一致的理解。

**来自开发计划**：P0-01 - 建立领域词汇表

**产物**：User、Agent、Organization、Conversation、Scene、Memory、Consent 等定义及中英文枚举

**依赖**：无（P0阶段第一个任务）

## 验收标准

- [x] 完成核心实体词汇定义
- [x] 完成中英文对照
- [x] 完成枚举值规范
- [x] 完成关系说明
- [x] 所有术语可通过链接索引
- [x] 文档已提交到版本控制
- [ ] 文档已团队评审（待进行，非阻塞）

## 实现过程

### 2026-07-13 22:00-23:00

1. 阅读完整项目计划书和架构文档
2. 提取核心实体和概念
3. 设计词汇表结构

### 识别的核心实体

从项目计划书中提取到以下核心实体：

**用户与身份**：
- User（用户）
- StudentProfile（学生档案）
- GlobalRole（全局角色）

**组织**：
- Organization（组织）
- OrganizationMembership（组织成员）
- OrganizationRole（组织角色）

**通讯**：
- Conversation（会话）
- ConversationParticipant（会话参与者）
- Message（消息）

**智能体**：
- Agent（智能体）
- AgentType（智能体类型）
- AutonomyLevel（代理等级）

**记忆与授权**：
- MemoryItem（记忆项）
- ConsentRecord（授权记录）
- MemoryCategory（记忆分类）
- SensitivityLevel（敏感级别）

**场景**：
- SceneDefinition（场景定义）
- SceneInstance（场景实例）
- SceneParticipant（场景参与者）
- PrivateSceneSubmission（私有场景提交）
- PreferenceCapsule（偏好胶囊）

**模型与节点**：
- ModelProfile（模型配置）
- EdgeNode（边缘节点）
- ModelDeployment（模型部署）

## 修改的文件

### 新增文件
- `docs/domain/DOMAIN_VOCABULARY.md` - 领域词汇表主文档
- `docs/domain/README.md` - 词汇表导航

### 修改文件
- （暂无）

### 删除文件
- （无）

## 测试结果

- ✅ 术语一致性检查：通过
- ✅ 中英文对照完整性：通过
- ✅ 枚举值准确性：通过
- ✅ 链接可访问性：通过
- ⏳ 团队评审：待进行（非阻塞）

## 问题与解决

| 问题 | 解决方案 | 耗时 |
|------|---------|------|
| 部分概念在文档中有多种表述（如"场景实例"与"场景"） | 统一为 SceneDefinition（定义）/SceneInstance（实例）的区分 | 15分钟 |
| "Consent" 翻译选择：授权/同意/许可 | 统一使用"授权"，ConsentRecord = 授权记录 | 10分钟 |

## 下一步

- **依赖任务**：P0-02（冻结MVP/非MVP，需要使用词汇表）
- **注意事项**：
  - 词汇表需要团队评审确认
  - P0-12创建ADR时会引用本词汇表

## 提交信息

- Commit: `docs(domain): establish domain vocabulary`
- PR: （待创建，词汇表建立后可创建PR供团队评审）
- 评审人：（待分配）
- 状态：草稿，待团队评审
