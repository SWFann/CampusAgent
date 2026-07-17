# P4 完成报告：组织、成员与校园目录

> **执行人**: Claude (AI 辅助实现)
> **执行日期**: 2026-07-17
> **审计人**: Codex
> **分支**: main (未提交、未推送)

## 1. 基准信息

| 项目 | 值 |
|------|-----|
| 项目路径 | `/root/CampusAgent` |
| 分支 | `main` |
| 起始提交 | `34df5d5 test(auth): avoid gitleaks false positive in auth model test` |
| 是否保留 P3 | ✅ 是，P3 代码和测试完整保留 |
| 远程仓库 | `git@github.com:SWFann/CampusAgent.git` |

## 2. 完成任务列表 P4-01～P4-12

| ID | 任务 | 状态 | 测试数 |
|----|------|:----:|:------:|
| P4-01 | 设计组织模型 | [x] | 9 |
| P4-02 | 实现组织 CRUD | [x] | 21 |
| P4-03 | 实现成员生命周期 | [x] | 11 + 5 集成 |
| P4-04 | 实现组织角色 | [x] | 20 |
| P4-05 | 保护最后一个 Owner | [x] | 7 |
| P4-06 | 实现加入策略 | [x] | 8 |
| P4-07 | 实现目录搜索 | [x] | 11 |
| P4-08 | 实现组织树 | [x] | 8 |
| P4-09 | 实现推荐占位规则 | [x] | 6 |
| P4-10 | 发布成员领域事件 | [x] | 8 |
| P4-11 | 完成越权测试矩阵 | [x] | 13 |
| P4-12 | 完成组织与联系人页面 | [x] | — |

**P4 新增测试**: 127 个（含 5 个集成测试）
**后端总测试**: 454 passed（P3 的 324 + P4 新增 130）

## 3. 修改文件列表

### 后端 — 修改 (apps/api/)

| 文件 | 说明 |
|------|------|
| `src/modules/organizations/models.py` | Organization、OrganizationMembership ORM 模型及 6 个枚举 |
| `src/modules/organizations/schemas.py` | 10 个 Pydantic schema（Create/Update/Read/List/Member） |
| `src/modules/organizations/repository.py` | OrganizationRepository + OrganizationMembershipRepository |
| `src/modules/organizations/service.py` | CRUD + 成员生命周期 + 权限 + 事件发布 (902 行) |
| `src/modules/organizations/permissions.py` | OrganizationPermissionService 集中权限服务 |
| `src/modules/organizations/events.py` | 5 个 DomainEvent 子类 |
| `src/modules/organizations/exceptions.py` | 6 个 AppError 子类 |
| `src/modules/organizations/api.py` | 11 个 API 端点 |
| `src/modules/directory/schemas.py` | 目录搜索/树/推荐 schema |
| `src/modules/directory/exceptions.py` | 4 个 AppError 子类 |
| `src/modules/directory/service.py` | 搜索/树/推荐业务逻辑 (402 行) |
| `src/modules/directory/api.py` | 3 个 API 端点 |
| `src/modules/auth/dependencies.py` | 新增 `get_optional_current_user` |
| `src/modules/users/api.py` | 实现 `GET /users/{id}/organizations` |
| `src/main.py` | 注册 organizations 和 directory 路由 |
| `tests/conftest.py` | 导入组织模型 |
| `tests/unit/test_alembic.py` | 更新迁移测试 |
| `pyproject.toml` | 添加 test helper pythonpath |

### 后端 — 新增 (apps/api/)

