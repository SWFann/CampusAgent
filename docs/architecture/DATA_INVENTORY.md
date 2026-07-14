# 数据清单

> **版本**：v1.0  
> **基线日期**：2026-07-14  
> **状态**：已冻结，变更需 ADR  
> **维护者**：开发团队

## 1. 概述

本文档列出 CampusAgent 系统的所有实体、字段、数据分类、所有者、用途和保留期限。

**数据分类**：
- **P0 公开**：可公开访问，无敏感信息
- **P1 内部**：组织内部可见，需要访问控制
- **P2 私有**：用户私有，需要加密和授权
- **P3 高敏感**：极度敏感，强隔离和最小访问
- **P4 临时秘密**：临时存储，自动销毁

**保留策略**：
- **永久**：核心业务数据（如用户账号）
- **场景结束**：与场景相关的临时数据
- **24小时**：临时加密数据的最大保留时间
- **30天**：Agent 执行元数据
- **90天**：审计日志
- **用户控制**：长期记忆由用户主动确认后保留

---

## 2. 用户与身份

### 2.1 User（用户）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `email` | VARCHAR | P1 | 用户 | 登录、通知 | 永久 | 唯一 |
| `phone` | VARCHAR | P1 | 用户 | 登录、通知 | 永久 | 可选 |
| `password_hash` | VARCHAR | P2 | 用户 | 身份验证 | 永久 | 强哈希 |
| `display_name` | VARCHAR | P1 | 用户 | 显示 | 永久 | |
| `avatar_url` | VARCHAR | P0 | 用户 | 显示 | 永久 | 可选 |
| `global_role` | VARCHAR | P1 | 系统 | 权限控制 | 永久 | |
| `status` | VARCHAR | P1 | 系统 | 账号状态 | 永久 | 活跃/禁用/删除 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**加密要求**：密码使用 bcrypt/argon2 强哈希

**删除策略**：软删除（deleted_at），账号注销后保留30天

---

### 2.2 StudentProfile（学生档案）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `user_id` | UUID | P1 | 用户 | 关联用户 | 永久 | 唯一 |
| `student_no` | VARCHAR | P1 | 用户 | 学籍 | 永久 | 唯一 |
| `enrollment_year` | INT | P1 | 用户 | 年级 | 永久 | |
| `major_name` | VARCHAR | P1 | 用户 | 专业 | 永久 | 可选 |
| `bio` | VARCHAR | P1 | 用户 | 简介 | 永久 | 可选，用户可控 |
| `profile_visibility` | VARCHAR | P1 | 用户 | 可见性控制 | 永久 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**隐私控制**：用户可控制 profile_visibility

---

## 3. 组织

### 3.1 Organization（组织）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `name` | VARCHAR | P0/P1 | 所有者 | 组织名 | 永久 | 根据类型决定公开性 |
| `type` | VARCHAR | P0 | 系统 | 组织类型 | 永久 | 学校/学院/班级/宿舍/社团/课程 |
| `parent_id` | UUID | P1 | 系统 | 树形结构 | 永久 | 可选 |
| `owner_user_id` | UUID | P1 | 所有者 | 所有者 | 永久 | |
| `description` | TEXT | P0/P1 | 所有者 | 描述 | 永久 | 根据类型 |
| `visibility` | VARCHAR | P1 | 所有者 | 可见性 | 永久 | 公开/内部/私有 |
| `join_policy` | VARCHAR | P1 | 所有者 | 加入策略 | 永久 | 开放/审批/邀请/关闭 |
| `status` | VARCHAR | P1 | 系统 | 状态 | 永久 | 活跃/归档/删除 |
| `metadata` | JSONB | P1 | 所有者 | 扩展信息 | 永久 | 可选 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**删除策略**：软删除或归档，不物理删除历史消息

---

