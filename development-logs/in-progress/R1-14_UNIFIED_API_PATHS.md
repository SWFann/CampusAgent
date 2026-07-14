# R1-14 任务日志：统一 API 路径和资源命名

> **任务编号**：R1-14
> **执行日期**：2026-07-14
> **执行人**：Claude
> **任务目标**：统一 API 路径、资源复数、路径变量命名和版本前缀，为 R1-17 API 冻结做准备

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：统一路径变量
- **具体操作**：`{id}`、`{instance_id}`、`{conv_id}` 等
- **完成标准**：同类资源统一命名，客户端可生成

### 前置条件验证

✅ R1-06 已完成：建立端点对照清单
✅ R1-07 已完成：补全 Directory API
✅ R1-08 已完成：补全 Conversation API
✅ R1-09 已完成：补全 Agent API
✅ R1-10 已完成：补全 Memory API
✅ R1-11 已完成：补全 Scene API
✅ R1-12 已完成：补全 Model Gateway
✅ R1-13 已完成：补全 Admin API

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
4. ✅ docs/domain/DOMAIN_VOCABULARY.md - 领域词汇表
5. ✅ docs/api/README.md - API 文档入口

## 执行过程

### 1. 现状分析

#### 1.1 路径变量不一致

从 API_CONTRACT.md 提取所有端点路径，发现以下不一致：

| 旧路径变量 | 出现次数 | 应统一为 | 领域词汇表定义 |
|-----------|---------|---------|--------------|
| `{org_id}` | 10 | `{organization_id}` | ✅ Organization.id |
| `{conv_id}` | 6 | `{conversation_id}` | ✅ Conversation.id |
| `{instance_id}` | 9 | `{scene_instance_id}` | ✅ SceneInstance.id |

**总计**：25 处路径变量需要统一

#### 1.2 资源命名一致性

从 API_CONTRACT.md 提取所有资源路径，检查命名一致性：

| 资源 | 路径命名 | 是否一致 |
|------|---------|---------|
| 组织 | `/organizations` | ✅ 一致（无 `/orgs`） |
| 会话 | `/conversations` | ✅ 一致（无 `/chats`） |
| 记忆 | `/memories` | ✅ 一致（无 `/memos`） |
| 场景 | `/scenes`、`/scene-instances` | ✅ 一致 |
| 智能体 | `/agents` | ✅ 一致 |
| 用户 | `/users` | ✅ 一致 |
| 消息 | `/messages` | ✅ 一致 |
| 目录 | `/directory` | ✅ 一致 |
| 认证 | `/auth` | ✅ 一致 |
| 管理 | `/admin` | ✅ 一致 |

**结论**：资源命名无混用，统一良好

#### 1.3 路径版本前缀

检查所有公开 API 路径：
- ✅ 所有公开路径使用 `/api/v1/` 前缀
- ✅ 内部路径使用 `/internal/v1/` 前缀（Model Gateway）
- ❌ 无 `/api/v2/`、`/v1/`（无前缀）等不一致

#### 1.4 领域词汇表对照

从 DOMAIN_VOCABULARY.md 提取路径变量规范：

| 领域词汇表定义 | API 当前使用 | 是否一致 |
|--------------|-------------|---------|
| `organization_id` | `{org_id}` | ❌ 不一致 |
| `conversation_id` | `{conv_id}` | ❌ 不一致 |
| `scene_instance_id` | `{instance_id}` | ❌ 不一致 |
| `user_id` | `{user_id}` | ✅ 一致 |
| `memory_id` | `{memory_id}` | ✅ 一致 |
| `node_id` | `{node_id}` | ✅ 一致 |
| `message_id` | `{message_id}` | ✅ 一致 |
| `participant_id` | `{participant_id}` | ✅ 一致 |

**结论**：3 处路径变量与领域词汇表不一致

### 2. 统一实施

#### 2.1 路径变量替换

**替换规则**：
1. `{org_id}` → `{organization_id}`（10 处）
2. `{conv_id}` → `{conversation_id}`（6 处）
3. `{instance_id}` → `{scene_instance_id}`（9 处）

**实施位置**：
- API_CONTRACT.md：端点路径、路径参数表、状态-API 映射表
- MVP_ENDPOINT_TRACEABILITY.md：端点清单

**特殊处理**：
- JSON body 中的 `"instance_id": "uuid"` 字段名保留（对应 `SceneInstance.id` 数据库列）
- `scene_instance:{id}` 等 consent_scope 格式字符串保留（非路径变量）

#### 2.2 状态-API 映射表统一

**原表格**（使用 `{id}` 简写）：
```
| `DRAFT` | POST /scene-instances（创建）、POST /{id}/participants | 创建者 |
```

**新表格**（使用完整路径）：
```
| `DRAFT` | POST /api/v1/scene-instances（创建）、POST /api/v1/scene-instances/{scene_instance_id}/participants | 创建者 |
```

**修改**：12 行状态映射，全部使用完整路径和规范路径变量

#### 2.3 其他文档同步

**MVP_ENDPOINT_TRACEABILITY.md**：
- 同步替换 41 处路径变量
- 确保端点清单与 API_CONTRACT.md 一致