| 文件 | 说明 |
|------|------|
| `alembic/versions/0003_organization_membership_tables.py` | 组织与成员表迁移 (168 行) |
| `tests/unit/test_organization_models.py` | 模型测试 (9) |
| `tests/unit/test_organization_crud.py` | CRUD 测试 (21) |
| `tests/unit/test_organization_membership.py` | 成员生命周期测试 (11) |
| `tests/unit/test_organization_permissions.py` | 权限矩阵测试 (20) |
| `tests/unit/test_organization_owner_protection.py` | 最后 OWNER 保护测试 (7) |
| `tests/unit/test_organization_join_policy.py` | 加入策略测试 (8) |
| `tests/unit/test_organization_events.py` | 领域事件测试 (8) |
| `tests/unit/test_directory_search.py` | 目录搜索测试 (11) |
| `tests/unit/test_directory_tree.py` | 组织树测试 (8) |
| `tests/unit/test_directory_recommended.py` | 推荐测试 (6) |
| `tests/unit/test_organization_authorization_matrix.py` | 越权测试矩阵 (13) |
| `tests/integration/test_organization_flow.py` | 集成测试 (5) |
| `tests/unit/helpers_p4.py` | P4 测试辅助函数 |

### 前端 — 新增 (apps/web/)

| 文件 | 说明 |
|------|------|
| `src/app/organizations/page.tsx` | 组织列表与创建页面 (193 行) |
| `src/app/organizations/[organizationId]/page.tsx` | 组织详情与成员管理 (200 行) |
| `src/app/directory/page.tsx` | 目录搜索与推荐页面 (154 行) |
| `src/lib/organizations.ts` | 组织 API helper (195 行) |
| `src/lib/directory.ts` | 目录 API helper (113 行) |

### 文档和日志

| 文件 | 说明 |
|------|------|
| `docs/development/DEVELOPMENT_PLAN.md` | P4-01～P4-12 标记 [x]，进度表更新 |
| `docs/development/P4-COMPLETION-REPORT.md` | 本报告 |
| `docs/development/P4_FULL_IMPLEMENTATION_GUIDE.md` | P4 执行指南 |
| `mypy.ini` | mypy 配置（忽略 test helper 导入检查） |
| `development-logs/in-progress/P4-01-organization-model.md` | 开发日志 |
| `development-logs/in-progress/P4-02-organization-crud.md` | 开发日志 |
| `development-logs/in-progress/P4-03-membership-lifecycle.md` | 开发日志 |
| `development-logs/in-progress/P4-04-organization-roles.md` | 开发日志 |
| `development-logs/in-progress/P4-05-last-owner-protection.md` | 开发日志 |
| `development-logs/in-progress/P4-06-join-policy.md` | 开发日志 |
| `development-logs/in-progress/P4-07-directory-search.md` | 开发日志 |
| `development-logs/in-progress/P4-08-directory-tree.md` | 开发日志 |
| `development-logs/in-progress/P4-09-directory-recommended.md` | 开发日志 |
| `development-logs/in-progress/P4-10-membership-events.md` | 开发日志 |
| `development-logs/in-progress/P4-11-authorization-test-matrix.md` | 开发日志 |
| `development-logs/in-progress/P4-12-organization-frontend.md` | 开发日志 |

## 4. 数据模型说明

### 4.1 Organization

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID PK | 主键 |
| `name` | String(120) | 组织名称 |
| `slug` | String(160), unique, nullable | URL 友好标识 |
| `type` | String(40) | SCHOOL/COLLEGE/DEPARTMENT/CLASS/DORM/CLUB/COURSE/TEAM/OTHER |
| `parent_id` | UUID FK → organizations.id, nullable | 父组织（树结构） |
| `description` | String(500), nullable | 描述 |
| `visibility` | String(40) | PUBLIC/MEMBERS_ONLY/PRIVATE |
| `join_policy` | String(40) | OPEN/APPROVAL/INVITE_ONLY/CLOSED |
| `status` | String(40) | ACTIVE/ARCHIVED/DELETED |
| `capacity` | int, nullable | 成员上限 |
| `created_by` | UUID FK → users.id | 创建者 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |
| `archived_at` | datetime, nullable | 归档时间 |
| `deleted_at` | datetime, nullable | 删除时间 |

关系：`parent`/`children`（自引用）、`memberships`（一对多）

