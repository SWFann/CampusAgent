---
task_id: R1-07
status: in_progress
stage: R1
title: 建立完整端点清单
started_at: 2026-07-14T12:51:00+09:00
completed_at:
estimated_hours: 2
actual_hours:
---

# R1-07：建立完整端点清单

## 目标

建立完整的 62 端点清单，为后续补全 HTTP 合同提供基础。

**来自整改计划**：R1-07 - 建立完整端点清单

**产物**：
- 完整端点清单（62 个 MVP 端点）
- 端点文档化状态追踪

**依赖**：R1-06（端点不一致已识别 ✅）

## 验收标准

- [ ] 列出所有 62 个 MVP 端点
- [ ] 标记每个端点的文档化状态
- [ ] 识别需要补全的端点

## 端点清单（MVP_SCOPE.md 68 个端点）

### 认证模块（5 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/auth/register` | POST | 注册 | ✅ 已文档化 |
| `/api/v1/auth/login` | POST | 登录 | ✅ 已文档化 |
| `/api/v1/auth/refresh` | POST | 刷新令牌 | ✅ 已文档化 |
| `/api/v1/auth/logout` | POST | 注销 | ✅ 已文档化 |
| `/api/v1/auth/me` | GET | 当前用户信息 | ✅ 已文档化 |

### 用户模块（4 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/users/{user_id}` | GET | 用户详情 | ✅ 已文档化 |
| `/api/v1/users/{user_id}` | PATCH | 更新用户资料 | ✅ 已文档化 |
| `/api/v1/users/{user_id}/organizations` | GET | 用户组织列表 | ❌ 缺失 |
| `/api/v1/users/{user_id}/agent` | GET | 用户智能体 | ❌ 缺失 |

### 组织模块（11 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/organizations` | POST | 创建组织 | ✅ 已文档化 |
| `/api/v1/organizations` | GET | 组织列表 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}` | GET | 组织详情 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}` | PATCH | 更新组织 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}` | DELETE | 删除组织 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}/members` | POST | 添加成员 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}/members` | GET | 成员列表 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}/members/{user_id}` | PATCH | 更新成员角色 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}/members/{user_id}` | DELETE | 移除成员 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}/join` | POST | 加入组织 | ✅ 已文档化 |
| `/api/v1/organizations/{org_id}/leave` | POST | 退出组织 | ✅ 已文档化 |

### 目录模块（3 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/directory/search` | GET | 搜索用户/组织 | ✅ 已文档化 |
| `/api/v1/directory/tree` | GET | 组织树 | ✅ 已文档化 |
| `/api/v1/directory/recommended` | GET | 推荐（占位） | ✅ 已文档化 |

### 对话模块（8 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/conversations` | POST | 创建会话 | ✅ 已文档化 |
| `/api/v1/conversations` | GET | 会话列表 | ✅ 已文档化 |
| `/api/v1/conversations/{conv_id}` | GET | 会话详情 | ✅ 已文档化 |
| `/api/v1/conversations/{conv_id}` | PATCH | 更新会话 | ❌ 缺失 |
| `/api/v1/conversations/{conv_id}/participants` | POST | 添加参与者 | ❌ 缺失 |
| `/api/v1/conversations/{conv_id}/participants/{participant_id}` | DELETE | 移除参与者 | ❌ 缺失 |
| `/api/v1/conversations/{conv_id}/messages` | GET | 消息列表 | ❌ 缺失 |
| `/api/v1/conversations/{conv_id}/messages` | POST | 发送消息 | ❌ 缺失 |
| `/api/v1/messages/{message_id}` | DELETE | 删除消息 | ❌ 缺失 |

**注**：对话模块实际 9 个端点（MVP_SCOPE 列出 8 个 + 删除消息）

### 智能体模块（6 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/agents/me` | GET | 我的智能体 | ✅ 已文档化 |
| `/api/v1/agents/me` | PATCH | 更新智能体配置 | ✅ 已文档化 |
| `/api/v1/agents/me/chat` | POST | 与智能体对话 | ✅ 已文档化 |
| `/api/v1/agents/me/permissions` | GET | 查看权限 | ❌ 缺失 |
| `/api/v1/agents/me/permissions` | PATCH | 修改权限 | ❌ 缺失 |
| `/api/v1/agents/me/runs` | GET | 执行历史 | ❌ 缺失 |

### 记忆模块（7 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/memories` | GET | 记忆列表 | ✅ 已文档化 |
| `/api/v1/memories` | POST | 创建记忆 | ✅ 已文档化 |
| `/api/v1/memories/{memory_id}` | GET | 记忆详情 | ✅ 已文档化 |
| `/api/v1/memories/{memory_id}` | PATCH | 更新记忆 | ✅ 已文档化 |
| `/api/v1/memories/{memory_id}` | DELETE | 删除记忆 | ✅ 已文档化 |
| `/api/v1/memories/access-log` | GET | 访问记录 | ❌ 缺失 |
| `/api/v1/memories/export` | POST | 导出记忆 | ❌ 缺失 |

### 场景模块（13 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/scenes` | GET | 场景列表 | ✅ 已文档化 |
| `/api/v1/scenes/{scene_key}` | GET | 场景详情 | ✅ 已文档化 |
| `/api/v1/scene-instances` | POST | 创建场景实例 | ✅ 已文档化 |
| `/api/v1/scene-instances/{instance_id}` | GET | 场景详情 | ✅ 已文档化 |
| `/api/v1/scene-instances/{instance_id}/participants` | POST | 添加参与者 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/consent` | POST | 授权 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/private-submission` | POST | 私有提交 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/start` | POST | 开始处理 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/candidates` | GET | 候选列表 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/vote` | POST | 投票 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/confirm` | POST | 确认结果 | ❌ 缺失 |
| `/api/v1/scene-instances/{instance_id}/cancel` | POST | 取消场景 | ❌ 缺失 |

### 模型网关（3 个 - 内部）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/internal/v1/model/chat` | POST | 模型调用（内部） | ❌ 缺失 |
| `/internal/v1/model/embedding` | POST | 嵌入向量（内部） | ❌ 缺失 |
| `/internal/v1/model/health` | GET | 模型健康检查 | ❌ 缺失 |

### 健康检查（2 个）

| 端点 | 方法 | 描述 | 文档状态 |
|------|------|------|---------|
| `/api/v1/health/live` | GET | 健康检查 | ❌ 缺失 |
| `/api/v1/health/ready` | GET | 健康检查 | ❌ 缺失 |

### 管理模块（非 MVP，12 个）

（R1-B 整改范围不包括非 MVP 端点）

## 统计

- **MVP 端点总数**：68 个
- **已文档化**：41 个（60.3%）
- **缺失文档**：27 个（39.7%）
- **完成目标**：100%（需补全 27 个端点）

## 下一步

- **R1-07 完成**：更新完整端点清单到文档
- **R1-08 至 R1-14**：补全 7 个模块的缺失端点

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
