---
task_id: P3-02
task_name: 实现密码安全
status: in_review
started_at: 2026-07-16T20:30:00+08:00
completed_at: 2026-07-16T20:50:00+08:00
actual_hours: 0.33
owner: Claude
auditor: Codex
---

# P3-02 开发日志：实现密码安全

## 1. 背景

P3-02 实现密码哈希、校验、强度检查和统一错误处理。使用 bcrypt 库进行密码哈希，实现 `hash_password`、`verify_password` 和 `validate_password_strength` 三个核心函数。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/requirements.txt` | 修改 | 添加 bcrypt>=4.0.0 和 PyJWT>=2.8.0 |
| `apps/api/requirements.lock` | 新增 | 锁定 bcrypt==5.0.0 和 PyJWT==2.13.0 |
| `apps/api/src/modules/auth/passwords.py` | 重写 | hash_password、verify_password、validate_password_strength |
| `apps/api/src/modules/auth/exceptions.py` | 重写 | Auth 模块完整异常类（WeakPassword、InvalidCredentials 等） |
| `apps/api/src/utils/errors.py` | 修改 | 修复 dict 类型标注为 dict[str, Any]（mypy strict） |
| `apps/api/tests/unit/test_auth_passwords.py` | 新增 | 18 个密码安全测试 |

## 3. 设计说明

### 3.1 密码哈希

- 使用 `bcrypt` 库（行业标准，自适应成本因子）
- `hash_password(password: str) -> str`：生成带随机盐的 bcrypt 哈希
- `verify_password(password: str, password_hash: str) -> bool`：验证密码，不区分失败原因
- 相同密码多次哈希产生不同结果（盐生效）

### 3.2 密码强度规则

- 长度至少 8 个字符
- 至少包含一个字母和一个数字
- 不能全为空白字符
- 不能包含邮箱本地部分（@ 之前部分，长度≥3）
- 不能包含学号（长度≥3）

### 3.3 异常设计

- `WeakPasswordError`：AUTH_WEAK_PASSWORD，HTTP 400
- `InvalidCredentialsError`：AUTH_INVALID_CREDENTIALS，HTTP 401（不区分用户不存在和密码错误）
- `InvalidTokenError`：AUTH_INVALID_TOKEN，HTTP 401
- `RefreshTokenRevokedError`：AUTH_REFRESH_TOKEN_REVOKED，HTTP 401
- `RefreshTokenExpiredError`：AUTH_REFRESH_TOKEN_EXPIRED，HTTP 401
- `UserAlreadyExistsError`：USER_ALREADY_EXISTS，HTTP 409
- `CsrfTokenMissingError`：CSRF_TOKEN_MISSING，HTTP 403
- `CsrfTokenMismatchError`：CSRF_TOKEN_MISMATCH，HTTP 403
- `AccountDisabledError`：使用 AUTH_INVALID_CREDENTIALS 码（不泄露禁用状态），HTTP 401

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_hash_is_not_plaintext` | 哈希不等于明文 |
| `test_same_password_different_hashes` | 相同密码不同哈希（盐） |
| `test_hash_starts_with_bcrypt_prefix` | 哈希前缀验证 |
| `test_correct_password_verifies` | 正确密码验证通过 |
| `test_wrong_password_fails` | 错误密码验证失败 |
| `test_empty_password_fails` | 空密码失败 |
| `test_malformed_hash_returns_false` | 畸形哈希返回 False |
| `test_none_password_returns_false` | None 密码返回 False |
| `test_strong_password_passes` | 强密码通过 |
| `test_short_password_fails` | 短密码失败 |
| `test_pure_letters_fails` | 纯字母失败 |
| `test_pure_digits_fails` | 纯数字失败 |
| `test_all_whitespace_fails` | 全空白失败 |
| `test_contains_email_local_part_fails` | 包含邮箱本地部分失败 |
| `test_contains_student_no_fails` | 包含学号失败 |
| `test_no_email_or_student_no_is_ok` | 无上下文时跳过检查 |
| `test_error_does_not_leak_password` | 错误不泄露明文 |
| `test_error_code_is_auth_weak_password` | 错误码正确 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent ruff check src/modules/auth/ src/utils/errors.py ... --no-cache
# All checks passed!

conda run -n CampusAgent mypy src/modules/auth/passwords.py src/modules/auth/exceptions.py ... --no-incremental
# Success: no issues found in 3 source files

conda run -n CampusAgent python -m pytest tests/unit/test_auth_passwords.py -v
# 18 passed in 2.27s
```

## 6. 未执行项及原因

无

## 7. 边界声明

- 未执行 P4+
- 未修改 P0/P1 冻结契约
- 未实现 Agent/Organization/Conversation/Memory
- 未引入真实密钥
- 未提交、未推送
