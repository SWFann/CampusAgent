---
task_id: R1-20
status: completed
stage: R1
title: 修正登录响应
completed_at: 2026-07-14T13:08:00+09:00
estimated_hours: 0.5
actual_hours: 0.1
---

# R1-20：修正登录响应

## 完成状态

✅ **登录响应已修正**

**完成时间**：2026-07-14T13:08:00+09:00

## 目标

修正登录响应，确保不再同时声称只用 Cookie 又返回持久化 Token。

**来自整改计划**：R1-20 - 修正登录响应

## 修正前的问题

**问题**：登录接口可能同时返回 access_token 和 refresh_token，导致前端困惑是否应该持久化存储。

**风险**：
- access_token 被写入 localStorage → XSS 风险
- refresh_token 被同时返回 → 与 HttpOnly Cookie 机制重复

## 修正后的登录响应

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.edu.cn",
  "password": "password123"
}

→ 200 OK
Set-Cookie: refresh_token=xxx; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**关键点**：
- ✅ Refresh Token 通过 HttpOnly Cookie 设置（前端无法访问）
- ✅ Access Token 仅在响应体中返回（前端存储在内存）
- ✅ 前端**无须**把任何 Token 写入浏览器存储

## 前端存储规范

| Token | 存储位置 | 原因 |
|-------|---------|------|
| Access Token | 内存（变量/状态管理） | 1小时过期，无需持久化 |
| Refresh Token | HttpOnly Cookie | 7天有效期，防 XSS |

## 验证结果

- [x] 登录响应已明确：access_token 在响应体，refresh_token 在 Cookie
- [x] 前端无须把 Token 写入浏览器存储

## 下一步

- **R1-21**：修正 Refresh 流程

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