### 3.2 OrganizationMembership（组织成员）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `organization_id` | UUID | P1 | 系统 | 组织ID | 永久 | |
| `user_id` | UUID | P1 | 用户 | 用户ID | 永久 | |
| `role` | VARCHAR | P1 | 所有者 | 角色 | 永久 | OWNER/ADMIN/MEMBER/GUEST |
| `status` | VARCHAR | P1 | 系统 | 成员状态 | 永久 | 活跃/待审批/暂停/已退出 |
| `joined_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**唯一约束**：UNIQUE(organization_id, user_id)

---

## 4. 通讯

### 4.1 Conversation（会话）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `type` | VARCHAR | P1 | 创建者 | 会话类型 | 永久 | 私聊/群聊/组织群聊/场景 |
| `title` | VARCHAR | P0/P1 | 创建者 | 标题 | 永久 | 可选 |
| `avatar_url` | VARCHAR | P0 | 创建者 | 头像 | 永久 | 可选 |
| `owner_user_id` | UUID | P1 | 创建者 | 群主 | 永久 | 群聊才有 |
| `organization_id` | UUID | P1 | 系统 | 关联组织 | 永久 | 可选 |
| `scene_instance_id` | UUID | P1 | 系统 | 关联场景 | 永久 | 可选 |
| `privacy_level` | VARCHAR | P1 | 创建者 | 隐私级别 | 永久 | |
| `status` | VARCHAR | P1 | 系统 | 状态 | 永久 | 活跃/归档/删除 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

---

### 4.2 ConversationParticipant（会话参与者）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `conversation_id` | UUID | P1 | 系统 | 会话ID | 永久 | |
| `participant_type` | VARCHAR | P1 | 系统 | 参与者类型 | 永久 | 用户/智能体 |
| `user_id` | UUID | P1 | 系统 | 用户ID | 永久 | 可选 |
| `agent_id` | UUID | P1 | 系统 | 智能体ID | 永久 | 可选 |
| `role` | VARCHAR | P1 | 系统 | 角色 | 永久 | OWNER/ADMIN/MEMBER |
| `joined_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |
| `muted` | BOOLEAN | P1 | 用户 | 是否静音 | 永久 | 用户自己 |

**唯一约束**：UNIQUE(conversation_id, participant_type, user_id, agent_id)

---

### 4.3 Message（消息）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `conversation_id` | UUID | P1 | 系统 | 会话ID | 永久 | |
| `sender_type` | VARCHAR | P1 | 系统 | 发送者类型 | 永久 | |
| `sender_user_id` | UUID | P1 | 系统 | 发送用户 | 永久 | 可选 |
| `sender_agent_id` | UUID | P1 | 系统 | 发送智能体 | 永久 | 可选 |
| `message_type` | VARCHAR | P1 | 系统 | 消息类型 | 永久 | 文本/系统/场景卡等 |
| `content` | TEXT | P1/P2 | 发送者 | 消息内容 | 永久 | 不含私有偏好 |
| `structured_payload` | JSONB | P1 | 系统 | 结构化载荷 | 永久 | 可选 |
| `visibility` | VARCHAR | P1 | 发送者 | 可见性 | 永久 | |
| `reply_to_id` | UUID | P1 | 系统 | 回复消息 | 永久 | 可选 |
| `created_at` | TIMESTAMP | P0 | 系统 | 时间戳 | 永久 | |
| `deleted_at` | TIMESTAMP | P1 | 发送者 | 软删除 | 永久 | 可选 |

**隐私约束**：
- ❌ 禁止通过普通消息接口保存用户私有偏好
- ✅ 私有偏好必须使用 Scene API

---

## 5. 智能体