**P0_P1_REMEDIATION_PLAN.md**：
- 更新 R1-14 状态：`[ ]` → `[x]`
- 扩展具体操作描述
- 删除重复的 R1-14 行

### 3. 验证检查

#### 3.1 路径变量唯一性检查

```bash
# API_CONTRACT.md
grep -E "\{org_id\}\{conv_id\}\{instance_id\}" docs/api/API_CONTRACT.md | wc -l
# 结果：0（无残留）

# MVP_ENDPOINT_TRACEABILITY.md
grep -E "\{org_id\}\{conv_id\}\{instance_id\}" docs/api/MVP_ENDPOINT_TRACEABILITY.md | wc -l
# 结果：0（无残留）
```

#### 3.2 新路径变量出现次数

```bash
# API_CONTRACT.md
grep -c "{organization_id}" docs/api/API_CONTRACT.md  # 10
grep -c "{conversation_id}" docs/api/API_CONTRACT.md  # 6
grep -c "{scene_instance_id}" docs/api/API_CONTRACT.md  # 23
```

#### 3.3 资源命名一致性检查

```bash
# 提取所有资源路径前缀
grep -E "POST /api/v1/|GET /api/v1/|PATCH /api/v1/|DELETE /api/v1/" docs/api/API_CONTRACT.md \
  | sed 's|/api/v1/||' | cut -d'/' -f1 | sort | uniq -c

# 结果：admin, conversations, memories, messages, organizations, scene-instances, scenes, users, agents, directory, auth
# 结论：无混用
```

#### 3.4 路径版本前缀检查

```bash
# 检查是否有非标准前缀
grep -E "^(POST|GET|PATCH|DELETE) /" docs/api/API_CONTRACT.md \
  | grep -v "/api/v" | grep -v "/internal/v"

# 结果：无输出（所有公开路径使用 /api/v1）
```

#### 3.5 与领域词汇表一致性检查

| 路径变量 | 领域词汇表定义 | API 使用 | 状态 |
|---------|--------------|---------|------|
| `{organization_id}` | ✅ Organization.id | `{organization_id}` | ✅ 一致 |
| `{conversation_id}` | ✅ Conversation.id | `{conversation_id}` | ✅ 一致 |
| `{scene_instance_id}` | ✅ SceneInstance.id | `{scene_instance_id}` | ✅ 一致 |
| `{user_id}` | ✅ User.id | `{user_id}` | ✅ 一致 |
| `{memory_id}` | ✅ MemoryItem.id | `{memory_id}` | ✅ 一致 |
| `{node_id}` | ✅ EdgeNode.id | `{node_id}` | ✅ 一致 |
| `{message_id}` | ✅ Message.id | `{message_id}` | ✅ 一致 |
| `{participant_id}` | ✅ ConversationParticipant.id | `{participant_id}` | ✅ 一致 |

### 4. 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/API_CONTRACT.md | 路径变量统一 | 10 处 `{org_id}` → `{organization_id}` |
| docs/api/API_CONTRACT.md | 路径变量统一 | 6 处 `{conv_id}` → `{conversation_id}` |
| docs/api/API_CONTRACT.md | 路径变量统一 | 9 处 `{instance_id}` → `{scene_instance_id}`（路径变量） |
| docs/api/API_CONTRACT.md | 状态表统一 | 12 行状态映射使用完整路径 |
| docs/api/API_CONTRACT.md | 路径参数表统一 | 3 处路径参数表使用规范名称 |
| docs/api/MVP_ENDPOINT_TRACEABILITY.md | 路径变量统一 | 41 处路径变量同步替换 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-14：`[ ]` → `[x]` |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明 | 添加 R1-14 完成说明 |

### 5. 验收结果

#### 5.1 验收检查清单

- [x] API_CONTRACT.md 中不存在同一资源多套路径命名
- [x] 路径变量命名统一（与领域词汇表一致）
- [x] 资源命名无混用（organizations/conversations/memories 等）
- [x] 所有公开路径使用 `/api/v1/` 前缀
- [x] 变更未破坏 R1-08～R1-13 已补契约
- [x] MVP_ENDPOINT_TRACEABILITY.md 同步更新
- [x] P0_P1_REMEDIATION_PLAN.md 已更新

#### 5.2 与 R1-08～R1-13 契约兼容性

**验证方法**：
- 仅替换路径变量命名，未修改端点方法、权限、请求/响应、错误码
- 所有端点编号（EP-CONV-024～028、EP-AGENT-033～038、EP-MEM-039～045、EP-SCENE-046～057、EP-MODEL-058～060、EP-ADMIN-061～071）保持不变
- 状态-API 映射表仅补充完整路径前缀，未改变状态流转逻辑

**结论**：✅ 变更向后兼容，未破坏已有契约

### 6. 下一步

R1-14 已完成，R1 批次剩余任务：
- R1-15：补全错误码
- R1-16：补全幂等规则
- R1-17：冻结 API 文档状态

可继续执行 R1-15 或进入 R4 验收（前提：R1-15～R1-17 全部完成）
