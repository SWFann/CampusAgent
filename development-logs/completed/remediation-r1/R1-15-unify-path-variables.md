---
task_id: R1-15
status: completed
stage: R1
title: 统一路径变量
completed_at: 2026-07-14T12:59:00+09:00
estimated_hours: 0.5
actual_hours: 0.15
---

# R1-15：统一路径变量

## 完成状态

✅ **路径变量命名规范已建立**

**完成时间**：2026-07-14T12:59:00+09:00

## 目标

统一 API 路径变量的命名规范，确保同类资源使用相同的变量名。

**来自整改计划**：R1-15 - 统一路径变量

## 路径变量规范

### 主键变量对照表

| 资源类型 | 路径变量名 | 示例 |
|---------|----------|------|
| 用户 | `{user_id}` | `/api/v1/users/{user_id}` |
| 组织 | `{org_id}` | `/api/v1/organizations/{org_id}` |
| 会话 | `{conv_id}` | `/api/v1/conversations/{conv_id}` |
| 场景实例 | `{instance_id}` | `/api/v1/scene-instances/{instance_id}` |
| 场景定义 | `{scene_key}` | `/api/v1/scenes/{scene_key}` |
| 记忆 | `{memory_id}` | `/api/v1/memories/{memory_id}` |
| 消息 | `{message_id}` | `/api/v1/messages/{message_id}` |
| 节点 | `{node_id}` | `/api/v1/admin/nodes/{node_id}` |
| 参与者 | `{participant_id}` | `/api/v1/conversations/{conv_id}/participants/{participant_id}` |

### 命名规则

1. **主键统一使用 `{entity_id}` 格式**
2. **实体名使用单数名词**：user, org, conv, instance, scene, memory, message, node
3. **避免复数形式**：不使用 `{users}`, `{orgs}`
4. **保持一致性**：同类资源全局统一

### 特殊变量

| 变量名 | 用途 | 示例 |
|-------|------|------|
| `{scene_key}` | 场景定义标识（字符串） | `/api/v1/scenes/{scene_key}` |
| `{cursor}` | 分页游标 | `?cursor=xxx` |

## 验证结果

- [x] 所有端点路径变量命名一致
- [x] 无复数形式的路径变量
- [x] 主键变量统一使用 `{entity_id}` 格式

## 下一步

- **R1-16**：建立请求响应模型

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
