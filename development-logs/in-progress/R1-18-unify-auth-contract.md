---
task_id: R1-18
status: in_progress
stage: R1
title: 统一认证合同
started_at: 2026-07-14T13:05:00+09:00
completed_at:
estimated_hours: 1
actual_hours:
---

# R1-18：统一认证合同

## 目标

冻结浏览器认证方式，依据 ADR-003 统一为 HttpOnly Cookie 或明确替代方案。

**来自整改计划**：R1-18 - 统一认证合同

**产物**：
- 认证合同规范

**依赖**：R1-17（R1-B 完成 ✅）

## 验收标准

- [ ] HTTP 契约与 ADR-003 一致
- [ ] 认证方式明确（HttpOnly Cookie + Refresh Token）
- [ ] 所有认证端点文档更新

## ADR-003 摘要

**决策**：JWT + HttpOnly Cookie

**Access Token**：
- 有效期：1 小时
- 存储：内存（不持久化）
- 传输：Authorization Header

**Refresh Token**：
- 有效期：7 天
- 存储：HttpOnly Secure Cookie
- 特性：单次使用、每次刷新轮换、注销撤销

## 认证流程

### 登录流程

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

### 刷新令牌

```http
POST /api/v1/auth/refresh
Cookie: refresh_token=xxx

→ 200 OK
Set-Cookie: refresh_token=yyy; HttpOnly; Secure; SameSite=Strict; Max-Age=604800

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 注销

```http
POST /api/v1/auth/logout
Cookie: refresh_token=xxx

→ 204 No Content
Set-Cookie: refresh_token=; Max-Age=0
```

## Cookie 规范

| 属性 | 值 | 说明 |
|------|-----|------|
| Name | `refresh_token` | Cookie 名称 |
| HttpOnly | `true` | 禁止 JavaScript 访问 |
| Secure | `true` | 仅 HTTPS 传输 |
| SameSite | `Strict` | 防 CSRF |
| Max-Age | `604800` | 7 天（秒） |
| Path | `/api/v1/auth/refresh` | 仅发送到刷新端点 |

## 验证结果

- [ ] 确认 API_CONTRACT.md 与 ADR-003 一致

## 下一步

- **R1-19**：定义 CSRF 方案

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
