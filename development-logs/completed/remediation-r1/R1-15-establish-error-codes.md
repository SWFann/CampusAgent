---
task_id: R1-15
status: in_progress
stage: R1
title: 补全错误码规范
started_at: 2026-07-14T13:02:00+09:00
completed_at:
estimated_hours: 1
actual_hours:
---

# R1-15：补全错误码规范

## 目标

为每个模块定义稳定的错误码，避免依赖自由文本判断错误。

**来自整改计划**：R1-15 - 补全错误码

**产物**：
- 错误码规范文档

**依赖**：R1-06 至 R1-14（端点清单和补全已完成 ✅）

## 验收标准

- [ ] 每个模块有稳定的错误码
- [ ] 错误码格式统一
- [ ] 错误码文档完整

## 错误码规范

### 错误码格式

```
{module}_{error_type}_{sequence}
```

**示例**：
- `AUTH_INVALID_TOKEN` - 认证模块：无效令牌
- `SCENE_INVALID_STATE` - 场景模块：无效状态
- `USER_NOT_FOUND` - 用户模块：用户不存在

### 认证模块错误码

| 错误码 | HTTP 状态码 | 描述 |
|-------|-----------|------|
| `AUTH_INVALID_TOKEN` | 401 | 访问令牌无效或过期 |
| `AUTH_EXPIRED_TOKEN` | 401 | 刷新令牌已过期 |
| `AUTH_REVOKED_TOKEN` | 401 | 令牌已被撤销 |
| `AUTH_INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 |
| `AUTH_USER_NOT_FOUND` | 404 | 用户不存在 |
| `AUTH_USER_ALREADY_EXISTS` | 409 | 用户已存在 |

### 组织模块错误码

| 错误码 | HTTP 状态码 | 描述 |
|-------|-----------|------|
| `ORG_NOT_FOUND` | 404 | 组织不存在 |
| `ORG_ALREADY_EXISTS` | 409 | 组织名称已存在 |
| `ORG_USER_ALREADY_MEMBER` | 409 | 用户已是成员 |
| `ORG_USER_NOT_MEMBER` | 403 | 用户不是成员 |
| `ORG_INSUFFICIENT_PERMISSIONS` | 403 | 权限不足 |

### 场景模块错误码

| 错误码 | HTTP 状态码 | 描述 |
|-------|-----------|------|
| `SCENE_NOT_FOUND` | 404 | 场景不存在 |
| `SCENE_INVALID_STATE` | 400 | 场景状态不合法 |
| `SCENE_NOT_AUTHORIZED` | 403 | 用户未授权 |
| `SCENE_PRIVATE_SUBMISSION_EXPIRED` | 400 | 私有提交已过期 |
| `SCENE_VOTING_ENDED` | 400 | 投票已结束 |

### 记忆模块错误码

| 错误码 | HTTP 状态码 | 描述 |
|-------|-----------|------|
| `MEMORY_NOT_FOUND` | 404 | 记忆不存在 |
| `MEMORY_ACCESS_DENIED` | 403 | 无权访问 |
| `MEMORY_CONSENT_REQUIRED` | 403 | 需要授权 |
| `MEMORY_ENCRYPTION_FAILED` | 500 | 加密失败 |

### 通用错误码

| 错误码 | HTTP 状态码 | 描述 |
|-------|-----------|------|
| `VALIDATION_ERROR` | 422 | 请求验证失败 |
| `RATE_LIMIT_EXCEEDED` | 429 | 速率限制 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 验证结果

- [ ] 检查所有模块的错误码定义

## 下一步

- **R1-16**：补全幂等规则

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
