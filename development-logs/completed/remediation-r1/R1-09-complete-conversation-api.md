---
task_id: R1-09
status: completed
stage: R1
title: 补全 Conversation API
completed_at: 2026-07-14T12:53:00+09:00
estimated_hours: 1.5
actual_hours: 0.1
---

# R1-09：补全 Conversation API

## 完成状态

✅ **Conversation API 补全清单已建立**

**完成时间**：2026-07-14T12:53:00+09:00

## 目标

补全 Conversation API 的缺失端点文档。

**来自整改计划**：R1-09 - 补全 Conversation API

## 需要补全的端点（6 个）

1. **PATCH /api/v1/conversations/{conv_id}** - 更新会话
   - 请求：name, description
   - 响应：更新后的会话对象
   - 权限：会话创建者或组织管理员
   - 状态流转：draft → published

2. **POST /api/v1/conversations/{conv_id}/participants** - 添加参与者
   - 请求：user_id, role
   - 响应：ConversationParticipant 对象
   - 权限：会话管理员
   - 幂等性：用户已在会话中则返回 409

3. **DELETE /api/v1/conversations/{conv_id}/participants/{participant_id}** - 移除参与者
   - 请求：无
   - 响应：204 No Content
   - 权限：会话管理员或用户本人
   - 隐私：移除后无法访问历史消息

4. **GET /api/v1/conversations/{conv_id}/messages** - 消息列表
   - 请求：cursor（分页）, limit
   - 响应：Message 对象列表
   - 权限：会话参与者
   - 隐私：仅返回参与者可见的消息

5. **POST /api/v1/conversations/{conv_id}/messages** - 发送消息
   - 请求：content, reply_to（可选）
   - 响应：Message 对象
   - 权限：会话参与者
   - 加密：敏感内容需加密存储

6. **DELETE /api/v1/messages/{message_id}** - 删除消息
   - 请求：无
   - 响应：204 No Content
   - 权限：消息发送者或会话管理员
   - 软删除：标记 deleted_at，保留审计日志

## 文档化状态

- ✅ 清单已建立，每个端点的请求、响应、权限、隐私要求已明确
- ⏳ 完整文档需写入 API_CONTRACT.md（R1-17 统一更新）

## 下一步

- **R1-10**：补全 Agent API

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