### 4.2 OrganizationMembership

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID PK | 主键 |
| `organization_id` | UUID FK → organizations.id | 组织 |
| `user_id` | UUID FK → users.id | 用户 |
| `role` | String(40) | OWNER/ADMIN/MEMBER/GUEST |
| `status` | String(40) | INVITED/PENDING/ACTIVE/LEFT/REMOVED |
| `invited_by` | UUID FK → users.id, nullable | 邀请人 |
| `joined_at` | datetime, nullable | 加入时间 |
| `left_at` | datetime, nullable | 离开时间 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

唯一约束：`(organization_id, user_id)` — 同一用户在同一组织只有一条权威记录

`__repr__` 不泄露 email、password_hash 等敏感字段。

## 5. Alembic 迁移说明

**迁移文件**: `0003_organization_membership_tables.py`
- `revision = "0003_organization_membership_tables"`
- `down_revision = "0002_user_auth_tables"`

**创建表**:
- `organizations`（含 parent_id 自引用外键）
- `organization_memberships`（含 3 个外键）

**创建索引** (7 个):
- `ix_organizations_parent_id`
- `ix_organizations_type`
- `ix_organizations_status`
- `ix_organization_memberships_organization_id`
- `ix_organization_memberships_user_id`
- `ix_organization_memberships_role`
- `ix_organization_memberships_status`

**创建唯一约束** (1 个):
- `uq_organization_memberships_org_user`

**迁移测试**:
- ✅ upgrade 后存在 `organizations` 和 `organization_memberships` 表
- ✅ downgrade 后表移除
- ✅ upgrade → downgrade → upgrade 可重复

## 6. API 端点说明

### 组织 API (`/api/v1/organizations`)

| 端点 | 方法 | 认证 | CSRF | 说明 |
|------|------|:----:|:----:|------|
| `/api/v1/organizations` | POST | 必须 | 必须 | 创建组织，创建者自动成为 OWNER |
| `/api/v1/organizations` | GET | 可选 | — | 列表（按权限裁剪） |
| `/api/v1/organizations/{id}` | GET | 可选 | — | 详情（按权限裁剪） |
| `/api/v1/organizations/{id}` | PATCH | 必须 | 必须 | 更新（OWNER/ADMIN/系统管理员） |
| `/api/v1/organizations/{id}` | DELETE | 必须 | 必须 | 软删除（OWNER/SYSTEM_ADMIN） |
| `/api/v1/organizations/{id}/members` | POST | 必须 | 必须 | 添加成员 |
| `/api/v1/organizations/{id}/members` | GET | 必须 | — | 成员列表 |
| `/api/v1/organizations/{id}/members/{user_id}` | PATCH | 必须 | 必须 | 修改角色 |
| `/api/v1/organizations/{id}/members/{user_id}` | DELETE | 必须 | 必须 | 移除成员 |
| `/api/v1/organizations/{id}/join` | POST | 必须 | 必须 | 自助加入 |
| `/api/v1/organizations/{id}/leave` | POST | 必须 | 必须 | 退出 |

### 目录 API (`/api/v1/directory`)

| 端点 | 方法 | 认证 | CSRF | 说明 |
|------|------|:----:|:----:|------|
| `/api/v1/directory/search` | GET | 可选 | — | 搜索用户和组织 |
| `/api/v1/directory/tree` | GET | 可选 | — | 组织树（权限裁剪） |
| `/api/v1/directory/recommended` | GET | 可选 | — | 推荐组织 |

### 用户 API 补齐

| 端点 | 方法 | 认证 | CSRF | 说明 |
|------|------|:----:|:----:|------|
| `/api/v1/users/{user_id}/organizations` | GET | 可选 | — | 用户组织列表（权限裁剪） |

### 错误码

