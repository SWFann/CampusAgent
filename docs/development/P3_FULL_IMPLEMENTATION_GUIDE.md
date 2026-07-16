# P3 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P3「身份、用户与会话安全」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P3-01～P3-12；不得跳任务、不得执行 P4+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。

## 0. 项目背景

项目名称：CampusAgent

项目定位：隐私优先、智能体原生的校园平台。系统面向校园组织、师生、社团、活动与多智能体协作场景，核心能力包括 Conversation、Agent、Memory、Scene、Model Gateway、Admin、Edge Node、WebSocket 实时事件和隐私测试矩阵。

项目路径：

```text
/root/CampusAgent
```

远程仓库：

```text
git@github.com:SWFann/CampusAgent.git
```

当前分支：

```text
main
```

当前基准提交：

```text
1d5af9d test(api): isolate readiness checks from CI services
```

P2 收口提交：

```text
0a7a2d3 feat(infra): complete P2 backend foundation
1d5af9d test(api): isolate readiness checks from CI services
```

P2 远端 CI：

```text
https://github.com/SWFann/CampusAgent/actions/runs/29500458558
```

P2 CI 状态：

- `Lint, Typecheck & Test`: success
- `E2E Tests (Playwright)`: success

当前环境：

- 后续开发统一以 `/root/CampusAgent` 为准。
- Python 环境优先使用 conda 环境 `CampusAgent`。
- Docker 在本机 WSL 内可能不可用；如果 `docker command not found`，记录原因，但不要跳过非 Docker 验证。
- `gh` CLI 可能不可用；远端 CI 可用 GitHub API 或浏览器观察。

## 1. 当前权威状态

P0/P1 权威口径：

- HTTP API 契约：`v1.0-frozen`
- HTTP API 端点：68 个 MVP + 3 个 internal = 71 个总文档化端点
- WebSocket 契约：`v1.0-frozen`
- 威胁模型：T-01～T-09，共 9 个威胁
- 风险分布：严重 1 / 高 6 / 中 2 / 低 0
- 控制状态：`planned=9 / implemented=0 / verified=0`
- 隐私测试：`defined=100 / not_run=100`

P2 已完成：

- Docker Compose 基线
- Settings 配置对象
- PostgreSQL engine/session
- Alembic 基线迁移
- Redis 客户端
- API Envelope
- 请求上下文中间件
- 敏感日志过滤
- Clock/UUID 工具
- 领域事件总线
- Repository / Unit of Work 基线
- 测试数据库夹具
- OpenAPI 基线
- 基础可观测性

P3 当前状态：

- P3-01～P3-12 尚未执行。
- `apps/api/src/modules/auth/*` 和 `apps/api/src/modules/users/*` 目前主要是骨架。
- 前端目前只有基础页面和健康页；P3-12 才允许实现登录/注册页面。

## 2. 必读文件

开始前必须阅读：

1. `docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md`
2. `docs/project/README.md`
3. `docs/development/DEVELOPMENT_PLAN.md`
4. `docs/development/P2_FULL_IMPLEMENTATION_GUIDE.md`
5. `development-logs/in-progress/P2-COMPLETION-REPORT.md`
6. `docs/api/API_CONTRACT.md`
7. `docs/api/WEBSOCKET_CONTRACT.md`
8. `docs/domain/DOMAIN_VOCABULARY.md`
9. `docs/decisions/0003-authentication.md`
10. `docs/privacy/PRIVACY_TEST_MATRIX.md`
11. `docs/security/THREAT_MODEL.md`
12. `apps/api/src/config.py`
13. `apps/api/src/main.py`
14. `apps/api/src/dependencies.py`
15. `apps/api/src/db/base.py`
16. `apps/api/src/db/session.py`
17. `apps/api/src/db/repositories.py`
18. `apps/api/src/events/bus.py`
19. `apps/api/src/schemas/envelope.py`
20. `apps/api/src/utils/redaction.py`
21. `apps/api/tests/conftest.py`

阅读后先确认：

```bash
cd /root/CampusAgent
git status --short --branch
git log -3 --oneline
```

预期：

- 当前分支为 `main`
- 工作树干净
- 最新提交为 `1d5af9d test(api): isolate readiness checks from CI services`

