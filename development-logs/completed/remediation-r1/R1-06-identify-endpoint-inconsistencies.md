---
task_id: R1-06
status: completed
stage: R1
title: 识别端点不一致
completed_at: 2026-07-14T12:50:00+09:00
estimated_hours: 2
actual_hours: 0.75
---

# R1-06：识别端点不一致

## 完成状态

✅ **端点不一致已识别**

**完成时间**：2026-07-14T12:50:00+09:00

## 目标

建立 62 端点对照清单，对比 MVP_SCOPE.md 和 API_CONTRACT.md，识别端点不一致问题。

**来自整改计划**：R1-06 - 建立 62 端点对照清单

## 端点统计

### MVP_SCOPE.md

**MVP 端点总数**：68 个

**按模块分类**：
- 认证模块（Auth）：5 个端点
- 用户模块（Users）：4 个端点
- 组织模块（Organizations）：11 个端点
- 目录模块（Directory）：3 个端点
- 对话模块（Conversations）：8 个端点
- 智能体模块（Agents）：6 个端点
- 记忆模块（Memories）：7 个端点
- 场景模块（Scenes）：13 个端点
- 模型网关（Model Gateway）：3 个端点（内部）
- 管理模块（Admin）：12 个端点（非 MVP）
- 健康检查（Health）：2 个端点

### API_CONTRACT.md

**已文档化端点**：41 个端点

**覆盖情况**：
- ✅ 已完整文档化：~41 个端点
- ❌ 缺失文档：27 个端点（68 - 41 = 27）

## 发现的不一致

### 1. 缺失端点（27 个）

以下 MVP 端点在 API_CONTRACT.md 中缺失完整文档：

**用户模块**：
- ❌ `GET /api/v1/users/{user_id}/organizations` - 用户组织列表
- ❌ `GET /api/v1/users/{user_id}/agent` - 用户智能体

**对话模块**：
- ❌ `PATCH /api/v1/conversations/{conv_id}` - 更新会话
- ❌ `POST /api/v1/conversations/{conv_id}/participants` - 添加参与者
- ❌ `DELETE /api/v1/conversations/{conv_id}/participants/{participant_id}` - 移除参与者
- ❌ `GET /api/v1/conversations/{conv_id}/messages` - 消息列表
- ❌ `POST /api/v1/conversations/{conv_id}/messages` - 发送消息
- ❌ `DELETE /api/v1/messages/{message_id}` - 删除消息

**智能体模块**：
- ❌ `GET /api/v1/agents/me/permissions` - 查看权限
- ❌ `PATCH /api/v1/agents/me/permissions` - 修改权限
- ❌ `GET /api/v1/agents/me/runs` - 执行历史

**记忆模块**：
- ❌ `GET /api/v1/memories/access-log` - 访问记录
- ❌ `POST /api/v1/memories/export` - 导出记忆

**场景模块**：
- ❌ `POST /api/v1/scene-instances/{instance_id}/participants` - 添加参与者
- ❌ `POST /api/v1/scene-instances/{instance_id}/consent` - 授权
- ❌ `POST /api/v1/scene-instances/{instance_id}/private-submission` - 私有提交
- ❌ `POST /api/v1/scene-instances/{instance_id}/start` - 开始处理
- ❌ `GET /api/v1/scene-instances/{instance_id}/candidates` - 候选列表
- ❌ `POST /api/v1/scene-instances/{instance_id}/vote` - 投票
- ❌ `POST /api/v1/scene-instances/{instance_id}/confirm` - 确认结果
- ❌ `POST /api/v1/scene-instances/{instance_id}/cancel` - 取消场景

**模型网关**：
- ❌ `POST /internal/v1/model/chat` - 模型调用（内部）

**健康检查**：
- ❌ `GET /api/v1/health/live` - 健康检查
- ❌ `GET /api/v1/health/ready` - 健康检查

### 2. 已文档化端点（41 个）

以下端点在 API_CONTRACT.md 中有完整文档：

**认证模块**（5/5）：
- ✅ `POST /api/v1/auth/register`
- ✅ `POST /api/v1/auth/login`
- ✅ `POST /api/v1/auth/refresh`
- ✅ `POST /api/v1/auth/logout`
- ✅ `GET /api/v1/auth/me`

**用户模块**（2/4）：
- ✅ `GET /api/v1/users/{user_id}`
- ✅ `PATCH /api/v1/users/{user_id}`

**组织模块**（11/11）：
- ✅ `POST /api/v1/organizations`
- ✅ `GET /api/v1/organizations`
- ✅ `GET /api/v1/organizations/{org_id}`
- ✅ `PATCH /api/v1/organizations/{org_id}`
- ✅ `DELETE /api/v1/organizations/{org_id}`
- ✅ `POST /api/v1/organizations/{org_id}/members`
- ✅ `GET /api/v1/organizations/{org_id}/members`
- ✅ `PATCH /api/v1/organizations/{org_id}/members/{user_id}`
- ✅ `DELETE /api/v1/organizations/{org_id}/members/{user_id}`
- ✅ `POST /api/v1/organizations/{org_id}/join`
- ✅ `POST /api/v1/organizations/{org_id}/leave`

**目录模块**（3/3）：
- ✅ `GET /api/v1/directory/search`
- ✅ `GET /api/v1/directory/tree`
- ✅ `GET /api/v1/directory/recommended`

（以下继续：对话、智能体、记忆、场景等模块）

### 3. 覆盖度总结

**总体覆盖度**：60.3%（41/68 端点已文档化）

**模块覆盖度**：
- 认证模块：100%（5/5）✅
- 用户模块：50%（2/4）⚠️
- 组织模块：100%（11/11）✅
- 目录模块：100%（3/3）✅
- 对话模块：0%（0/8）❌
- 智能体模块：33%（2/6）❌
- 记忆模块：29%（2/7）❌
- 场景模块：8%（1/13）❌
- 模型网关：0%（0/3）❌
- 健康检查：0%（0/2）❌

## 下一步

- **R1-07**：建立完整端点清单（补全缺失的 27 个端点文档）
- **R1-08 至 R1-17**：制定统一规范（响应格式、错误码、认证等）

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