| 错误码 | HTTP | 说明 |
|--------|------|------|
| ORG_NOT_FOUND | 404 | 组织不存在 |
| ORG_PERMISSION_DENIED | 403 | 无权操作 |
| ORG_MEMBER_ALREADY_EXISTS | 409 | 已是成员 |
| ORG_LAST_OWNER_CANNOT_LEAVE | 409 | 最后所有者保护 |
| ORG_INVALID_JOIN_POLICY | 400 | 加入策略不允许 |
| ORG_CAPACITY_EXCEEDED | 409 | 成员已满 |
| DIRECTORY_QUERY_TOO_SHORT | 400 | 搜索关键词过短 |
| DIRECTORY_INVALID_TYPE | 400 | 无效搜索类型 |
| DIRECTORY_ORG_NOT_FOUND | 404 | 组织不存在或无权查看 |
| DIRECTORY_TREE_TOO_DEEP | 400 | 树深度超限 |
| ORG_SLUG_ALREADY_EXISTS | 409 | slug 重复（自定义 code） |

## 7. 权限策略说明

### 7.1 集中权限服务

`OrganizationPermissionService`（单例 `permission_service`）实现所有权限判定：

| 方法 | 说明 |
|------|------|
| `can_view_organization` | 查看组织详情 |
| `can_view_members` | 查看成员列表 |
| `can_update_organization` | 更新组织 |
| `can_delete_organization` | 删除组织 |
| `can_add_member` | 添加成员（按目标角色） |
| `can_remove_member` | 移除成员 |
| `can_change_member_role` | 修改角色 |
| `can_transfer_ownership` | 转让所有权 |

### 7.2 权限矩阵

| Actor | View PUBLIC | View PRIVATE | Add Member | Change Role | Delete Org |
|-------|:---:|:---:|:---:|:---:|:---:|
| anonymous | ✅ | ❌ | ❌ | ❌ | ❌ |
| non-member | ✅ | ❌ | ❌ | ❌ | ❌ |
| GUEST | ✅ | limited | ❌ | ❌ | ❌ |
| MEMBER | ✅ | ✅ | ❌ | ❌ | ❌ |
| ADMIN | ✅ | ✅ | MEMBER/GUEST | MEMBER/GUEST | ❌ |
| OWNER | ✅ | ✅ | all | all | ✅ |
| SYSTEM_ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ |
| SCHOOL_ADMIN | ✅ | ✅ | ✅ | ✅ | ❌ (MVP 可管理) |
| ORG_ADMIN | ❌ | ❌ | ❌ | ❌ | ❌ |

### 7.3 关键设计决策

- **ORG_ADMIN 不自动等于任意组织 OWNER**: 全局 ORG_ADMIN 角色不赋予任何组织管理权限
- **SCHOOL_ADMIN P4 MVP**: 可管理全部组织，后续按学校范围收窄
- **ADMIN 不能操作 OWNER**: ADMIN 不能移除、修改 OWNER，不能升人为 OWNER
- **后端强制权限**: 不依赖前端隐藏按钮，所有写操作在 service 层检查权限

## 8. 加入策略说明

| 策略 | 自助 join | membership status | role |
|------|----------|-------------------|------|
| OPEN | 直接加入 | ACTIVE | MEMBER |
| APPROVAL | 需审批 | PENDING | MEMBER |
| INVITE_ONLY | 拒绝 (`ORG_INVALID_JOIN_POLICY`) | — | — |
| CLOSED | 拒绝 (`ORG_INVALID_JOIN_POLICY`) | — | — |

- **Capacity 限制**: `capacity` 不为 None 时，ACTIVE 成员数 >= capacity 返回 `ORG_CAPACITY_EXCEEDED`
- **管理员添加**: 不受 join_policy 限制，但受 capacity 和权限限制
- **重复加入**: LEFT/REMOVED 状态可重新加入（复用行）

## 9. 最后 OWNER 保护说明

| 路径 | 保护行为 |
|------|---------|
| 最后 OWNER 退出 | `ORG_LAST_OWNER_CANNOT_LEAVE` (409) |
| 最后 OWNER 被移除 | `ORG_LAST_OWNER_CANNOT_LEAVE` (409) |
| 最后 OWNER 被降级 | `ORG_LAST_OWNER_CANNOT_LEAVE` (409) |
| 删除组织绕过 | 不适用（软删除是 OWNER/SYSTEM_ADMIN 显式操作） |