如果工作树不干净，先停止并报告，不要覆盖用户或 Codex 的改动。

## 3. P3 总目标

P3 阶段名称：身份、用户与会话安全。

P3 总目标：

- 建立 `User` / `StudentProfile` / `AuthSession` / `RefreshToken` 数据模型和迁移。
- 实现密码哈希、密码强度校验和统一认证失败响应。
- 实现注册、登录、刷新、注销、当前用户和资料读写 API。
- 使用 JWT + HttpOnly Cookie，严格遵守 API 契约。
- 实现 CSRF double-submit cookie 机制。
- 实现 refresh token 轮换、重放检测和 token family 撤销。
- 实现禁用账号拒绝访问。
- 实现基础 Auth 限流，不泄露账号是否存在。
- 发布 `UserRegistered` 领域事件，但不实现 Agent 业务。
- 完成登录/注册前端页面和基础登录状态处理。

P3 完成后必须满足：

- 注册成功后自动登录，响应体不包含 access_token 或 refresh_token。
- 登录成功后只通过 `Set-Cookie` 发放 `access_token`、`refresh_token`、`csrf_token`。
- `access_token` / `refresh_token` 均为 HttpOnly Cookie。
- `csrf_token` 为非 HttpOnly Cookie，供前端读取并放入 `X-CSRF-Token`。
- `POST /api/v1/auth/refresh` 和 `POST /api/v1/auth/logout` 必须强制 CSRF。
- `POST /api/v1/auth/register` 和 `POST /api/v1/auth/login` 豁免 CSRF。
- Bearer token 内部调用可豁免 CSRF，但 P3 不需要实现完整内部服务权限系统。
- 密码不得明文存储、不得写入日志、不得出现在测试快照中。
- 登录失败不泄露账号是否存在。
- refresh token 重放必须失败关闭并撤销 token family。
- 禁用用户不得继续访问 `/auth/me` 或资料写接口。
- P3 不得实现 P4 组织业务、P5 消息、P6 Agent/Memory、P7 真实模型网关。

## 4. P3 技术决策

### 4.1 认证方式

以 `docs/decisions/0003-authentication.md` 和 `docs/api/API_CONTRACT.md` 为准：

- JWT + HttpOnly Cookie。
- Access Token 有效期 1 小时。
- Refresh Token 有效期 7 天。
- Refresh Token 单次使用，刷新时轮换。
- CSRF 使用 double-submit cookie。

### 4.2 密码哈希

优先使用 `passlib[bcrypt]` 或 `bcrypt`。执行方必须：

- 将依赖加入 `apps/api/requirements.txt`。
- 将锁定版本加入 `apps/api/requirements.lock`。
- 在 conda 环境安装并验证。
- 不使用自写哈希算法。

推荐实现：

- `apps/api/src/modules/auth/passwords.py`
- `hash_password(password: str) -> str`
- `verify_password(password: str, password_hash: str) -> bool`
- `validate_password_strength(password: str) -> None`

密码强度 MVP 规则：

- 长度至少 8。
- 至少包含字母和数字。
- 不允许全空白。
- 不允许包含邮箱本地部分或学号。

### 4.3 JWT 与 Token 存储

推荐使用 `PyJWT`。

新增依赖：

- `PyJWT`

推荐实现：

- `apps/api/src/modules/auth/tokens.py`
- `create_access_token(...)`
- `create_refresh_token(...)`
- `decode_token(...)`
- `TokenType.ACCESS`
- `TokenType.REFRESH`

Token claims 最小集合：

Access Token：

- `sub`: user_id
- `typ`: `access`
- `role`: global_role
- `iat`
- `exp`
- `jti`

Refresh Token：

- `sub`: user_id
- `typ`: `refresh`
- `family_id`
- `session_id`
- `iat`
- `exp`
- `jti`

禁止：

- 不把密码、邮箱验证码、csrf token、完整用户资料写入 JWT。
- 不把 JWT 原文写入日志。

### 4.4 Cookie 属性

必须与契约一致：

`access_token`：

