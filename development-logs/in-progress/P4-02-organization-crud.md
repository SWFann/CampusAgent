---
task_id: P4-02
task_name: 实现组织 CRUD
status: in_review
started_at: 2026-07-17T09:30:00+08:00
completed_at: 2026-07-17T11:00:00+08:00
actual_hours: 1.5
owner: Claude
auditor: Codex
---

# P4-02 开发日志：实现组织 CRUD

## 1. 背景

P4-02 实现组织创建、列表、详情、更新和软删除。创建者自动成为 OWNER，写端点要求认证 + CSRF，列表和详情按权限裁剪。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/schemas.py` | 重写 | 10 个 Pydantic schema（Create/Update/Read/List/Member） |
| `apps/api/src/modules/organizations/repository.py` | 重写 | OrganizationRepository + OrganizationMembershipRepository |
| `apps/api/src/modules/organizations/service.py` | 重写 | CRUD 业务逻辑 + 权限检查 + 事件发布 |
| `apps/api/src/modules/organizations/exceptions.py` | 重写 | 6 个 AppError 子类（ORG_NOT_FOUND 等） |
| `apps/api/src/modules/organizations/api.py` | 重写 | 11 个 API 端点（CRUD + 成员管理） |
| `apps/api/src/main.py` | 修改 | 注册 organizations 路由 |
| `apps/api/src/modules/auth/dependencies.py` | 修改 | 新增 `get_optional_current_user` 依赖 |
| `apps/api/tests/unit/test_organization_crud.py` | 新增 | CRUD 测试 (21) |

## 3. 设计说明

### 3.1 Repository 层

- `OrganizationRepository`: get_by_id, get_active_by_id, list_active, get_children, slug_exists, count_active_members, search
- `OrganizationMembershipRepository`: get_by_org_user, get_active_by_org_user, list_active_by_org, list_active_by_user, count_active_owners, count_active_members, has_active_membership
- Repository 只做查询和基础持久化，不做权限决策

### 3.2 Service 层

- `create_organization`: 验证 type/visibility/join_policy，验证 parent_id，检查 slug 唯一性，创建组织 + OWNER membership，commit 后发布 `OrganizationCreated` 事件
- `list_organizations`: 按 visibility 权限过滤，分页返回
- `get_organization`: 权限检查后返回详情
- `update_organization`: OWNER/ADMIN/SYSTEM_ADMIN/SCHOOL_ADMIN 可更新，只能改 name/description/visibility/join_policy/capacity
- `delete_organization`: 软删除（status=DELETED, deleted_at），只有 OWNER/SYSTEM_ADMIN 可执行，commit 后发布 `OrganizationArchived` 事件
- 删除后 list/search/tree 不返回

### 3.3 API 端点

| 端点 | 方法 | 认证 | CSRF |
|------|------|:----:|:----:|
| `/api/v1/organizations` | POST | 必须 | 必须 |
| `/api/v1/organizations` | GET | 可选 | — |
| `/api/v1/organizations/{id}` | GET | 可选 | — |
| `/api/v1/organizations/{id}` | PATCH | 必须 | 必须 |
| `/api/v1/organizations/{id}` | DELETE | 必须 | 必须 |

### 3.4 Schema 设计

- `OrganizationRead`: 不包含成员列表或敏感用户数据
- `OrganizationListItem`: 最小安全投影（id, name, type, visibility, status, member_count）
- 成员 schema 只返回 user_id, display_name, avatar_url, global_role, role, status — 不返回 email/student_no/password_hash

### 3.5 可选用户依赖

- 新增 `get_optional_current_user`：从 Cookie/Authorization 解析用户，匿名返回 None
- 不破坏现有 `get_current_user` 语义

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_create_org_success` | 登录用户创建组织返回 201 |
| `test_create_org_auto_owner` | 创建者自动成为 OWNER |
| `test_create_org_no_auth` | 匿名创建返回 401 |
| `test_create_org_no_csrf` | 缺 CSRF 返回 CSRF_TOKEN_MISSING |
| `test_create_org_with_parent` | 带父组织创建成功 |
| `test_create_org_invalid_type` | 无效类型报错 |
| `test_create_org_duplicate_slug` | slug 重复返回 409 |
| `test_list_orgs_public_visible` | 公开组织对所有人可见 |
| `test_list_orgs_private_hidden` | 私有组织对非成员不可见 |
| `test_get_org_public` | 获取公开组织详情 |
| `test_get_org_private_denied` | 非成员无法获取私有组织 |
| `test_get_org_not_found` | 不存在的组织返回 404 |
| `test_get_org_deleted_not_found` | 已删除组织返回 404 |
| `test_update_org_owner` | OWNER 可更新 |
| `test_update_org_admin` | ADMIN 可更新 |
| `test_update_org_member_denied` | MEMBER 不可更新 |
| `test_update_org_non_member_denied` | 非成员不可更新 |
| `test_delete_org_owner` | OWNER 可软删除 |
| `test_delete_org_member_denied` | MEMBER 不可删除 |
| `test_delete_org_then_not_found` | 删除后获取返回 404 |
| `test_delete_org_csrf_required` | 删除需要 CSRF |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_crud.py -q -p no:cacheprovider
# 21 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证（Docker 不可用）
- 集成测试在 P4-03 中统一执行

## 7. 边界声明

- 未实现成员生命周期完整逻辑（P4-03）
- 未实现权限策略服务完整矩阵（P4-04）
- 未修改冻结契约
- 未提交、未推送