**所有权转让**:
- 只有当前 OWNER 或 SYSTEM_ADMIN 可转让
- 转让方式：先通过 `update_member_role` 升新 OWNER（此时有两个 OWNER），再降旧 OWNER
- ADMIN 不能转让所有权

**测试验证**: 7 个测试覆盖所有保护路径和转让逻辑

## 10. 目录搜索说明

### 搜索参数
- `q` (str, 必填): 搜索关键词，最少 2 字符
- `type` (str, 默认 "all"): all/users/organizations
- `limit` (int, 默认 20): 每类最大返回数
- `offset` (int, 默认 0): 分页偏移

### 用户搜索隐私投影
- **搜索字段**: 只搜 `display_name`（ilike）
- **不搜索**: email, student_no, bio
- **不返回**: email, student_no, password_hash, bio
- **返回字段**: id, display_name, avatar_url, profile_visibility
- **过滤**: 只返回 ACTIVE 用户

### 组织搜索隐私投影
- **搜索字段**: name, slug（ilike）
- **可见性**: PUBLIC 对所有人，MEMBERS_ONLY/PRIVATE 对成员/系统管理员
- **过滤**: 排除 DELETED/ARCHIVED

### 分页策略
- MVP 使用 limit + offset 简单分页
- 按名称升序排序

## 11. 组织树说明

- **端点**: `GET /api/v1/directory/tree`
- **参数**: `root_organization_id` (可选), `max_depth` (默认 3, 上限 5)
- **递归构建**: service 层递归，每个节点通过 `can_view_organization` 检查
- **裁剪**: 不可见节点不返回，其子树整棵裁剪
- **安全投影**: 只返回 id, name, type, visibility, status, parent_id, children
- **错误**: `DIRECTORY_TREE_TOO_DEEP` (max_depth > 5), `DIRECTORY_ORG_NOT_FOUND` (root 不存在/无权)
- **max_depth 检查**: 在 service 层执行，不在 API 层使用 FastAPI 约束（避免 422 先于业务逻辑）

## 12. 推荐占位规则说明

- **匿名用户**: 返回 PUBLIC 组织通用推荐，reason: `"public_organization"`
- **已登录用户**:
  - 策略 1: 同父组织下 PUBLIC 兄弟组织，reason: `"same_parent_public_organization"`
  - 策略 2: 未加入的 PUBLIC CLUB/COURSE/TEAM，reason: `"public_club_course_team"`
- **隐私保证**: 不做隐性画像，不读取偏好/聊天/消息/记忆，不使用 email/student_no/bio
- **可解释**: 每个推荐包含 `reason` 字段
- **空结果**: 无安全推荐时返回空数组

## 13. 领域事件说明

### 事件类型

| 事件 | 触发时机 |
|------|---------|
| `OrganizationCreated` | 创建组织后 |
| `OrganizationArchived` | 归档/删除组织后 |
| `OrganizationMemberJoined` | 添加成员/加入后 |
| `OrganizationMemberLeft` | 退出/移除成员后 |
| `OrganizationMemberRoleChanged` | 修改角色后 |

### 事件总线
- 使用 P2 `default_event_bus`，不新建不兼容事件总线
- 事件在 `session.commit()` 成功后发布
- handler 异常不阻断主流程（P2 EventBus 语义）

### 隐私要求
- **不包含**: email, student_no, password_hash, token, session, bio
- **只包含**: event_id, organization_id, user_id, actor_id, role, status, action, occurred_at
- 事件 ID 使用 `secrets.token_hex(16)` 生成

## 14. 前端页面说明

### `/organizations` — 组织列表与创建
- 组织列表展示（name, type, visibility, member_count）
- 创建组织表单
- loading/error/empty 状态

### `/organizations/[organizationId]` — 组织详情与成员管理
- 组织详情展示
- 成员列表（display_name, role, status）
- 添加成员/修改角色/移除成员
- 加入/退出按钮
- 根据 API 返回隐藏无权操作入口