- HttpOnly: true
- Secure: production true；development/test 可 false 以便本地测试
- SameSite: Lax
- Path: `/api/v1`
- Max-Age: 3600

`refresh_token`：

- HttpOnly: true
- Secure: production true；development/test 可 false
- SameSite: Lax
- Path: `/api/v1/auth`
- Max-Age: 604800

`csrf_token`：

- HttpOnly: false
- Secure: production true；development/test 可 false
- SameSite: Lax
- Path: `/`
- Max-Age: 604800

Cookie helper 建议放在：

- `apps/api/src/modules/auth/cookies.py`

### 4.5 CSRF

CSRF 只保护 Cookie 已认证的浏览器写请求。

P3 必须实现：

- `csrf_token` Cookie 生成。
- `X-CSRF-Token` 与 `csrf_token` Cookie 比对。
- register/login 豁免。
- refresh/logout 强制。
- 后续 P4+ 写接口可复用同一 dependency/middleware。

推荐实现：

- `apps/api/src/modules/auth/csrf.py`
- `generate_csrf_token()`
- `validate_csrf(request: Request) -> None`
- `require_csrf(request: Request) -> None`

错误码：

- `CSRF_TOKEN_MISSING`
- `CSRF_TOKEN_MISMATCH`

`CSRF_TOKEN_EXPIRED` 是可选增强，不要为了追求完整性扩大范围。

### 4.6 数据模型

推荐模型：

`User`：

- `id`: UUID primary key
- `email`: unique, lowercase normalized
- `password_hash`: string
- `display_name`: string
- `avatar_url`: nullable string
- `global_role`: enum/string, default `STUDENT`
- `status`: enum/string, default `ACTIVE`
- `created_at`
- `updated_at`
- `deleted_at`: nullable

`StudentProfile`：

- `id`: UUID primary key
- `user_id`: FK users.id, unique
- `student_no`: unique
- `enrollment_year`: nullable int
- `major_name`: nullable string
- `bio`: nullable string
- `profile_visibility`: enum/string, default `PUBLIC`
- `created_at`
- `updated_at`

`AuthSession`：

- `id`: UUID primary key
- `user_id`: FK users.id
- `family_id`: UUID/string, indexed
- `session_version`: int, default 1
- `status`: `ACTIVE` / `REVOKED` / `COMPROMISED`
- `created_at`
- `updated_at`
- `expires_at`
- `revoked_at`

`RefreshToken`：

- `id`: UUID primary key
- `session_id`: FK auth_sessions.id
- `user_id`: FK users.id
- `family_id`: indexed
- `jti_hash`: unique
- `status`: `ACTIVE` / `USED` / `REVOKED`
- `issued_at`
- `expires_at`
- `used_at`
- `revoked_at`

注意：

- 不存 refresh token 原文，只存 `jti_hash`。
- 可以用 SHA-256 哈希 `jti`，但不要哈希整个 token 原文。
- P3 不需要建 OrganizationMembership。

### 4.7 前端策略

P3-12 只做基础登录/注册闭环：

- `/login`
- `/register`
- 当前用户状态请求 `/api/v1/auth/me`
- 登录/注册表单
- 错误态展示
- CSRF token 从 cookie 读取，用于后续写请求

禁止：

- 不做复杂 dashboard。
- 不做组织、聊天、场景、Agent 页面。
- 不在前端读取 access_token 或 refresh_token。

## 5. 执行顺序

必须按顺序执行：

1. P3-01 设计 User/StudentProfile
2. P3-02 实现密码安全
3. P3-03 实现注册
4. P3-04 实现登录
5. P3-05 实现刷新与注销
6. P3-06 实现当前用户上下文
7. P3-07 实现资料读写
8. P3-08 发布 UserRegistered
9. P3-09 账号删除流程
10. P3-10 Auth 限流
11. P3-11 完成认证测试
12. P3-12 完成登录注册页面

每个任务完成时必须：

- 新增或更新对应开发日志。
- 更新 `docs/development/DEVELOPMENT_PLAN.md` 中对应 P3 任务状态。
- 添加或更新测试。
- 跑任务相关测试。
- 不提交。
- 不推送。

如果某个任务阻塞：

- 停止后续任务。
- 写清阻塞原因。
- 不要通过删除测试绕过。

