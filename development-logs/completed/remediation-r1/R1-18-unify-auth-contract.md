---
task_id: R1-18
status: completed
stage: R1
title: 统一认证合同
completed_at: 2026-07-14T13:06:00+09:00
estimated_hours: 1
actual_hours: 0.15
---

# R1-18：统一认证合同

## 完成状态

✅ **认证合同已统一**

**完成时间**：2026-07-14T13:06:00+09:00

## 目标

冻结浏览器认证方式，依据 ADR-003 统一为 HttpOnly Cookie + JWT。

**来自整改计划**：R1-18 - 统一认证合同

## 认证方案（依据 ADR-003）

### Access Token
- **存储**：内存（不持久化）
- **传输**：Authorization Header
- **有效期**：1 小时

### Refresh Token
- **存储**：HttpOnly Secure Cookie
- **有效期**：7 天
- **特性**：单次使用、每次刷新轮换

### Cookie 规范

| 属性 | 值 |
|------|-----|
| HttpOnly | true |
| Secure | true |
| SameSite | Strict |
| Max-Age | 604800（7天） |
| Path | `/api/v1/auth/refresh` |

## 验证结果

- [x] HTTP 契约与 ADR-003 一致
- [x] 认证方式明确（HttpOnly Cookie + Refresh Token）

## 下一步

- **R1-19**：定义 CSRF 方案

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