### `/directory` — 目录搜索与推荐
- 搜索框 + 类型筛选
- 安全字段展示（不含 email/student_no）
- 推荐组织区域

### 前端安全
- 所有请求 `credentials: "include"`
- 写请求使用 `getWriteHeaders()` 带 CSRF
- 不使用 localStorage/sessionStorage 存 token
- 不把 token 放 URL

## 15. 新增/修改测试列表

| 测试文件 | 测试数 | 说明 |
|---------|:------:|------|
| `test_organization_models.py` | 9 | 模型、默认值、repr、迁移 |
| `test_organization_crud.py` | 21 | CRUD、权限、CSRF |
| `test_organization_membership.py` | 11 | 成员生命周期、状态转换 |
| `test_organization_permissions.py` | 20 | 权限矩阵完整覆盖 |
| `test_organization_owner_protection.py` | 7 | 最后 OWNER 保护 |
| `test_organization_join_policy.py` | 8 | 加入策略、capacity |
| `test_organization_events.py` | 8 | 领域事件发布、隐私 |
| `test_directory_search.py` | 11 | 搜索、隐私投影 |
| `test_directory_tree.py` | 8 | 组织树、权限裁剪 |
| `test_directory_recommended.py` | 6 | 推荐、隐私 |
| `test_organization_authorization_matrix.py` | 13 | 越权测试矩阵 |
| `test_organization_flow.py` | 5 | 端到端集成测试 |
| `test_alembic.py` | (修改) | 新增组织表迁移测试 |
| **总计** | **127** | |

## 16. 自检命令和结果

```bash
# 1. Git 状态
git status --short --branch
# ## main...origin/main (19 modified, 17+ new files, 未提交)

# 2. Ruff 检查
ruff check apps/api --no-cache
# All checks passed!

# 3. Mypy 检查
mypy apps/api/src apps/api/tests --no-incremental
# Success: no issues found in 198 source files

# 4. 后端全量测试
python -m pytest apps/api/tests -q -p no:cacheprovider
# 454 passed, 1 warning in 67.14s

# 5. 前端 Lint
corepack pnpm --filter @campus-agent/web lint
# ✓ No ESLint warnings or errors

# 6. 前端 Typecheck
corepack pnpm --filter @campus-agent/web typecheck
# ✓ tsc --noEmit passed

# 7. 前端 Build
corepack pnpm --filter @campus-agent/web build
# ✓ Compiled successfully
# Routes: /organizations, /organizations/[organizationId], /directory

# 8. Gitleaks
/tmp/gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner
# 33 commits scanned. no leaks found.

# 9. Git diff check
git diff HEAD --check
# (no output — clean)
```

### 验证结果汇总

| 检查项 | 结果 |
|--------|------|
| Ruff | ✅ All checks passed! |
| Mypy | ✅ Success: no issues found in 198 source files |
| 后端测试 | ✅ 454 passed, 1 warning |
| 前端 Lint | ✅ No ESLint warnings or errors |
| 前端 Typecheck | ✅ tsc --noEmit passed |
| 前端 Build | ✅ Compiled successfully |
| Gitleaks | ✅ no leaks found |
| Git diff --check | ✅ clean |

## 17. 未执行项和原因

| 项目 | 原因 |
|------|------|
| Docker compose 实跑 | Docker 本地不可用（`docker: command not found`） |
| 远端 CI 观察 | 未提交、未推送，远端 CI 由 Codex 后续观察 |
| Playwright E2E | P4 前端页面已通过 lint/typecheck/build，E2E 在 P10/P11 阶段 |
| APPROVAL 审批接口 | MVP 仅记录 PENDING 状态，审批流程在后续迭代 |
| Cursor 分页 | MVP 使用 limit+offset，如 API_CONTRACT 后续要求 cursor 再实现 |

## 18. 边界声明

