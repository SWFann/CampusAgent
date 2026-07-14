---
task_id: R1-19
status: completed
stage: R1
title: 定义 CSRF 方案
completed_at: 2026-07-14T13:07:00+09:00
estimated_hours: 0.5
actual_hours: 0.1
---

# R1-19：定义 CSRF 方案

## 完成状态

✅ **CSRF 方案已定义**

**完成时间**：2026-07-14T13:07:00+09:00

## 目标

定义 CSRF 防护方案：Token 来源、Header、轮换和失败响应。

**来自整改计划**：R1-19 - 定义 CSRF 方案

## CSRF 防护方案

### 机制：Double Submit Cookie

1. **登录时**：服务器生成 CSRF Token 并设置为 Cookie
2. **前端**：从 Cookie 读取 CSRF Token，放入请求头
3. **后端**：比较 Cookie 中的 Token 和请求头中的 Token

### CSRF Token Cookie

| 属性 | 值 |
|------|-----|
| Name | `csrf_token` |
| HttpOnly | false（前端可读取） |
| Secure | true |
| SameSite | Strict |
| Max-Age | 匹配 refresh_token（7天） |

### 请求头

```
X-CSRF-Token: <csrf_token_value>
```

### 验证规则

- 所有写请求（POST/PUT/PATCH/DELETE）必须携带 `X-CSRF-Token`
- 读请求（GET）豁免 CSRF 检查
- Token 不匹配 → 403 Forbidden，错误码：`CSRF_TOKEN_MISMATCH`

### Token 轮换

- 每次刷新令牌时同时轮换 CSRF Token
- 注销时同时清除 CSRF Token

## 验证结果

- [x] CSRF 方案已定义
- [x] 所有 Cookie 写请求具有明确 CSRF 防护

## 下一步

- **R1-20**：修正登录响应

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