## 6. P3-01：设计 User/StudentProfile

目标：建立身份与用户资料的数据库模型、Repository 基线和 Alembic 迁移。

允许修改：

- `apps/api/src/modules/users/models.py`
- `apps/api/src/modules/users/schemas.py`
- `apps/api/src/modules/users/repository.py`
- `apps/api/src/modules/auth/models.py`
- `apps/api/alembic/versions/*.py`
- `apps/api/tests/unit/test_user_models.py`
- `apps/api/tests/unit/test_auth_models.py`
- `docs/development/DEVELOPMENT_PLAN.md`
- `development-logs/in-progress/P3-01-user-profile-model.md`

必须实现：

- User ORM。
- StudentProfile ORM。
- AuthSession ORM。
- RefreshToken ORM。
- 必要 enum 或常量。
- 邮箱唯一约束。
- 学号唯一约束。
- User 与 StudentProfile 一对一约束。
- AuthSession 与 RefreshToken 关联。
- Alembic 迁移，可 upgrade/downgrade。

建议表名：

- `users`
- `student_profiles`
- `auth_sessions`
- `refresh_tokens`

测试要求：

- 创建 User 成功。
- 创建 StudentProfile 成功。
- 同一 email 重复失败。
- 同一 student_no 重复失败。
- User 删除/软删除字段存在。
- AuthSession family_id 可查询。
- RefreshToken 不存 token 原文，只存 `jti_hash`。
- Alembic upgrade head / downgrade base 在 SQLite 测试库可回放。

禁止：

- 不实现注册 API。
- 不实现密码哈希。
- 不实现组织成员。
- 不实现 Agent 创建。

## 7. P3-02：实现密码安全

目标：实现密码哈希、校验、强度检查和统一错误。

允许修改：

- `apps/api/requirements.txt`
- `apps/api/requirements.lock`
- `apps/api/src/modules/auth/passwords.py`
- `apps/api/src/modules/auth/exceptions.py`
- `apps/api/src/schemas/envelope.py`（仅在确有必要补映射；不得破坏既有错误）
- `apps/api/tests/unit/test_auth_passwords.py`
- `development-logs/in-progress/P3-02-password-security.md`

必须实现：

- `hash_password(password: str) -> str`
- `verify_password(password: str, password_hash: str) -> bool`
- `validate_password_strength(password: str, *, email: str | None = None, student_no: str | None = None) -> None`
- 弱密码错误映射为 `AUTH_WEAK_PASSWORD`。
- 验证错误不包含明文密码。

测试要求：

- hash 结果不是明文。
- 同一密码多次 hash 结果不同（salt 生效）。
- 正确密码验证通过。
- 错误密码验证失败。
- 短密码失败。
- 纯字母或纯数字失败。
- 包含 email 本地部分失败。
- 包含 student_no 失败。
- 弱密码错误响应不泄露原始密码。

禁止：

- 不自写哈希算法。
- 不把密码写入日志。
- 不把密码存入测试快照。

## 8. P3-03：实现注册

目标：实现 `POST /api/v1/auth/register`，创建 User + StudentProfile + AuthSession + RefreshToken，成功后自动登录并发布待提交后的事件。

允许修改：

- `apps/api/src/modules/auth/api.py`
- `apps/api/src/modules/auth/service.py`
- `apps/api/src/modules/auth/schemas.py`
- `apps/api/src/modules/auth/cookies.py`
- `apps/api/src/modules/auth/tokens.py`
- `apps/api/src/modules/users/repository.py`
- `apps/api/src/main.py`
- `apps/api/tests/unit/test_auth_register.py`
- `development-logs/in-progress/P3-03-register.md`

必须实现：

- 请求 schema：email、password、display_name、student_no、organization_ids。
- `organization_ids` 在 P3 可接受但不创建成员关系；记录为暂不处理或忽略，不能报错。
- email normalize 为 lowercase。
- student_no 唯一。
- 注册成功返回 201。
- 响应体返回用户公开字段，不包含 token。
- 设置 access_token、refresh_token、csrf_token cookie。
- refresh token jti_hash 入库。
- 重复 email 或 student_no 返回 `USER_ALREADY_EXISTS`。
- 弱密码返回 `AUTH_WEAK_PASSWORD`。

