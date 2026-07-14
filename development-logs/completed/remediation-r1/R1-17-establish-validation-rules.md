---
task_id: R1-17
status: in_progress
stage: R1
title: 建立验证规则
started_at: 2026-07-14T13:01:00+09:00
completed_at:
estimated_hours: 1.5
actual_hours:
---

# R1-17：建立验证规则

## 目标

建立统一的请求验证规则，包括必填字段、格式验证和业务规则验证。

**来自整改计划**：R1-17 - 建立验证规则

**产物**：
- 验证规则规范

**依赖**：R1-16（请求响应模型已建立 ✅）

## 验收标准

- [ ] 定义必填字段验证规则
- [ ] 定义格式验证规则
- [ ] 定义业务规则验证
- [ ] 建立验证错误响应格式

## 验证规则规范

### 必填字段验证

```python
# 示例：创建组织请求
class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    type: str = Field(..., pattern="^(school|college|class|dorm|club|course)$")
    description: Optional[str] = Field(None, max_length=500)
```

### 格式验证

| 字段类型 | 验证规则 | 示例 |
|---------|---------|------|
| 邮箱 | email 格式 | `user@example.edu.cn` |
| 手机号 | E.164 格式 | `+8613800138000` |
| UUID | UUID v4 格式 | `550e8400-e29b-41d4-a716-446655440000` |
| 日期时间 | ISO 8601 | `2026-07-14T12:00:00Z` |
| URL | HTTP/HTTPS | `https://example.com` |
| 枚举 | 白名单 | `student`, `teacher`, `counselor` |

### 业务规则验证

1. **唯一性验证**
   - 邮箱必须唯一
   - 学号必须唯一
   - 组织名称在同一父组织下必须唯一

2. **权限验证**
   - 用户只能修改自己的资料（除非是管理员）
   - 只有组织所有者可以删除组织
   - 只有场景创建者可以取消场景

3. **状态流转验证**
   - draft → published → running → voting → completed
   - 任何状态可 → cancelled
   - 禁止逆序流转

4. **关联存在性验证**
   - 创建成员时必须验证组织存在
   - 发送消息时必须验证会话存在
   - 投票时必须验证候选者存在

### 验证错误响应

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "code": "invalid_format",
        "message": "Invalid email format"
      },
      {
        "field": "name",
        "code": "too_short",
        "message": "Name must be at least 2 characters"
      }
    ]
  },
  "request_id": "uuid-v4",
  "timestamp": "2026-07-14T12:00:00Z"
}
```

## Pydantic 验证模型示例

```python
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional
from datetime import datetime

class CreateUserRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    global_role: str = Field(..., pattern="^(student|teacher|counselor|org_admin|school_admin|system_admin)$")

    @validator("password")
    def validate_password(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isalpha() for char in v):
            raise ValueError("Password must contain at least one letter")
        return v
```

## 下一步

- **R1-B 完成**：更新 API_CONTRACT.md（R1-17）
- **R1-C**：开始统一认证与实时合同

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