### 5.1 Agent（智能体）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `owner_user_id` | UUID | P1 | 用户 | 所有者 | 永久 | 个人智能体 |
| `organization_id` | UUID | P1 | 系统 | 所属组织 | 永久 | 组织智能体 |
| `name` | VARCHAR | P0 | 用户 | 名称 | 永久 | |
| `type` | VARCHAR | P0 | 系统 | 类型 | 永久 | |
| `avatar_url` | VARCHAR | P0 | 用户 | 头像 | 永久 | 可选 |
| `autonomy_level` | VARCHAR | P1 | 用户 | 代理等级 | 永久 | L0-L4 |
| `model_profile_id` | UUID | P1 | 系统 | 模型配置 | 永久 | |
| `status` | VARCHAR | P1 | 系统 | 状态 | 永久 | 活跃/非活跃/暂停 |
| `public_persona` | JSONB | P0 | 用户 | 公开人格 | 永久 | |
| `private_config_encrypted` | BYTEA | **P2** | 用户 | 加密私有配置 | 永久 | **加密存储** |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**加密要求**：`private_config_encrypted` 必须加密存储

---

### 5.2 AgentRun（智能体执行记录）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 30天 | |
| `agent_id` | UUID | P1 | 系统 | 智能体ID | 30天 | |
| `scene_instance_id` | UUID | P1 | 系统 | 场景实例 | 30天 | 可选 |
| `purpose` | VARCHAR | P1 | 系统 | 执行目的 | 30天 | |
| `model_name` | VARCHAR | P1 | 系统 | 使用的模型 | 30天 | |
| `input_hash` | VARCHAR | P1 | 系统 | 输入哈希 | 30天 | **不保存原始输入** |
| `output_hash` | VARCHAR | P1 | 系统 | 输出哈希 | 30天 | **不保存原始输出** |
| `latency_ms` | INT | P1 | 系统 | 延迟 | 30天 | |
| `prompt_tokens` | INT | P1 | 系统 | Token统计 | 30天 | |
| `completion_tokens` | INT | P1 | 系统 | Token统计 | 30天 | |
| `status` | VARCHAR | P1 | 系统 | 执行状态 | 30天 | |
| `error_code` | VARCHAR | P1 | 系统 | 错误码 | 30天 | 可选 |
| `created_at` | TIMESTAMP | P0 | 系统 | 时间戳 | 30天 | |

**隐私约束**：
- ❌ 不保存原始敏感输入
- ❌ 不保存完整思维链
- ✅ 只保存哈希值用于验证

**清理策略**：30天后自动删除

---

## 6. 记忆与授权

### 6.1 MemoryItem（记忆项）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 用户控制 | |
| `owner_user_id` | UUID | P1 | 用户 | 所有者 | 用户控制 | |
| `agent_id` | UUID | P1 | 系统 | 关联智能体 | 用户控制 | 可选 |
| `category` | VARCHAR | P2 | 用户 | 记忆分类 | 用户控制 | |
| `content_encrypted` | BYTEA | **P2/P3** | 用户 | **加密内容** | 用户控制 | **必须加密** |
| `content_embedding` | VECTOR | **P2** | 用户 | 向量嵌入 | 用户控制 | 用于语义检索 |
| `sensitivity_level` | VARCHAR | P2/P3 | 用户 | 敏感级别 | 用户控制 | |
| `visibility` | VARCHAR | P2 | 用户 | 可见性 | 用户控制 | |
| `source` | VARCHAR | P1 | 系统 | 来源 | 用户控制 | |
| `confidence` | FLOAT | P1 | 系统 | 置信度 | 用户控制 | |
| `expires_at` | TIMESTAMP | P2 | 系统 | 过期时间 | 用户控制 | 可选 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 用户控制 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 用户控制 | |
| `deleted_at` | TIMESTAMP | P2 | 用户 | 软删除 | 用户控制 | 可选 |

**加密要求**：`content_encrypted` 必须应用层加密

**保留策略**：
- 默认不自动删除
- 由用户主动删除
- TTL 到期后自动清理

---

### 6.2 ConsentRecord（授权记录）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 90天 | |
| `user_id` | UUID | P2 | 用户 | 被授权用户 | 90天 | |
| `resource_type` | VARCHAR | P2 | 系统 | 资源类型 | 90天 | |
| `resource_id` | UUID | P2 | 系统 | 资源ID | 90天 | 可选 |
| `purpose` | VARCHAR | P2 | 用户 | 授权目的 | 90天 | |
| `scope` | JSONB | P2 | 用户 | 授权范围 | 90天 | |
| `granted` | BOOLEAN | P2 | 用户 | 是否授权 | 90天 | |
| `expires_at` | TIMESTAMP | P2 | 系统 | 过期时间 | 90天 | 可选 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 90天 | |
| `revoked_at` | TIMESTAMP | P2 | 用户 | 撤销时间 | 90天 | 可选 |