测试要求：

- 成功注册创建 User。
- 成功注册创建 StudentProfile。
- 成功注册设置三类 Cookie。
- Cookie 属性符合契约。
- 响应体不含 access_token/refresh_token。
- 重复 email 返回 409。
- 重复 student_no 返回 409。
- 弱密码返回 400 或契约约定状态，并带 `AUTH_WEAK_PASSWORD`。
- register 豁免 CSRF。

禁止：

- 不实现组织加入。
- 不创建 Agent。
- 不把 token 返回 JSON body。

## 9. P3-04：实现登录

目标：实现 `POST /api/v1/auth/login`。

允许修改：

- `apps/api/src/modules/auth/api.py`
- `apps/api/src/modules/auth/service.py`
- `apps/api/src/modules/auth/schemas.py`
- `apps/api/src/modules/auth/tokens.py`
- `apps/api/src/modules/auth/cookies.py`
- `apps/api/tests/unit/test_auth_login.py`
- `development-logs/in-progress/P3-04-login.md`

必须实现：

- email + password 登录。
- 成功返回 200 和用户公开字段。
- 成功设置 access_token、refresh_token、csrf_token cookie。
- 错误邮箱和错误密码都返回 `AUTH_INVALID_CREDENTIALS`。
- 禁用/删除账号登录失败也返回统一认证错误，不泄露账号状态。
- 登录成功创建新的 AuthSession 和 RefreshToken。

测试要求：

- 正确凭据登录成功。
- 错误密码失败。
- 不存在邮箱失败。
- 错误密码与不存在邮箱响应形状一致。
- 禁用用户登录失败，不泄露 disabled。
- token 不在响应体中。
- login 豁免 CSRF。

## 10. P3-05：实现刷新与注销

目标：实现 `POST /api/v1/auth/refresh` 和 `POST /api/v1/auth/logout`。

允许修改：

- `apps/api/src/modules/auth/api.py`
- `apps/api/src/modules/auth/service.py`
- `apps/api/src/modules/auth/csrf.py`
- `apps/api/src/modules/auth/tokens.py`
- `apps/api/src/modules/auth/cookies.py`
- `apps/api/tests/unit/test_auth_refresh_logout.py`
- `development-logs/in-progress/P3-05-refresh-logout.md`

必须实现 refresh：

- 从 refresh_token Cookie 读取 token。
- 强制 CSRF。
- 校验 token 类型为 refresh。
- 校验 jti_hash 存在且 ACTIVE。
- 成功后旧 refresh token 标记 USED。
- 成功后创建新 refresh token。
- session_version +1。
- 重新设置 access_token 和 refresh_token cookie。
- 缺失/无效 token 返回 `AUTH_INVALID_TOKEN`。
- 过期返回 `AUTH_REFRESH_TOKEN_EXPIRED`。
- 已使用/撤销返回 `AUTH_REFRESH_TOKEN_REVOKED`。
- 重放检测：同一旧 refresh token 再次使用时，整个 token family 标记 COMPROMISED/REVOKED。

必须实现 logout：

- 从 access_token Cookie 认证当前用户。
- 强制 CSRF。
- 撤销当前 session/token family。
- 清除 access_token、refresh_token、csrf_token cookie。
- 返回 204。

测试要求：

- refresh 成功轮换 token。
- refresh 后旧 token 不能再用。
- refresh 重放撤销 family。
- refresh 缺 CSRF 返回 `CSRF_TOKEN_MISSING`。
- refresh CSRF 不匹配返回 `CSRF_TOKEN_MISMATCH`。
- logout 成功清除 Cookie。
- logout 后 `/auth/me` 失败。

## 11. P3-06：实现当前用户上下文

目标：实现认证依赖和 `GET /api/v1/auth/me`。

允许修改：

- `apps/api/src/dependencies.py`
- `apps/api/src/modules/auth/dependencies.py`
- `apps/api/src/modules/auth/api.py`
- `apps/api/src/modules/auth/service.py`
- `apps/api/src/modules/users/schemas.py`
- `apps/api/tests/unit/test_auth_me.py`
- `development-logs/in-progress/P3-06-current-user.md`

