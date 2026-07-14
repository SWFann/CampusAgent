# HTTP API 契约

> **版本**：v1.0-DRAFT  
> **基线日期**：2026-07-14  
> **状态**：草稿，待评审  
> **维护者**：开发团队

## 1. 基础约定

### 1.1 API 前缀

```
/api/v1
```

### 1.2 响应格式

**成功响应**：
```json
{
  "success": true,
  "data": {},
  "request_id": "req_xxx"
}
```

**失败响应**：
```json
{
  "success": false,
  "error": {
    "code": "MODULE_REASON",
    "message": "人类可读的错误信息",
    "details": {}
  },
  "request_id": "req_xxx"
}
```

### 1.3 分页

**请求**：
```
?page=1&page_size=20
```

**响应**：
```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

### 1.4 幂等性

创建场景、提交偏好、确认结果等接口支持：

```
Idempotency-Key: <uuid>
```

重复请求返回相同结果。

### 1.5 鉴权

```
Authorization: Bearer <access_token>
```

或使用 HttpOnly Cookie。

### 1.6 错误码格式

格式：`MODULE_REASON`

示例：
```
AUTH_INVALID_TOKEN
USER_NOT_FOUND
ORG_PERMISSION_DENIED
CONVERSATION_NOT_MEMBER
AGENT_CONSENT_REQUIRED
SCENE_INVALID_STAGE
MEMORY_ACCESS_DENIED
MODEL_NODE_UNAVAILABLE
```

---

## 2. API 端点清单

### 2.1 Auth（认证）

#### POST /api/v1/auth/register

**描述**：注册新用户

**权限**：公开

**请求体**：
```json
{
  "email": "student@example.edu",
  "password": "******",
  "display_name": "张三",
  "student_no": "20260001",
  "organization_ids": ["class_uuid", "dorm_uuid"]
}
```

**响应**：201 Created

**说明**：
- 邮箱和学号必须唯一
- 支持幂等性
- 发布 `UserRegistered` 事件

---

#### POST /api/v1/auth/login

**描述**：用户登录

**权限**：公开

**请求体**：
```json
{
  "email": "student@example.edu",
  "password": "******"
}
```

**响应**：200 OK
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**安全**：
- 密码错误次数限制
- 不泄露账号是否存在
- 统一响应时间

---

#### POST /api/v1/auth/refresh

**描述**：刷新令牌

**权限**：已认证

**请求体**：
```json
{
  "refresh_token": "..."
}
```

**响应**：200 OK

---

#### POST /api/v1/auth/logout

**描述**：注销

**权限**：已认证

**响应**：204 No Content

---

#### GET /api/v1/auth/me

**描述**：获取当前用户信息

**权限**：已认证

**响应**：200 OK
```json
{
  "id": "uuid",
  "email": "...",
  "display_name": "...",
  "global_role": "STUDENT",
  "agent": { ... }
}
```

---

### 2.2 User（用户）

#### GET /api/v1/users/{user_id}

**描述**：获取用户详情

**权限**：公开信息

**响应**：200 OK
```json
{
  "id": "uuid",
  "display_name": "...",
  "avatar_url": "...",
  "profile_visibility": "PUBLIC"
}
```

**隐私**：
- 不返回私有信息
- 可见性控制生效

---

#### PATCH /api/v1/users/{user_id}

**描述**：更新用户资料

**权限**：本人或管理员

**请求体**：
```json
{
  "display_name": "...",
  "bio": "..."
}
```

**响应**：200 OK

---

#### GET /api/v1/users/{user_id}/organizations

**描述**：获取用户组织列表

**权限**：本人或管理员

**响应**：200 OK

---

#### GET /api/v1/users/{user_id}/agent

**描述**：获取用户智能体

**权限**：本人或管理员

**响应**：200 OK

---

### 2.3 Organization（组织）

#### POST /api/v1/organizations

**描述**：创建组织

**权限**：已认证

**请求体**：
```json
{
  "name": "8栋302宿舍",
  "type": "DORM",
  "description": "...",
  "visibility": "PRIVATE",
  "join_policy": "INVITE_ONLY"
}
```

**响应**：201 Created

---

#### GET /api/v1/organizations

**描述**：获取组织列表

**权限**：已认证

**查询参数**：
```
?type=DORM&page=1&page_size=20
```

**响应**：200 OK

---

#### GET /api/v1/organizations/{org_id}

**描述**：获取组织详情

**权限**：成员或可见性允许

**响应**：200 OK

---

#### PATCH /api/v1/organizations/{org_id}

**描述**：更新组织

**权限**：OWNER 或 ADMIN

**请求体**：部分更新

**响应**：200 OK

---

#### DELETE /api/v1/organizations/{org_id}

**描述**：删除组织

**权限**：OWNER

**响应**：204 No Content

**说明**：软删除或归档

---

#### POST /api/v1/organizations/{org_id}/members

**描述**：添加成员

**权限**：OWNER 或 ADMIN

**请求体**：
```json
{
  "user_id": "uuid",
  "role": "MEMBER"
}
```

**响应**：201 Created

---

#### GET /api/v1/organizations/{org_id}/members

**描述**：获取成员列表

**权限**：成员

**响应**：200 OK

---

#### PATCH /api/v1/organizations/{org_id}/members/{user_id}

**描述**：更新成员角色

**权限**：OWNER 或 ADMIN

**请求体**：
```json
{
  "role": "ADMIN"
}
```

**响应**：200 OK

**保护**：最后一个 OWNER 不能降级

---

#### DELETE /api/v1/organizations/{org_id}/members/{user_id}

**描述**：移除成员

**权限**：OWNER 或 ADMIN

**响应**：204 No Content

**保护**：最后一个 OWNER 不能移除

---

#### POST /api/v1/organizations/{org_id}/join

**描述**：加入组织

**权限**：已认证

**响应**：201 Created

---

#### POST /api/v1/organizations/{org_id}/leave

**描述**：退出组织

**权限**：成员

**响应**：204 No Content

**保护**：最后一个 OWNER 不能退出

---

### 2.4 Conversation（会话）

#### POST /api/v1/conversations

**描述**：创建会话

**权限**：已认证

**请求体**：
```json
{
  "type": "GROUP",
  "title": "8栋302宿舍",
  "participant_user_ids": ["uuid1", "uuid2"],
  "attach_group_agent": true
}
```

**响应**：201 Created

---

#### GET /api/v1/conversations

**描述**：获取会话列表

**权限**：已认证

**响应**：200 OK

---

#### GET /api/v1/conversations/{conv_id}

**描述**：获取会话详情

**权限**：参与者

**响应**：200 OK

---

#### POST /api/v1/conversations/{conv_id}/messages

**描述**：发送消息

**权限**：参与者

**请求体**：
```json
{
  "message_type": "TEXT",
  "content": "...",
  "reply_to_id": null
}
```

**响应**：201 Created

**隐私**：私有偏好不能通过此接口发送

---

### 2.5 Agent（智能体）

#### GET /api/v1/agents/me

**描述**：获取我的智能体

**权限**：本人

**响应**：200 OK

---

#### PATCH /api/v1/agents/me

**描述**：更新智能体配置

**权限**：本人

**请求体**：
```json
{
  "name": "...",
  "autonomy_level": "L1"
}
```

**响应**：200 OK

---

#### POST /api/v1/agents/me/permissions

**描述**：更新场景权限

**权限**：本人

**请求体**：
```json
{
  "scene_key": "meal_planning",
  "autonomy_level": "L2",
  "allowed_memory_categories": ["FOOD_PREFERENCE"],
  "expires_at": "2026-07-14T00:00:00+09:00"
}
```

**响应**：200 OK

---

### 2.6 Memory（记忆）

#### GET /api/v1/memories

**描述**：获取记忆列表

**权限**：本人

**查询参数**：
```
?category=FOOD_PREFERENCE&page=1&page_size=20
```

**响应**：200 OK

---

#### POST /api/v1/memories

**描述**：创建记忆

**权限**：本人

**响应**：201 Created

---

#### DELETE /api/v1/memories/{memory_id}

**描述**：删除记忆

**权限**：所有者

**响应**：204 No Content

---

### 2.7 Scene（场景）

#### POST /api/v1/scene-instances

**描述**：创建场景实例

**权限**：已认证

**请求体**：
```json
{
  "scene_key": "meal_planning",
  "conversation_id": "uuid",
  "participant_user_ids": ["uuid1", "uuid2"],
  "public_context": {
    "date": "2026-07-18",
    "city": "广州"
  }
}
```

**响应**：201 Created

---

#### POST /api/v1/scene-instances/{id}/private-submission

**描述**：提交私有偏好 ⭐ 核心隐私接口

**权限**：参与者本人

**请求体**：
```json
{
  "preferences": {
    "budget_max": 100,
    "cuisines": ["日料", "粤菜"],
    "excluded_ingredients": ["香菜"],
    "distance_limit_km": 3,
    "notes": "希望安静一点"
  },
  "save_to_long_term_memory": false
}
```

**响应**：202 Accepted
```json
{
  "submission_status": "ACCEPTED",
  "capsule_generated": true,
  "expires_at": "2026-07-14T00:00:00+09:00"
}
```

**隐私控制**：
- 只接受自己的提交
- 响应不回显原文
- 不进入消息表

---

#### POST /api/v1/scene-instances/{id}/consent

**描述**：授权场景

**权限**：参与者本人

**请求体**：
```json
{
  "granted": true,
  "autonomy_level": "L2",
  "expires_at": "2026-07-14T00:00:00+09:00"
}
```

**响应**：200 OK

---

#### POST /api/v1/scene-instances/{id}/start

**描述**：开始处理

**权限**：创建者

**响应**：202 Accepted

---

#### GET /api/v1/scene-instances/{id}/candidates

**描述**：获取候选列表

**权限**：参与者

**响应**：200 OK

---

#### POST /api/v1/scene-instances/{id}/vote

**描述**：投票

**权限**：参与者

**请求体**：
```json
{
  "candidate_id": "uuid"
}
```

**响应**：200 OK

---

#### POST /api/v1/scene-instances/{id}/confirm

**描述**：确认结果

**权限**：群主或创建者

**请求体**：
```json
{
  "selected_candidate_id": "uuid"
}
```

**响应**：200 OK

---

#### POST /api/v1/scene-instances/{id}/cancel

**描述**：取消场景

**权限**：群主或创建者

**响应**：204 No Content

---

### 2.8 Admin（管理）

#### GET /api/v1/admin/nodes

**描述**：获取节点列表

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**响应**：200 OK

---

#### GET /api/v1/admin/nodes/{node_id}/metrics

**描述**：获取节点指标

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**响应**：200 OK
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "gpu_usage": 82.1,
  "active_requests": 12
}
```

**隐私**：不含敏感标签

---

#### GET /api/v1/admin/users

**描述**：获取用户列表

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**响应**：200 OK

**隐私**：不含私有偏好和记忆

---

## 3. WebSocket 事件（P0-10）

见 [实时与事件契约](./WEBSOCKET_CONTRACT.md)

---

## 4. 版本管理

### 4.1 API 版本

当前版本：`v1`

版本变更必须：
1. 更新本文档版本号
2. 更新 OpenAPI 规范
3. 通知前端团队
4. 至少保留1个旧版本

### 4.2 破坏性变更

破坏性变更必须：
1. 提前至少2周通知
2. 提供迁移指南
3. 保持旧版本可用
4. 通过 ADR 记录原因

---

## 5. 相关文档

- [领域词汇表](../domain/DOMAIN_VOCABULARY.md)
- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [场景状态机](../architecture/SCENE_STATE_MACHINE.md)

---

**下一步**：P0-10（草拟实时与事件契约）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
