---
task_id: R1-16
status: in_progress
stage: R1
title: 建立请求响应模型
started_at: 2026-07-14T13:00:00+09:00
completed_at:
estimated_hours: 2
actual_hours:
---

# R1-16：建立请求响应模型

## 目标

制定统一的请求和响应格式规范，确保所有 API 端点遵循相同的信封格式。

**来自整改计划**：R1-16 - 建立请求响应模型

**产物**：
- 统一响应规范
- 统一请求规范

**依赖**：R1-15（路径变量已统一 ✅）

## 验收标准

- [ ] 定义标准响应信封
- [ ] 定义标准错误响应格式
- [ ] 定义分页响应格式
- [ ] 所有现有端点遵循该规范

## 统一响应规范

### 标准响应信封

```json
{
  "success": true,
  "data": {
    // 响应数据（对象或数组）
  },
  "request_id": "uuid-v4",
  "timestamp": "2026-07-14T12:00:00Z"
}
```

### 标准错误响应

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // 可选：详细错误信息
    }
  },
  "request_id": "uuid-v4",
  "timestamp": "2026-07-14T12:00:00Z"
}
```

### 分页响应

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "cursor": "next_cursor_token",
    "has_more": true,
    "limit": 20
  },
  "request_id": "uuid-v4",
  "timestamp": "2026-07-14T12:00:00Z"
}
```

## 统一请求规范

### 请求头

```
Content-Type: application/json
X-Correlation-ID: uuid-v4（可选）
Authorization: Bearer <access_token>
```

### 请求体

- 所有请求体使用 JSON 格式
- 字段名使用 snake_case
- 日期时间使用 ISO 8601 格式：`2026-07-14T12:00:00Z`
- 敏感字段需加密（password, private_config 等）

### 查询参数

- 分页：`?cursor=xxx&limit=20`
- 过滤：`?status=active&role=student`
- 排序：`?sort_by=created_at&order=desc`

## HTTP 状态码使用规范

| 状态码 | 用途 |
|-------|------|
| 200 OK | 成功（GET, PUT, PATCH） |
| 201 Created | 创建成功（POST） |
| 204 No Content | 删除成功（DELETE） |
| 400 Bad Request | 请求参数错误 |
| 401 Unauthorized | 未认证 |
| 403 Forbidden | 无权限 |
| 404 Not Found | 资源不存在 |
| 409 Conflict | 资源冲突（重复注册等） |
| 422 Unprocessable Entity | 验证失败 |
| 429 Too Many Requests | 速率限制 |
| 500 Internal Server Error | 服务器错误 |

## 下一步

- **R1-17**：建立验证规则

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