1. **未执行 P5+**: 未实现会话、消息、Agent、Memory、Scene、Model Gateway 等业务
2. **未修改冻结契约**: 未修改 `API_CONTRACT.md`、`WEBSOCKET_CONTRACT.md`、`PERMISSION_MATRIX.md`、`PRIVACY_TEST_MATRIX.md`、`THREAT_MODEL.md` 的语义
3. **未引入真实密钥**: 使用测试密钥和虚构数据
4. **未提交、未推送**: 所有变更仅在工作树中
5. **SCHOOL_ADMIN 权限**: P4 MVP 可管理全部组织，后续需按学校范围收窄
6. **ORG_ADMIN**: 全局角色不自动赋予组织管理权限（按设计）
7. **事件总线**: 使用进程内 `default_event_bus`，未实现跨进程发布
8. **组织树构建**: 使用 service 层递归，未使用 SQL 递归 CTE（MVP 策略）
9. **自定义错误码**: `ORG_SLUG_ALREADY_EXISTS` (409) 是冻结契约外的自定义 code，因契约无专用 `ORG_ALREADY_EXISTS`，在报告中说明
10. **mypy.ini**: 新增配置文件以忽略 test helper 的导入检查（`helpers_p4.py`）

## 19. `git status --short --branch` 输出

```
## main...origin/main
 M apps/api/pyproject.toml
 M apps/api/src/main.py
 M apps/api/src/modules/auth/dependencies.py
 M apps/api/src/modules/directory/api.py
 M apps/api/src/modules/directory/exceptions.py
 M apps/api/src/modules/directory/schemas.py
 M apps/api/src/modules/directory/service.py
 M apps/api/src/modules/organizations/api.py
 M apps/api/src/modules/organizations/events.py
 M apps/api/src/modules/organizations/exceptions.py
 M apps/api/src/modules/organizations/models.py
 M apps/api/src/modules/organizations/permissions.py
 M apps/api/src/modules/organizations/repository.py
 M apps/api/src/modules/organizations/schemas.py
 M apps/api/src/modules/organizations/service.py
 M apps/api/src/modules/users/api.py
 M apps/api/tests/conftest.py
 M apps/api/tests/unit/test_alembic.py
 M docs/development/DEVELOPMENT_PLAN.md
?? apps/api/alembic/versions/0003_organization_membership_tables.py
?? apps/api/tests/integration/test_organization_flow.py
?? apps/api/tests/unit/helpers_p4.py
?? apps/api/tests/unit/test_directory_recommended.py
?? apps/api/tests/unit/test_directory_search.py
?? apps/api/tests/unit/test_directory_tree.py
?? apps/api/tests/unit/test_organization_authorization_matrix.py
?? apps/api/tests/unit/test_organization_crud.py
?? apps/api/tests/unit/test_organization_events.py
?? apps/api/tests/unit/test_organization_join_policy.py
?? apps/api/tests/unit/test_organization_membership.py
?? apps/api/tests/unit/test_organization_models.py
?? apps/api/tests/unit/test_organization_owner_protection.py
?? apps/api/tests/unit/test_organization_permissions.py
?? apps/web/src/app/directory/
?? apps/web/src/app/organizations/
?? apps/web/src/lib/directory.ts
?? apps/web/src/lib/organizations.ts
?? development-logs/in-progress/P4-01-organization-model.md
?? development-logs/in-progress/P4-02-organization-crud.md
?? development-logs/in-progress/P4-03-membership-lifecycle.md
?? development-logs/in-progress/P4-04-organization-roles.md
?? development-logs/in-progress/P4-05-last-owner-protection.md
?? development-logs/in-progress/P4-06-join-policy.md
?? development-logs/in-progress/P4-07-directory-search.md
?? development-logs/in-progress/P4-08-directory-tree.md
?? development-logs/in-progress/P4-09-directory-recommended.md
?? development-logs/in-progress/P4-10-membership-events.md
?? development-logs/in-progress/P4-11-authorization-test-matrix.md
?? development-logs/in-progress/P4-12-organization-frontend.md
?? docs/development/P4-COMPLETION-REPORT.md
?? docs/development/P4_FULL_IMPLEMENTATION_GUIDE.md
?? mypy.ini
```

---

**报告结束。请 Codex 审计。**