必须实现：

- 从 access_token Cookie 解析当前用户。
- token 缺失/无效/过期返回 `AUTH_INVALID_TOKEN`。
- 用户不存在、已删除、禁用均返回 `AUTH_INVALID_TOKEN` 或契约允许的认证失败。
- `request.state.actor_id` 或等价字段可用于后续日志 actor 摘要。
- `/auth/me` 返回当前用户公开字段。

测试要求：

- 有效 access_token 调用 `/auth/me` 成功。
- 缺 token 失败。
- refresh_token 不能用于 `/auth/me`。
- 篡改 token 失败。
- 过期 access token 失败。
- 禁用用户失败。
- request context actor 可被设置或可通过 dependency 获取。

## 12. P3-07：实现资料读写

目标：实现 User API 的 P3 范围：`GET /api/v1/users/{user_id}`、`PATCH /api/v1/users/{user_id}`。组织列表和用户 agent 端点只做契约安全占位，不做 P4/P6 业务。

允许修改：

- `apps/api/src/modules/users/api.py`
- `apps/api/src/modules/users/service.py`
- `apps/api/src/modules/users/schemas.py`
- `apps/api/src/modules/users/repository.py`
- `apps/api/src/modules/users/permissions.py`
- `apps/api/src/main.py`
- `apps/api/tests/unit/test_users_api.py`
- `development-logs/in-progress/P3-07-user-profile-api.md`

必须实现：

- `GET /api/v1/users/{user_id}` 返回公开资料。
- 不返回 email、student_no、password_hash、session 信息。
- `PATCH /api/v1/users/{user_id}` 仅本人可修改。
- 管理员修改可暂不实现，返回 `USER_PERMISSION_DENIED` 或明确仅本人。
- PATCH 强制 CSRF。
- 可更新 display_name、bio、avatar_url、profile_visibility。
- 不允许更新 email、student_no、global_role、status。
- `GET /api/v1/users/{user_id}/organizations` 可返回 501 或空列表，但不得伪造 P4 已实现。
- `GET /api/v1/users/{user_id}/agent` 可返回 `AGENT_NOT_FOUND`，不得创建 Agent。

测试要求：

- 公开 GET 不返回敏感字段。
- 本人 PATCH 成功。
- 他人 PATCH 返回 `USER_PERMISSION_DENIED`。
- PATCH 缺 CSRF 失败。
- PATCH 不能更新 global_role/status。
- deleted user 返回 `USER_NOT_FOUND`。

## 13. P3-08：发布 UserRegistered

目标：在注册事务成功提交后发布 `UserRegistered` 领域事件，保证幂等和一次性。

允许修改：

- `apps/api/src/modules/users/events.py`
- `apps/api/src/modules/auth/service.py`
- `apps/api/src/events/bus.py`（仅在现有能力不够时）
- `apps/api/tests/unit/test_user_registered_event.py`
- `development-logs/in-progress/P3-08-user-registered-event.md`

必须实现：

- `UserRegistered` 事件类型。
- 事件字段：event_id、user_id、email_hash 或 email_normalized、occurred_at。
- 注册成功且事务提交后发布。
- 注册失败不发布。
- 重复注册冲突不发布。
- 不在事件里放密码、token、student profile 全量。

测试要求：

- 注册成功发布一次。
- 重复请求不重复发布。
- 失败注册不发布。
- event_id 稳定或可追踪。
- 事件不含密码/token。

禁止：

- 不实现 Agent 自动创建；P3 只发布事件。

## 14. P3-09：账号删除流程

目标：实现 MVP 账号软删除/匿名化基础，不做完整数据清理编排。

允许修改：

- `apps/api/src/modules/users/api.py`
- `apps/api/src/modules/users/service.py`
- `apps/api/src/modules/auth/service.py`
- `apps/api/tests/unit/test_account_deletion.py`
- `development-logs/in-progress/P3-09-account-deletion.md`

建议端点：