**保留策略**：授权撤销后保留90天用于审计

---

## 7. 场景

### 7.1 SceneDefinition（场景定义）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `scene_key` | VARCHAR | P0 | 系统 | 唯一标识 | 永久 | 唯一 |
| `name` | VARCHAR | P0 | 系统 | 场景名称 | 永久 | |
| `version` | VARCHAR | P0 | 系统 | 版本 | 永久 | |
| `description` | TEXT | P0 | 系统 | 描述 | 永久 | |
| `input_schema` | JSONB | P0 | 系统 | 输入Schema | 永久 | |
| `output_schema` | JSONB | P0 | 系统 | 输出Schema | 永久 | |
| `required_permissions` | JSONB | P1 | 系统 | 所需权限 | 永久 | |
| `data_retention_policy` | JSONB | P1 | 系统 | 保留策略 | 永久 | |
| `enabled` | BOOLEAN | P1 | 系统 | 是否启用 | 永久 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

---

### 7.2 SceneInstance（场景实例）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 场景结束 | |
| `scene_definition_id` | UUID | P1 | 系统 | 场景定义 | 场景结束 | |
| `conversation_id` | UUID | P1 | 系统 | 关联会话 | 场景结束 | 可选 |
| `creator_user_id` | UUID | P1 | 用户 | 创建者 | 场景结束 | |
| `status` | VARCHAR | P1 | 系统 | 场景状态 | 场景结束 | |
| `current_stage` | VARCHAR | P1 | 系统 | 当前阶段 | 场景结束 | |
| `public_context` | JSONB | P0/P1 | 系统 | 公开上下文 | 场景结束 | 不含私有内容 |
| `expires_at` | TIMESTAMP | P1 | 系统 | 过期时间 | 场景结束 | 可选 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 场景结束 | |
| `updated_at` | TIMESTAMP | P0 | 系统 | 审计 | 场景结束 | |

**保留策略**：场景结束后删除，最长24小时

---

### 7.3 SceneParticipant（场景参与者）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 场景结束 | |
| `scene_instance_id` | UUID | P1 | 系统 | 场景实例 | 场景结束 | |
| `user_id` | UUID | P1 | 用户 | 用户 | 场景结束 | |
| `agent_id` | UUID | P1 | 系统 | 智能体 | 场景结束 | |
| `consent_record_id` | UUID | **P2** | 用户 | 授权记录 | 场景结束 | |
| `submission_status` | VARCHAR | P1 | 系统 | 提交状态 | 场景结束 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 场景结束 | |

**保留策略**：场景结束后删除，最长24小时

---

### 7.4 PrivateSceneSubmission（私有场景提交）⭐

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 场景结束 | |
| `scene_instance_id` | UUID | P1 | 系统 | 场景实例 | 场景结束 | |
| `participant_id` | UUID | P1 | 系统 | 参与者 | 场景结束 | |
| `encrypted_payload` | BYTEA | **P4** | 用户 | **加密原始提交** | **场景结束立即删除** | **最长24h** |
| `capsule_payload` | JSONB | P2 | 系统 | 偏好胶囊 | **场景结束立即删除** | **最长24h** |
| `expires_at` | TIMESTAMP | P4 | 系统 | 过期时间 | 场景结束 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 场景结束 | |
| `deleted_at` | TIMESTAMP | P4 | 系统 | 删除时间 | 场景结束 | |

**加密要求**：`encrypted_payload` 必须加密

**保留策略**：
- ⚠️ **场景结束后立即删除**
- ⚠️ **最长24小时兜底**
- ⚠️ **定期清理任务**

