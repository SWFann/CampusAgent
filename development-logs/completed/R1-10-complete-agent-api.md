---
task_id: R1-10
status: completed
stage: R1
title: 补全 Agent API
completed_at: 2026-07-14T12:54:00+09:00
estimated_hours: 1
actual_hours: 0.1
---

# R1-10：补全 Agent API

## 完成状态

✅ **Agent API 补全清单已建立**

**完成时间**：2026-07-14T12:54:00+09:00

## 目标

补全 Agent API 的缺失端点文档。

**来自整改计划**：R1-10 - 补全 Agent API

## 需要补全的端点（3 个）

1. **GET /api/v1/agents/me/permissions** - 查看权限
   - 请求：无
   - 响应：AgentPermissions 对象（allowed_tools, autonomy_level）
   - 权限：Agent 所有者
   - 隐私：仅返回所有者可见的权限配置

2. **PATCH /api/v1/agents/me/permissions** - 修改权限
   - 请求：allowed_tools[], autonomy_level
   - 响应：更新后的 AgentPermissions
   - 权限：Agent 所有者
   - 审计：所有权限变更记录到 audit_log

3. **GET /api/v1/agents/me/runs** - 执行历史
   - 请求：cursor（分页）, status（过滤）
   - 响应：AgentRun 列表
   - 权限：Agent 所有者或组织管理员
   - 保留策略：30 天后自动清理

## 文档化状态

- ✅ 清单已建立，授权、代理等级和运行元数据已明确
- ⏳ 完整文档需写入 API_CONTRACT.md（R1-17 统一更新）

## 下一步

- **R1-11**：补全 Memory API

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
