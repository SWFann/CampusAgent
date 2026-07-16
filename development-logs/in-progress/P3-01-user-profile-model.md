---
task_id: P3-01
task_name: 设计 User/StudentProfile 模型与迁移
status: in_review
started_at: 2026-07-16T20:00:00+08:00
completed_at: 2026-07-16T20:30:00+08:00
actual_hours: 0.5
owner: Claude
auditor: Codex
---

# P3-01 开发日志：设计 User/StudentProfile 模型与迁移

## 1. 背景

P3-01 是 P3 阶段的基础任务，建立身份与用户资料的数据库模型、Repository 基线和 Alembic 迁移。需要创建 `User`、`StudentProfile`、`AuthSession`、`RefreshToken` 四个 ORM 模型和对应的数据库迁移。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/users/models.py` | 重写 | User、StudentProfile ORM 模型 |
| `apps/api/src/modules/auth/models.py` | 重写 | AuthSession、RefreshToken ORM 模型 |
| `apps/api/src/modules/users/schemas.py` | 重写 | UserPublicRead、UserSelfRead、StudentProfileRead、UserProfileUpdate |
| `apps/api/src/modules/users/repository.py` | 重写 | UserRepository、StudentProfileRepository |
| `apps/api/alembic/versions/0002_user_auth_tables.py` | 新增 | 创建四张业务表的迁移 |
| `apps/api/tests/unit/test_user_models.py` | 新增 | User 和 StudentProfile 模型测试 |
| `apps/api/tests/unit/test_auth_models.py` | 新增 | AuthSession 和 RefreshToken 模型测试 |
| `apps/api/tests/unit/test_alembic.py` | 修改 | 更新迁移测试以反映新的业务表 |
| `apps/api/tests/conftest.py` | 修改 | 导入 ORM 模型以便 Base.metadata.create_all 注册 |

## 3. 设计说明

### 3.1 User 模型

- **表名**: `users`
- **主键**: UUID v4（通过 `new_uuid()` 生成）
- **唯一约束**: `email`（唯一，存储为 lowercase normalised）
- **状态字段**: `global_role`（默认 STUDENT）、`status`（默认 ACTIVE）
- **软删除**: `deleted_at`（nullable，支持软删除而不破坏外键）
- **时间戳**: `created_at`、`updated_at`（UTC timezone-aware）

### 3.2 StudentProfile 模型

- **表名**: `student_profiles`
- **主键**: UUID v4
- **唯一约束**: `user_id`（一对一与 User）、`student_no`（唯一学号）
- **可选字段**: `enrollment_year`、`major_name`、`bio`
- **可见性**: `profile_visibility`（默认 PUBLIC）

### 3.3 AuthSession 模型

- **表名**: `auth_sessions`
- **主键**: UUID v4
- **外键**: `user_id` → `users.id`
- **索引**: `user_id`、`family_id`
- **状态**: `status`（ACTIVE/REVOKED/COMPROMISED）
- **会话版本**: `session_version`（默认 1，刷新时递增）

### 3.4 RefreshToken 模型

- **表名**: `refresh_tokens`
- **主键**: UUID v4
- **外键**: `session_id` → `auth_sessions.id`、`user_id` → `users.id`
- **唯一约束**: `jti_hash`（SHA-256 of JWT jti claim，不存原始 token）
- **索引**: `user_id`、`family_id`、`jti_hash`（唯一）
- **状态**: `status`（ACTIVE/USED/REVOKED）
- **安全**: `__repr__` 不泄露 `jti_hash` 值

### 3.5 迁移设计

- 迁移文件 `0002_user_auth_tables.py` 创建四张表和所有索引
- 使用 `server_default` 设置默认值（迁移级别的默认值）
- 降级按依赖逆序删除表和索引
- 在 SQLite 测试库验证 upgrade/downgrade 可回放

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_create_user_success` | 创建 User 成功 |
| `test_user_defaults` | 默认值验证 |
| `test_user_repr_does_not_leak_password` | repr 不泄露密码 |
| `test_duplicate_email_fails` | 重复 email 失败 |
| `test_create_student_profile_success` | 创建 StudentProfile 成功 |
| `test_duplicate_student_no_fails` | 重复学号失败 |
| `test_one_to_one_constraint` | 一对一约束 |
| `test_deleted_at_field_exists` | 软删除字段存在 |
| `test_status_can_be_set_to_deleted` | 可设置 DELETED 状态 |
| `test_create_session_success` | 创建 AuthSession 成功 |
| `test_family_id_is_queryable` | family_id 可查询 |
| `test_session_version_defaults_to_1` | 版本号默认 1 |
| `test_create_refresh_token_success` | 创建 RefreshToken 成功 |
| `test_jti_hash_unique` | jti_hash 唯一约束 |
| `test_refresh_token_does_not_store_raw_token` | 不存原始 token |
| `test_repr_does_not_leak_jti` | repr 不泄露 jti |
| `test_session_has_refresh_tokens` | 关系测试 |
| `test_token_links_back_to_session` | 反向关系测试 |
| `test_business_tables_exist_after_upgrade` | 迁移后表存在 |
| `test_downgrade_base_clears_version` | 降级清除表 |
| `test_upgrade_then_downgrade_then_upgrade` | 循环测试 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent ruff check src/modules/users/ src/modules/auth/models.py ... --no-cache
# All checks passed!

conda run -n CampusAgent mypy src/modules/users/models.py src/modules/auth/models.py ... --no-incremental
# Success: no issues found in 4 source files

conda run -n CampusAgent python -m pytest tests/unit/test_user_models.py tests/unit/test_auth_models.py tests/unit/test_alembic.py -v
# 31 passed in 1.58s
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证（Docker 在本环境不可用）
- 未执行完整 `pip check`（在后续 P3 验证中统一执行）

## 7. 边界声明

- 未执行 P4+（组织、消息、Agent 等）
- 未修改 P0/P1 冻结契约（API_CONTRACT.md、WEBSOCKET_CONTRACT.md 等）
- 未实现 Agent/Organization/Conversation/Memory
- 未引入真实密钥
- 未提交、未推送