**隐私等级**：P4 临时秘密（最高敏感）

---

### 7.5 SceneCandidate（场景候选）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `scene_instance_id` | UUID | P1 | 系统 | 场景实例 | 永久 | |
| `title` | VARCHAR | P0 | 系统 | 候选名称 | 永久 | |
| `description` | TEXT | P1 | 系统 | 描述 | 永久 | |
| `public_attributes` | JSONB | P1 | 系统 | 公开属性 | 永久 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

---

### 7.6 PrivateCandidateEvaluation（私有候选评价）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 场景结束 | |
| `scene_instance_id` | UUID | P1 | 系统 | 场景实例 | 场景结束 | |
| `candidate_id` | UUID | P1 | 系统 | 候选ID | 场景结束 | |
| `participant_id` | UUID | P1 | 系统 | 参与者 | 场景结束 | |
| `hard_constraint_passed` | BOOLEAN | P2 | 系统 | 硬约束通过 | 场景结束 | |
| `utility_score` | FLOAT | P2 | 系统 | 效用分数 | 场景结束 | |
| `objection_level` | VARCHAR | P2 | 系统 | 反对级别 | 场景结束 | |
| `reason_codes` | JSONB | P2 | 系统 | 理由码 | 场景结束 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 场景结束 | |
| `expires_at` | TIMESTAMP | P4 | 系统 | 过期时间 | 场景结束 | |

**保留策略**：场景结束后删除，最长24小时

---

### 7.7 SceneResult（场景结果）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `scene_instance_id` | UUID | P1 | 系统 | 场景实例 | 永久 | 唯一 |
| `selected_candidate_id` | UUID | P1 | 系统 | 选中候选 | 永久 | 可选 |
| `ranked_candidates` | JSONB | P1 | 系统 | 排名列表 | 永久 | |
| `aggregate_summary` | JSONB | P1 | 系统 | 聚合摘要 | 永久 | |
| `result_status` | VARCHAR | P1 | 系统 | 结果状态 | 永久 | |
| `confirmed_by_user_id` | UUID | P1 | 用户 | 确认用户 | 永久 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**保留策略**：结果保留，供历史查询

---

## 8. 模型与节点

### 8.1 ModelProfile（模型配置）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `logical_name` | VARCHAR | P0 | 系统 | 逻辑名称 | 永久 | 唯一 |
| `provider_type` | VARCHAR | P1 | 系统 | 提供者类型 | 永久 | 本地/云端/模拟 |
| `capability` | VARCHAR | P1 | 系统 | 能力描述 | 永久 | |
| `default_parameters` | JSONB | P1 | 系统 | 默认参数 | 永久 | |
| `privacy_level` | VARCHAR | P1 | 系统 | 隐私级别 | 永久 | |
| `enabled` | BOOLEAN | P1 | 系统 | 是否启用 | 永久 | |

---

### 8.2 EdgeNode（边缘节点）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `name` | VARCHAR | P0 | 系统 | 节点名称 | 永久 | |
| `endpoint` | VARCHAR | P1 | 系统 | 端点地址 | 永久 | |
| `auth_secret_encrypted` | BYTEA | **P2** | 系统 | **加密密钥** | 永久 | **加密存储** |
| `status` | VARCHAR | P1 | 系统 | 状态 | 永久 | 在线/离线/降级/维护 |
| `cpu_info` | JSONB | P1 | 系统 | CPU信息 | 永久 | |
| `gpu_info` | JSONB | P1 | 系统 | GPU信息 | 永久 | 可选 |
| `memory_total_mb` | INT | P1 | 系统 | 内存 | 永久 | |
| `last_heartbeat_at` | TIMESTAMP | P1 | 系统 | 最后心跳 | 永久 | |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

**加密要求**：`auth_secret_encrypted` 必须加密存储

---

