---
task_id: R1-16
status: completed
stage: R1
title: 补全幂等规则
completed_at: 2026-07-14T13:03:00+09:00
estimated_hours: 1
actual_hours: 0.15
---

# R1-16：补全幂等规则

## 完成状态

✅ **幂等规则规范已建立**

**完成时间**：2026-07-14T13:03:00+09:00

## 目标

为每个关键写接口定义幂等性规则，避免重复提交导致的重复数据。

**来自整改计划**：R1-16 - 补全幂等规则

## 幂等性规范

### 什么时候需要幂等性

以下操作**必须**支持幂等性：
1. **创建资源**：组织、会话、场景实例、记忆
2. **提交操作**：私有提交、投票、确认结果
3. **状态变更**：开始处理、取消场景

### Idempotency-Key 机制

**请求头**：
```
Idempotency-Key: uuid-v4
```

**响应**：
- 首次请求：返回 200/201 + 结果
- 重复请求：返回 200 + 相同结果（不重复执行）

**存储**：Redis，TTL 24 小时

### 各接口幂等性要求

| 接口 | 幂等性要求 | 重复提交行为 |
|------|-----------|------------|
| `POST /api/v1/organizations` | 必须 | 返回已创建的组织 |
| `POST /api/v1/conversations` | 必须 | 返回已创建的会话 |
| `POST /api/v1/scene-instances` | 必须 | 返回已创建的实例 |
| `POST /api/v1/memories` | 必须 | 返回已创建的记忆 |
| `POST /api/v1/scene-instances/{id}/private-submission` | 必须 | 返回已保存的提交 |
| `POST /api/v1/scene-instances/{id}/vote` | 必须 | 返回已提交的投票 |
| `POST /api/v1/scene-instances/{id}/confirm` | 必须 | 返回已确认的结果 |
| `POST /api/v1/scene-instances/{id}/cancel` | 必须 | 返回已取消的状态 |
| `PATCH /api/v1/organizations/{id}` | 可选 | 返回最新状态 |
| `DELETE /api/v1/memories/{id}` | 必须 | 返回 204（已删除） |

### 幂等性失败处理

如果缺少 `Idempotency-Key`：
- 返回 400 Bad Request
- 错误码：`IDEMPOTENCY_KEY_REQUIRED`

如果 `Idempotency-Key` 重复：
- 返回 200 OK + 首次请求的结果
- 不重新执行操作

## 验证结果

- [x] 每个关键写接口的幂等性要求已定义
- [x] Idempotency-Key 机制已明确

## 下一步

- **R1-17**：冻结 API 文档状态

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
