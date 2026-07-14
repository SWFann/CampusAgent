# CampusAgent 领域词汇表

> **版本**：v1.0  
> **基线日期**：2026-07-13  
> **维护者**：开发团队  
> **状态**：草稿，待团队评审

## 使用说明

本文档是 CampusAgent 项目的唯一权威术语来源。所有代码、API、文档和讨论应使用本文档定义的术语。

- **中英文对照**：每个术语提供中文名称、英文标识符
- **枚举值**：列出所有合法的枚举值
- **关系说明**：说明与其他实体的关联
- **索引链接**：可点击跳转到相关术语

---

## 📑 词汇索引

### 用户与身份
- [User（用户）](#user用户)
- [StudentProfile（学生档案）](#studentprofile学生档案)
- [GlobalRole（全局角色）](#globalrole全局角色)

### 组织
- [Organization（组织）](#organization组织)
- [OrganizationMembership（组织成员）](#organizationmembership组织成员)
- [OrganizationRole（组织角色）](#organizationrole组织角色)

### 通讯
- [Conversation（会话）](#conversation会话)
- [ConversationParticipant（会话参与者）](#conversationparticipant会话参与者)
- [Message（消息）](#message消息)

### 智能体
- [Agent（智能体）](#agent智能体)
- [AgentType（智能体类型）](#agenttype智能体类型)
- [AutonomyLevel（代理等级）](#autonomylevel代理等级)

### 记忆与授权
- [MemoryItem（记忆项）](#memoryitem记忆项)
- [ConsentRecord（授权记录）](#consentrecord授权记录)
- [MemoryCategory（记忆分类）](#memorycategory记忆分类)
- [SensitivityLevel（敏感级别）](#sensitivitylevel敏感级别)

### 场景
- [SceneDefinition（场景定义）](#scenedefinition场景定义)
- [SceneInstance（场景实例）](#sceneinstance场景实例)
- [SceneParticipant（场景参与者）](#sceneparticipant场景参与者)
- [PrivateSceneSubmission（私有场景提交）](#privatescenesubmission私有场景提交)
- [PreferenceCapsule（偏好胶囊）](#preferencecapsule偏好胶囊)

### 模型与节点
- [ModelProfile（模型配置）](#modelprofile模型配置)
- [EdgeNode（边缘节点）](#edgenode边缘节点)
- [ModelDeployment（模型部署）](#modeldeployment模型部署)

---

## 用户与身份

### User（用户）

**定义**：使用 CampusAgent 平台的账户主体，代表一个真实的人。

**字段**：
- `id` UUID - 主键
- `email` VARCHAR - 邮箱（唯一）
- `phone` VARCHAR - 手机号（可选）
- `password_hash` VARCHAR - 密码哈希
- `display_name` VARCHAR - 显示名称
- `avatar_url` VARCHAR - 头像URL（可选）
- `global_role` VARCHAR - 全局角色
- `status` VARCHAR - 账号状态
- `created_at` TIMESTAMP - 创建时间
- `updated_at` TIMESTAMP - 更新时间

**关联**：
- 一个 User 有且仅有一个 StudentProfile（学生档案）
- 一个 User 可以是多个 Organization 的成员
- 一个 User 可以拥有多个 Agent
- 一个 User 可以创建多个 SceneInstance

---

### StudentProfile（学生档案）

**定义**：用户的校园学生身份扩展信息。

**字段**：
- `id` UUID - 主键
- `user_id` UUID - 关联 User（唯一）
- `student_no` VARCHAR - 学号（唯一）
- `enrollment_year` INT - 入学年份
- `major_name` VARCHAR - 专业名称（可选）
- `bio` VARCHAR - 个人简介（可选）
- `profile_visibility` VARCHAR - 资料可见性

**关联**：
- 一对一关联 User
- 通过 OrganizationMembership 关联多个 Organization

---

### GlobalRole（全局角色）

**定义**：用户在系统中的全局权限级别。

**枚举值**：

| 值 | 中文名 | 说明 |
|----|--------|------|
| `STUDENT` | 学生 | 使用通讯、智能体、场景和个人记忆 |
| `TEACHER` | 教师 | 创建课程组织、发布讨论、管理课程成员 |
| `COUNSELOR` | 心理支持人员 | 管理被授权的支持场景，不可读取默认私有数据 |
| `ORG_ADMIN` | 组织管理员 | 管理班级、社团、宿舍等指定组织 |
| `SCHOOL_ADMIN` | 校方管理员 | 管理学校组织、账号、模型和节点 |
| `SYSTEM_ADMIN` | 系统管理员 | 系统配置、运维和安全审计 |

**关联**：
- 一个 User 只能有一个 GlobalRole
- 一个 User 可以有多个 OrganizationRole（不同组织内）

---

## 组织

### Organization（组织）

**定义**：校园中的组织单元，统一承载学校、学院、班级、宿舍、社团、课程等对象。

**字段**：
- `id` UUID - 主键
- `name` VARCHAR - 组织名称
- `type` VARCHAR - 组织类型
- `parent_id` UUID - 父组织ID（可选，支持树形结构）
- `owner_user_id` UUID - 所有者（可选）
- `description` TEXT - 描述（可选）
- `visibility` VARCHAR - 可见性
- `join_policy` VARCHAR - 加入策略
- `status` VARCHAR - 状态
- `metadata` JSONB - 元数据
- `created_at` TIMESTAMP - 创建时间
- `updated_at` TIMESTAMP - 更新时间

**枚举值**：

**type（组织类型）**：
- `SCHOOL` - 学校
- `COLLEGE` - 学院
- `CLASS` - 班级
- `DORM` - 宿舍
- `CLUB` - 社团
- `COURSE` - 课程

**visibility（可见性）**：
- `PUBLIC` - 公开可见
- `INTERNAL` - 内部可见
- `PRIVATE` - 私有

**join_policy（加入策略）**：
- `OPEN` - 开放加入
- `APPROVAL` - 需审批
- `INVITE_ONLY` - 仅邀请
- `CLOSED` - 关闭

**关联**：
- 可以嵌套（parent_id 自关联）
- 一个 Organization 有多个 OrganizationMembership
- 一个 Organization 可以有多个 Conversation

---

### OrganizationMembership（组织成员）

**定义**：用户与组织的关联关系，记录用户在组织中的角色和状态。

**字段**：
- `id` UUID - 主键
- `organization_id` UUID - 组织ID
- `user_id` UUID - 用户ID
- `role` VARCHAR - 组织内角色
- `status` VARCHAR - 成员状态
- `joined_at` TIMESTAMP - 加入时间

**唯一约束**：`UNIQUE(organization_id, user_id)`

**枚举值**：

**role（组织角色）**：
- `OWNER` - 所有者（只能有一个）
- `ADMIN` - 管理员
- `MEMBER` - 成员
- `GUEST` - 访客

**status（成员状态）**：
- `ACTIVE` - 有效
- `PENDING` - 待审批
- `SUSPENDED` - 暂停
- `LEFT` - 已退出

**关联**：
- 多对多关联 User 和 Organization
- 通过 SceneParticipant 关联 SceneInstance

---

### OrganizationRole（组织角色）

**定义**：用户在特定组织内的权限级别，与全局角色 GlobalRole 独立。

**说明**：一个学生可以是全局 `STUDENT`，同时是某社团的 `OWNER`、某课程的 `MEMBER`。

**详见**：[OrganizationMembership](#organizationmembership组织成员)

---

## 通讯

### Conversation（会话）

**定义**：通讯的基本单元，可以是私聊、群聊、组织群聊或场景会话。

**字段**：
- `id` UUID - 主键
- `type` VARCHAR - 会话类型
- `title` VARCHAR - 标题（可选）
- `avatar_url` VARCHAR - 头像URL（可选）
- `owner_user_id` UUID - 创建者（可选）
- `organization_id` UUID - 关联组织（可选）
- `scene_instance_id` UUID - 关联场景实例（可选）
- `privacy_level` VARCHAR - 隐私级别
- `status` VARCHAR - 状态
- `created_at` TIMESTAMP - 创建时间
- `updated_at` TIMESTAMP - 更新时间

**枚举值**：

**type（会话类型）**：
- `DM` - 私聊
- `GROUP` - 普通群聊
- `ORG_GROUP` - 组织群聊
- `SCENE` - 场景会话

**privacy_level（隐私级别）**：
- `PUBLIC` - 公开
- `INTERNAL` - 内部
- `PRIVATE` - 私有
- `SCENE` - 场景（特殊隐私保护）

**关联**：
- 一个 Conversation 有多个 ConversationParticipant
- 一个 Conversation 有多个 Message
- 一个 Conversation 可以关联一个 SceneInstance
- 一个 Organization 可以有多个 Conversation

---

### ConversationParticipant（会话参与者）

**定义**：用户或智能体在会话中的参与身份。

**字段**：
- `id` UUID - 主键
- `conversation_id` UUID - 会话ID
- `participant_type` VARCHAR - 参与者类型
- `user_id` UUID - 用户ID（可选）
- `agent_id` UUID - 智能体ID（可选）
- `role` VARCHAR - 角色
- `joined_at` TIMESTAMP - 加入时间
- `muted` BOOLEAN - 是否静音

**唯一约束**：`UNIQUE(conversation_id, participant_type, user_id, agent_id)`

**枚举值**：

**participant_type（参与者类型）**：
- `USER` - 用户
- `AGENT` - 智能体

**role（角色）**：
- `OWNER` - 群主
- `ADMIN` - 管理员
- `MEMBER` - 成员

**关联**：
- 属于一个 Conversation
- 关联一个 User 或一个 Agent

---

### Message（消息）

**定义**：会话中的单条消息记录，严禁用于保存用户私有偏好。

**字段**：
- `id` UUID - 主键
- `conversation_id` UUID - 会话ID
- `sender_type` VARCHAR - 发送者类型
- `sender_user_id` UUID - 发送用户ID（可选）
- `sender_agent_id` UUID - 发送智能体ID（可选）
- `message_type` VARCHAR - 消息类型
- `content` TEXT - 消息内容（可选）
- `structured_payload` JSONB - 结构化载荷（可选）
- `visibility` VARCHAR - 可见性
- `reply_to_id` UUID - 回复消息ID（可选）
- `created_at` TIMESTAMP - 创建时间
- `deleted_at` TIMESTAMP - 删除时间（软删除）

**枚举值**：

**sender_type（发送者类型）**：
- `USER` - 用户
- `AGENT` - 智能体
- `SYSTEM` - 系统

**message_type（消息类型）**：
- `TEXT` - 文本消息
- `IMAGE` - 图片
- `FILE` - 文件
- `SYSTEM` - 系统消息
- `AGENT_PUBLIC` - 智能体公开消息
- `SCENE_CARD` - 场景卡片
- `VOTE` - 投票
- `PROPOSAL` - 提案
- `RESULT` - 结果
- `PRIVACY_NOTICE` - 隐私说明

**隐私约束**：
- ❌ 禁止通过普通消息接口保存用户私有偏好
- ✅ 私有偏好必须使用 Scene API

**关联**：
- 属于一个 Conversation
- 属于一个 ConversationParticipant

---

## 智能体

### Agent（智能体）

**定义**：代表用户或组织执行任务的 AI 代理实体，是用户可控的数字助手。

**字段**：
- `id` UUID - 主键
- `owner_user_id` UUID - 所有者用户ID（可选，组织智能体可为空）
- `organization_id` UUID - 所属组织ID（可选）
- `name` VARCHAR - 智能体名称
- `type` VARCHAR - 智能体类型
- `avatar_url` VARCHAR - 头像URL（可选）
- `autonomy_level` VARCHAR - 代理等级
- `model_profile_id` UUID - 模型配置ID
- `status` VARCHAR - 状态
- `public_persona` JSONB - 公开人格设定
- `private_config_encrypted` BYTEA - 加密私有配置
- `created_at` TIMESTAMP - 创建时间
- `updated_at` TIMESTAMP - 更新时间

**枚举值**：

**type（智能体类型）**：
- `PERSONAL` - 个人智能体
- `ORGANIZATION` - 组织智能体
- `COURSE` - 课程智能体
- `FACILITATOR` - 协调智能体
- `WELLBEING_SUPPORT` - 心理支持智能体
- `SYSTEM` - 系统智能体

**status（状态）**：
- `ACTIVE` - 活跃
- `INACTIVE` - 非活跃
- `SUSPENDED` - 暂停

**关联**：
- 属于一个 User（PERSONAL 类型）
- 属于一个 Organization（ORGANIZATION 类型）
- 有一个 ModelProfile
- 通过 AgentRun 记录执行历史

---

### AgentType（智能体类型）

**定义**：智能体的分类，决定了其功能范围和使用场景。

**详细说明**：[Agent.type](#agent智能体)

---

### AutonomyLevel（代理等级）

**定义**：智能体在特定场景中可以代替用户做决策的权限级别。

**枚举值**：

| 值 | 中文名 | 能力 | MVP使用 |
|----|--------|------|---------|
| `L0` | 只读辅助 | 只能在私聊中回答用户 | ❌ |
| `L1` | 建议 | 可根据记忆给用户建议 | ✅ 默认 |
| `L2` | 受限代言 | 可在指定场景中提交结构化偏好或评分 | ✅ 聚餐最高授权 |
| `L3` | 受限决策 | 可在明确规则下自动投票 | ❌ |
| `L4` | 受限执行 | 可执行报名等操作 | ❌ MVP不开放 |

**说明**：
- 默认等级：`L1`
- 聚餐场景最高授权：`L2`
- 用户必须按场景单独授权 L2
- 最终投票、支付、报名必须由用户确认

---

## 记忆与授权

### MemoryItem（记忆项）

**定义**：智能体或用户的记忆存储，记录偏好、经验和知识。

**字段**：
- `id` UUID - 主键
- `owner_user_id` UUID - 所有者用户ID
- `agent_id` UUID - 关联智能体ID（可选）
- `category` VARCHAR - 记忆分类
- `content_encrypted` BYTEA - 加密的内容
- `content_embedding` VECTOR - 向量嵌入（可选，用于语义检索）
- `sensitivity_level` VARCHAR - 敏感级别
- `visibility` VARCHAR - 可见性
- `source` VARCHAR - 来源
- `confidence` FLOAT - 置信度
- `expires_at` TIMESTAMP - 过期时间（可选）
- `created_at` TIMESTAMP - 创建时间
- `updated_at` TIMESTAMP - 更新时间
- `deleted_at` TIMESTAMP - 删除时间（软删除）

**隐私约束**：
- 内容必须加密存储
- 必须通过 MemoryService 访问，不能直接查询
- 读取需要有效的 ConsentRecord

**关联**：
- 属于一个 User
- 可以关联一个 Agent

---

### ConsentRecord（授权记录）

**定义**：记录用户对特定资源在特定目的下的授权状态。

**字段**：
- `id` UUID - 主键
- `user_id` UUID - 被授权用户ID
- `resource_type` VARCHAR - 资源类型
- `resource_id` UUID - 资源ID（可选）
- `purpose` VARCHAR - 授权目的
- `scope` JSONB - 授权范围
- `granted` BOOLEAN - 是否已授权
- `expires_at` TIMESTAMP - 过期时间（可选）
- `created_at` TIMESTAMP - 创建时间
- `revoked_at` TIMESTAMP - 撤销时间（可选）

**隐私约束**：
- 所有敏感访问必须同时明确：who、what、purpose、scope、expiration、consent
- 撤销后新请求立即失效
- 不能用一次全局授权覆盖所有未来场景

**关联**：
- 关联一个 User
- 关联一个 Resource（如 SceneInstance）

---

### MemoryCategory（记忆分类）

**定义**：记忆项的内容分类，用于访问控制和检索。

**枚举值**：

| 值 | 说明 | 示例 |
|----|------|------|
| `FOOD_PREFERENCE` | 饮食偏好 | 喜欢日料、不吃香菜 |
| `BUDGET_PREFERENCE` | 预算偏好 | 聚餐预算上限 |
| `ACTIVITY_PREFERENCE` | 活动偏好 | 喜欢安静环境 |
| `TIME_AVAILABILITY` | 时间可用性 | 周三下午有空 |
| `SOCIAL_PREFERENCE` | 社交偏好 | 偏好小团体 |
| `WELLBEING_STATE` | 心理状态 | 最近压力较大 |

---

### SensitivityLevel（敏感级别）

**定义**：记忆内容的敏感程度，决定访问控制和加密强度。

**枚举值**：

| 值 | 中文名 | 访问控制 | 加密要求 |
|----|--------|---------|---------|
| `P0_PUBLIC` | 公开 | 无限制 | 普通存储 |
| `P1_INTERNAL` | 内部 | 组织可见性控制 | 普通存储 |
| `P2_PRIVATE` | 私有 | 逐目的授权 + 审计 | 应用层加密 |
| `P3_SENSITIVE` | 高敏感 | 强隔离 + 最小访问 | 强加密 |
| `P4_TEMPORARY` | 临时秘密 | TTL + 自动销毁 | 临时加密 |

**对应数据分类**：[PRIVACY_BASELINE.md](../privacy/PRIVACY_BASELINE.md)

---

## 场景

### SceneDefinition（场景定义）

**定义**：场景的元数据定义，描述场景的类型、输入输出、权限要求和数据保留策略。

**字段**：
- `id` UUID - 主键
- `scene_key` VARCHAR - 场景唯一标识（唯一）
- `name` VARCHAR - 场景名称
- `version` VARCHAR - 版本号
- `description` TEXT - 描述
- `input_schema` JSONB - 输入JSON Schema
- `output_schema` JSONB - 输出JSON Schema
- `required_permissions` JSONB - 所需权限
- `data_retention_policy` JSONB - 数据保留策略
- `enabled` BOOLEAN - 是否启用
- `created_at` TIMESTAMP - 创建时间

**枚举值**：

**scene_key（场景标识）**：
- `meal_planning` - 宿舍聚餐协商
- `class_discussion` - 课堂讨论
- `club_planning` - 社团活动策划
- `study_group` - 学习小组匹配
- `freshman_helper` - 新生校园助手
- `emotion_journal` - 情绪记录

**关联**：
- 一个 SceneDefinition 可以有多个 SceneInstance

---

### SceneInstance（场景实例）

**定义**：场景的运行时实例，记录一次具体场景的执行状态和上下文。

**字段**：
- `id` UUID - 主键
- `scene_definition_id` UUID - 场景定义ID
- `conversation_id` UUID - 关联会话ID（可选）
- `creator_user_id` UUID - 创建者用户ID
- `status` VARCHAR - 场景状态
- `current_stage` VARCHAR - 当前阶段
- `public_context` JSONB - 公开上下文
- `expires_at` TIMESTAMP - 过期时间（可选）
- `created_at` TIMESTAMP - 创建时间
- `updated_at` TIMESTAMP - 更新时间

**枚举值**：

**status（场景状态）**：
- `ACTIVE` - 活跃
- `COMPLETED` - 已完成
- `CANCELLED` - 已取消
- `FAILED` - 失败
- `EXPIRED` - 已过期

**current_stage（当前阶段）**：
- `DRAFT` - 草稿
- `WAITING_FOR_PARTICIPANTS` - 等待参与者
- `WAITING_FOR_CONSENT` - 等待授权
- `WAITING_FOR_PRIVATE_INPUT` - 等待私有输入
- `PROCESSING` - 处理中
- `CANDIDATES_READY` - 候选就绪
- `VOTING` - 投票中
- `CONFIRMING` - 确认中
- `COMPLETED` - 已完成

**关联**：
- 属于一个 SceneDefinition
- 可以关联一个 Conversation
- 有多个 SceneParticipant
- 有多个 PrivateSceneSubmission
- 有多个 SceneCandidate
- 有一个 SceneResult

---

### SceneParticipant（场景参与者）

**定义**：用户或智能体在场景实例中的参与记录。

**字段**：
- `id` UUID - 主键
- `scene_instance_id` UUID - 场景实例ID
- `user_id` UUID - 用户ID
- `agent_id` UUID - 智能体ID
- `consent_record_id` UUID - 授权记录ID
- `submission_status` VARCHAR - 提交状态
- `created_at` TIMESTAMP - 创建时间

**唯一约束**：`UNIQUE(scene_instance_id, user_id)`

**枚举值**：

**submission_status（提交状态）**：
- `INVITED` - 已邀请
- `ACCEPTED` - 已接受
- `REJECTED` - 已拒绝
- `SUBMITTED` - 已提交
- `DECLINED` - 已退出

**关联**：
- 属于一个 SceneInstance
- 关联一个 User 和一个 Agent
- 关联一个 ConsentRecord
- 通过 PrivateSceneSubmission 记录私有提交

---

### PrivateSceneSubmission（私有场景提交）

**定义**：用户在场景中的私有提交，与普通消息严格隔离，用于存储敏感偏好。

**字段**：
- `id` UUID - 主键
- `scene_instance_id` UUID - 场景实例ID
- `participant_id` UUID - 参与者ID
- `encrypted_payload` BYTEA - 加密的原始提交内容
- `capsule_payload` JSONB - 最小化胶囊（可选）
- `expires_at` TIMESTAMP - 过期时间
- `created_at` TIMESTAMP - 创建时间
- `deleted_at` TIMESTAMP - 删除时间（软删除）

**隐私约束**：
- 原始内容必须加密存储
- 不得进入普通消息表
- 场景结束后必须清理（最长24小时）
- 胶囊只包含最小化结构化约束

**关联**：
- 属于一个 SceneInstance
- 属于一个 SceneParticipant

---

### PreferenceCapsule（偏好胶囊）

**定义**：个人智能体从原始私有提交中抽取的最小化结构化约束，用于协调层评价候选方案。

**字段**（JSONB 格式）：

```json
{
  "scene_type": "meal_planning",
  "hard_constraints": [
    {
      "type": "budget_max",
      "value": 100
    },
    {
      "type": "exclude_ingredient",
      "value": "香菜"
    }
  ],
  "soft_preferences": [
    {
      "type": "cuisine",
      "value": "日料",
      "weight": 0.8
    },
    {
      "type": "environment",
      "value": "quiet",
      "weight": 0.6
    }
  ],
  "availability": {
    "start": "18:30",
    "end": "21:00"
  },
  "disclosure_policy": {
    "allow_raw_preference": false,
    "allow_constraint_category": true,
    "allow_aggregated_reason": true
  }
}
```

**设计原则**：
- ✅ 原始自由文本只留在个人私有域
- ✅ 协调层只接收经过规则过滤的结构化胶囊
- ✅ 胶囊中的约束也不直接展示给其他成员
- ✅ 预算等信息转为区间或布尔约束

---

## 模型与节点

### ModelProfile（模型配置）

**定义**：逻辑模型的配置定义，不直接关联具体模型节点。

**字段**：
- `id` UUID - 主键
- `logical_name` VARCHAR - 逻辑名称（唯一）
- `provider_type` VARCHAR - 提供者类型
- `capability` VARCHAR - 能力描述
- `default_parameters` JSONB - 默认参数
- `privacy_level` VARCHAR - 隐私级别
- `enabled` BOOLEAN - 是否启用

**枚举值**：

**provider_type（提供者类型）**：
- `LOCAL` - 本地模型
- `CLOUD` - 云端模型
- `MOCK` - 模拟模型

**关联**：
- 一个 ModelProfile 可以有多个 ModelDeployment

---

### EdgeNode（边缘节点）

**定义**：部署在校园内的计算节点，用于运行本地模型。

**字段**：
- `id` UUID - 主键
- `name` VARCHAR - 节点名称
- `endpoint` VARCHAR - 端点地址
- `auth_secret_encrypted` BYTEA - 加密的认证密钥
- `status` VARCHAR - 状态
- `cpu_info` JSONB - CPU信息
- `gpu_info` JSONB - GPU信息（可选）
- `memory_total_mb` INT - 总内存（MB）
- `last_heartbeat_at` TIMESTAMP - 最后心跳时间
- `created_at` TIMESTAMP - 创建时间

**枚举值**：

**status（状态）**：
- `ONLINE` - 在线
- `OFFLINE` - 离线
- `DEGRADED` - 降级
- `MAINTENANCE` - 维护中

**关联**：
- 一个 EdgeNode 可以有多个 ModelDeployment

---

### ModelDeployment（模型部署）

**定义**：模型在具体节点上的部署实例。

**字段**：
- `id` UUID - 主键
- `node_id` UUID - 节点ID
- `model_profile_id` UUID - 模型配置ID
- `actual_model_name` VARCHAR - 实际模型名称
- `endpoint_path` VARCHAR - 端点路径
- `max_concurrency` INT - 最大并发数
- `status` VARCHAR - 状态
- `created_at` TIMESTAMP - 创建时间

**枚举值**：

**status（状态）**：
- `RUNNING` - 运行中
- `STOPPED` - 已停止
- `ERROR` - 错误

**关联**：
- 关联一个 EdgeNode
- 关联一个 ModelProfile

---

## 附录

### A. 相关文档

- [完整项目计划书](../product/CampusAgent_Project_Plan.md)
- [架构与模块边界](../architecture/MODULE_BOUNDARIES.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)
- [开发计划表](../development/DEVELOPMENT_PLAN.md)

### B. 词汇变更历史

| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-13 | 初始版本 | - |

### C. 待讨论问题

- [ ] "Consent" 是否统一翻译为"授权"？（当前：是）
- [ ] "Capsule" 是否统一翻译为"胶囊"？（当前：是）
- [ ] 需要补充更多业务领域的术语吗？

---

**下一步**：团队评审确认后，进入 P0-02（冻结MVP/非MVP）