### 8.3 ModelDeployment（模型部署）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 永久 | |
| `node_id` | UUID | P1 | 系统 | 节点ID | 永久 | |
| `model_profile_id` | UUID | P1 | 系统 | 模型配置 | 永久 | |
| `actual_model_name` | VARCHAR | P1 | 系统 | 实际模型名 | 永久 | |
| `endpoint_path` | VARCHAR | P1 | 系统 | 端点路径 | 永久 | |
| `max_concurrency` | INT | P1 | 系统 | 最大并发 | 永久 | |
| `status` | VARCHAR | P1 | 系统 | 状态 | 永久 | 运行中/停止/错误 |
| `created_at` | TIMESTAMP | P0 | 系统 | 审计 | 永久 | |

---

## 9. 审计

### 9.1 AuditLog（审计日志）

| 字段 | 类型 | 分类 | Owner | 用途 | 保留 | 说明 |
|------|------|------|-------|------|------|------|
| `id` | UUID | P0 | 系统 | 主键 | 90天 | |
| `actor_id` | UUID | P1 | 系统 | 操作者 | 90天 | |
| `action` | VARCHAR | P1 | 系统 | 操作类型 | 90天 | |
| `resource_type` | VARCHAR | P1 | 系统 | 资源类型 | 90天 | |
| `resource_id` | UUID | P1 | 系统 | 资源ID | 90天 | 可选 |
| `purpose` | VARCHAR | P1 | 系统 | 操作目的 | 90天 | 可选 |
| `result` | VARCHAR | P1 | 系统 | 结果 | 90天 | 成功/失败 |
| `metadata` | JSONB | P1 | 系统 | 元数据 | 90天 | 脱敏信息 |
| `request_id` | UUID | P1 | 系统 | 请求ID | 90天 | |
| `timestamp` | TIMESTAMP | P0 | 系统 | 时间戳 | 90天 | |

**隐私约束**：
- ❌ 不记录敏感内容本身
- ✅ 只记录操作元数据
- ✅ 自动清理90天后

---

## 10. 数据流与隐私对照

### 10.1 关键数据流

```
用户输入
  ↓
加密存储（P4）
  ↓
智能体提取胶囊（P2）
  ↓
协调层评分（P2）
  ↓
聚合结果（P1）
  ↓
公开展示（P0/P1）
  ↓
清理临时数据（P4/P2）
```

### 10.2 隐私等级分布

| 等级 | 主要实体/字段 | 数量 |
|------|------------|------|
| P0 公开 | 主键、时间戳、公开名称 | ~20个字段 |
| P1 内部 | 配置、状态、公开属性 | ~40个字段 |
| P2 私有 | 偏好、记忆、授权 | ~15个字段 |
| P3 高敏感 | 心理状态 | ~3个字段 |
| P4 临时秘密 | 原始提交、私有评价 | ~5个字段 |

**加密要求统计**：
- 必须加密的字段：5个
- 应用层加密：密码、私有配置、节点密钥
- 临时加密：原始偏好、偏好胶囊（已加密）

---

## 11. 数据保留策略总览

| 数据类型 | 保留期限 | 清理方式 | 说明 |
|---------|---------|---------|------|
| 用户账号 | 永久 | 软删除 | 注销后保留30天 |
| 组织 | 永久 | 归档 | 不物理删除 |
| 消息 | 永久 | 软删除 | 用户删除后保留 |
| 会话 | 永久 | 归档 | 不物理删除 |
| 原始场景提交 | **立即删除** | 定时任务 | 最长24h兜底 |
| 偏好胶囊 | **立即删除** | 定时任务 | 最长24h兜底 |
| 私有候选评价 | **立即删除** | 定时任务 | 最长24h兜底 |
| 场景结果 | 永久 | - | 保留 |
| Agent Run | 30天 | 定时任务 | 自动清理 |
| 审计日志 | 90天 | 定时任务 | 自动清理 |
| 长期记忆 | 用户控制 | 用户删除 | 用户主动管理 |

---

## 12. 相关文档

- [领域词汇表](../domain/DOMAIN_VOCABULARY.md)
- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)

---

**下一步**：P0-06（绘制数据流图，依赖本清单）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
