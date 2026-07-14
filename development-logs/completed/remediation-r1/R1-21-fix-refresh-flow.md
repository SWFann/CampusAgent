---
task_id: R1-21
status: completed
stage: R1
title: 修正 Refresh 流程
completed_at: 2026-07-14T13:09:00+09:00
estimated_hours: 0.5
actual_hours: 0.15
---

# R1-21：修正 Refresh 流程

## 完成状态

✅ **Refresh 流程已修正**

**完成时间**：2026-07-14T13:09:00+09:00

## 目标

修正 Refresh Token 流程，确保 Cookie 轮换、重放检测和注销撤销与 ADR 一致。

**来自整改计划**：R1-21 - 修正 Refresh 流程

## Refresh Token 流程

### 正常刷新

```http
POST /api/v1/auth/refresh
Cookie: refresh_token=<old_token>

→ 200 OK
Set-Cookie: refresh_token=<new_token>; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 轮换机制

- 每次刷新成功后，旧 Refresh Token 失效
- 新的 Refresh Token 通过 Cookie 返回
- 数据库存储当前有效的 Refresh Token 哈希

### 重放检测

- 如果使用已使用的 Refresh Token → 403 Forbidden
- 错误码：`AUTH_REPLAYED_TOKEN`
- 触发重放检测时，撤销该用户所有 Refresh Token

### 注销撤销

```http
POST /api/v1/auth/logout
Cookie: refresh_token=<token>

→ 204 No Content
Set-Cookie: refresh_token=; Max-Age=0
```

- 从数据库删除 Refresh Token
- Cookie 立即失效

## 验证结果

- [x] Cookie 轮换机制已明确
- [x] 重放检测已定义
- [x] 注销撤销已实现
- [x] ADR 与 API 契约一致

## 下一步

- **R1-22**：修正 WebSocket 鉴权

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