- 如果 `API_CONTRACT.md` 没有明确账号删除端点，不新增公开契约端点。
- 可实现 service 层 `deactivate_user(user_id)` / `soft_delete_user(user_id)`，供后续阶段使用。
- 如确需临时 API，必须先记录与契约差异并停止等待 Codex/用户确认。

必须实现：

- 用户 status 可变为 `DELETED` 或 `DISABLED`。
- 删除/禁用后撤销 token family。
- 删除/禁用后无法登录。
- 删除/禁用后 `/auth/me` 失败。
- 公开用户资料返回 `USER_NOT_FOUND` 或不包含敏感字段。

测试要求：

- soft delete 设置 deleted_at。
- soft delete 撤销 session。
- deleted user login 失败。
- deleted user auth/me 失败。
- 不硬删除 User 主记录，避免破坏审计外键。

## 15. P3-10：Auth 限流

目标：实现登录/注册基础限流，防暴力破解和账号枚举。

允许修改：

- `apps/api/src/modules/auth/rate_limit.py`
- `apps/api/src/modules/auth/api.py`
- `apps/api/src/cache/redis.py`（仅新增通用 helper 时）
- `apps/api/tests/unit/test_auth_rate_limit.py`
- `development-logs/in-progress/P3-10-auth-rate-limit.md`

必须实现：

- 登录按 IP + email normalize 维度限流。
- 注册按 IP + email normalize 维度限流。
- Redis 可用时使用 Redis TTL 计数。
- Redis 不可用时失败关闭还是降级？P3 采用保守 MVP：认证服务可继续，但记录 unavailable，并使用进程内短期计数器作为测试/开发兜底。
- 限流命中返回稳定错误，优先 `RATE_LIMITED` 或契约已有通用错误码。
- 不泄露账号是否存在。

建议默认：

- login：5 次 / 5 分钟。
- register：3 次 / 10 分钟。
- 测试中可注入更小阈值。

测试要求：

- 未超过阈值允许。
- 达到阈值后拒绝。
- TTL 过后恢复。
- 不同 email 独立。
- 不同 IP 独立。
- Redis down 时不崩溃。

## 16. P3-11：完成认证测试

目标：补齐 P3 阶段级认证/安全测试，不新增业务能力。

允许修改：

- `apps/api/tests/integration/test_auth_flow.py`
- `apps/api/tests/unit/test_auth_security_regression.py`
- `development-logs/in-progress/P3-11-auth-test-suite.md`

必须覆盖：

- register → me → logout → me fails。
- login → refresh → old refresh replay fails。
- disabled user cannot login。
- disabled user existing access token fails。
- CSRF missing/mismatch for refresh/logout/PATCH。
- register/login no CSRF required。
- password/token/cookie 不出现在日志。
- auth error shape 使用 envelope。
- request_id 存在。
- repeated failed login 不泄露账号是否存在。

必须扫描：

```bash
rg -n "access_token=.*eyJ|refresh_token=.*eyJ|password=.*|Bearer .*eyJ" apps/api/tests development-logs docs || true
```

不得有真实 token 或密码泄漏。

## 17. P3-12：完成登录注册页面

目标：实现最小可用的登录/注册前端闭环。

允许修改：

- `apps/web/app/login/page.tsx`
- `apps/web/app/register/page.tsx`
- `apps/web/app/page.tsx`
- `apps/web/src/lib/api.ts`
- `apps/web/src/lib/csrf.ts`
- `apps/web/src/components/auth/*.tsx`
- `apps/web/__tests__/*.test.tsx`
- `development-logs/in-progress/P3-12-auth-pages.md`

必须实现：

- 登录页面。
- 注册页面。
- 表单 loading/error 状态。
- 调用 `/api/v1/auth/login` 和 `/api/v1/auth/register`。
- 使用 `credentials: "include"`。
- 不读取 access_token/refresh_token。
- 提供读取 `csrf_token` 的 helper，供后续写请求使用。
- 登录/注册成功后可调用 `/api/v1/auth/me` 验证状态。

可以实现：

- 简单首页根据 `/auth/me` 显示已登录/未登录。

禁止：

- 不做组织页。
- 不做聊天页。
- 不做 Agent 页。
- 不把 token 放 localStorage/sessionStorage。

测试要求：

