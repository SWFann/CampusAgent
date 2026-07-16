---
task_id: P3-03
task_name: 实现注册 API
status: in_review
started_at: 2026-07-16T20:50:00+08:00
completed_at: 2026-07-16T21:30:00+08:00
actual_hours: 0.67
owner: Claude
auditor: Codex
---

# P3-03 开发日志：实现注册 API

## 1. 背景

P3-03 实现 `POST /api/v1/auth/register`，创建 User + StudentProfile + AuthSession + RefreshToken，成功后自动登录并设置 Cookie。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/auth/tokens.py` | 新增 | JWT token 创建和验证 |
| `apps/api/src/modules/auth/cookies.py` | 新增 | Cookie 设置和清除 |
| `apps/api/src/modules/auth/schemas.py` | 重写 | RegisterRequest、LoginRequest、UserRead、RefreshResponse |
| `apps/api/src/modules/auth/service.py` | 重写 | register_user、login_user、refresh_token_rotation、logout_user |
| `apps/api/src/modules/auth/api.py` | 重写 | 注册、登录、刷新、注销端点 |
| `apps/api/src/main.py` | 修改 | 注册 auth router |
| `apps/api/tests/conftest.py` | 修改 | 添加 db_client fixture、导入 TestClient |
| `apps/api/tests/unit/test_auth_register.py` | 新增 | 14 个注册测试 |
| `apps/api/requirements.txt` | 修改 | pydantic[email] |

## 3. 设计说明

### 3.1 Token 模块

- Access Token: sub(user_id), typ("access"), role, iat, exp, jti
- Refresh Token: sub(user_id), typ("refresh"), family_id, session_id, iat, exp, jti
- 签名密钥: settings.APP_SECRET
- jti_hash: SHA-256(jti)，不入库存原始 token

### 3.2 Cookie 模块

- access_token: HttpOnly, SameSite=Lax, Path=/api/v1, Max-Age=3600
- refresh_token: HttpOnly, SameSite=Lax, Path=/api/v1/auth, Max-Age=604800
- csrf_token: non-HttpOnly, SameSite=Lax, Path=/, Max-Age=604800
- Secure: 生产 true，开发/测试 false

### 3.3 注册流程

1. 邮箱 normalize 为 lowercase
2. 密码强度校验
3. 邮箱和学号唯一性检查
4. 创建 User、StudentProfile
5. 创建 AuthSession（family_id）
6. 创建 RefreshToken（jti_hash 入库）
7. 提交事务
8. 生成 access_token 和 csrf_token
9. 设置三类 Cookie
10. 响应体返回用户公开字段（不含 token）

### 3.4 同时实现的端点

P3-03 同时实现了登录(P3-04)、刷新(P3-05)、注销(P3-05)的服务层和 API端点，因为它们共享 tokens/cookies/service 模块。各任务测试在各自阶段补充。

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_register_returns_201` | 注册返回 201 |
| `test_register_response_has_user_fields` | 响应包含用户字段 |
| `test_register_response_no_tokens` | 响应不含 token |
| `test_register_sets_three_cookies` | 设置三个 Cookie |
| `test_access_token_cookie_attributes` | access_token Cookie 属性 |
| `test_refresh_token_cookie_attributes` | refresh_token Cookie 属性 |
| `test_csrf_cookie_attributes` | csrf_token Cookie 属性 |
| `test_duplicate_email_returns_409` | 重复邮箱 409 |
| `test_duplicate_student_no_returns_409` | 重复学号 409 |
| `test_weak_password_returns_400` | 弱密码 400 |
| `test_no_digit_returns_400` | 无数字 400 |
| `test_weak_password_no_leak` | 弱密码不泄露明文 |
| `test_register_no_csrf_header_required` | 注册豁免 CSRF |
| `test_email_lowercased` | 邮箱小写化 |

## 5. 自检命令和结果

```bash
ruff check ...  # All checks passed!
mypy ...         # Success: no issues found
pytest ...       # 14 passed
```

## 6. 边界声明

- 未执行 P4+
- 未修改 P0/P1 冻结契约
- 未实现 Agent/Organization/Conversation/Memory
- 未提交、未推送