- 登录表单渲染。
- 注册表单渲染。
- submit 调用正确 endpoint。
- fetch 使用 `credentials: "include"`。
- 错误消息展示。
- 不访问 localStorage token。

## 18. P3 总体验证

P3-01～P3-12 全部完成后必须运行：

```bash
git status --short --branch
git diff HEAD --check
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
conda run -n CampusAgent python -m pip check
```

如果 `/tmp/gitleaks-bin/gitleaks` 存在：

```bash
/tmp/gitleaks-bin/gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner
```

如果 Docker 可用：

```bash
docker compose config
docker compose up -d postgres redis
docker compose ps
docker compose down
```

如果 Docker 不可用，记录：

```text
docker command not found，未执行 docker compose 实跑。
```

## 19. P3 禁止事项

禁止修改：

- `docs/api/API_CONTRACT.md`，除非发现实现无法满足契约并先停止等待审计。
- `docs/api/WEBSOCKET_CONTRACT.md`
- `docs/security/THREAT_MODEL.md`
- `docs/privacy/PRIVACY_TEST_MATRIX.md`

禁止行为：

- 不执行 P4～P13。
- 不实现 Organization/Membership。
- 不实现 Conversation/Message。
- 不实现 Agent 自动创建，只发布事件。
- 不实现 Memory。
- 不接真实实验室模型。
- 不把 access_token/refresh_token 返回 JSON body。
- 不把 token 存 localStorage/sessionStorage。
- 不记录密码、JWT、Cookie、CSRF token 原文。
- 不提交。
- 不推送。

## 20. 每个任务开发日志格式

每个任务创建：

```text
development-logs/in-progress/P3-XX-<short-name>.md
```

front matter：

```yaml
---
task_id: P3-XX
task_name: <中文任务名>
status: in_review
started_at: 2026-07-16T00:00:00+08:00
completed_at: 2026-07-16T00:00:00+08:00
actual_hours: <数字>
owner: Claude
auditor: Codex
---
```

正文必须包含：

1. 背景
2. 修改文件列表
3. 设计说明
4. 测试覆盖
5. 自检命令和结果
6. 未执行项及原因
7. 边界声明

边界声明至少包括：

- 未执行 P4+
- 未修改 P0/P1 冻结契约
- 未实现 Agent/Organization/Conversation/Memory
- 未引入真实密钥
- 未提交、未推送

## 21. P3 完成报告格式

P3 全部完成后创建：

```text
development-logs/in-progress/P3-COMPLETION-REPORT.md
```

报告必须包含：

1. 基准信息：路径、分支、基准提交、P2 CI run。
2. P3-01～P3-12 每个任务完成摘要。
3. 所有修改文件列表。
4. Auth/User 数据模型说明。
5. Cookie/JWT/CSRF 设计说明。
6. Refresh token 轮换和重放检测说明。
7. 限流设计说明。
8. 前端登录/注册说明。
9. 测试清单和数量。
10. 完整自检命令结果。
11. 未执行项及原因。
12. `git status --short --branch` 完整输出。
13. 冻结契约未修改确认。
14. 明确声明未提交、未推送。

## 22. 给 Claude 的启动指令

可以直接把以下内容复制给 Claude 新对话：

```text
你现在接手 CampusAgent P3 阶段开发。项目路径是 /root/CampusAgent，当前分支 main，最新基准提交应为 1d5af9d test(api): isolate readiness checks from CI services。P2 已由 Codex 收口、提交、推送并通过远端 CI：https://github.com/SWFann/CampusAgent/actions/runs/29500458558。

请先执行：
cd /root/CampusAgent
git status --short --branch
git log -3 --oneline

如果工作树不干净，立即停止并报告。

然后阅读：
docs/development/P3_FULL_IMPLEMENTATION_GUIDE.md

再按该文件从 P3-01 到 P3-12 顺序执行。不要跳任务，不要执行 P4+，不要修改 P0/P1 冻结契约，不要提交，不要推送。每个任务必须写 development log、更新 DEVELOPMENT_PLAN.md、补测试并运行验证。全部完成后写 development-logs/in-progress/P3-COMPLETION-REPORT.md，输出完整报告交给 Codex 审计。
```

