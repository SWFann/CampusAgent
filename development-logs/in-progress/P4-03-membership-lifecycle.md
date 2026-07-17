---
task_id: P4-03
task_name: 实现成员生命周期
status: in_review
started_at: 2026-07-17T11:00:00+08:00
completed_at: 2026-07-17T12:30:00+08:00
actual_hours: 1.5
owner: Claude
auditor: Codex
---

# P4-03 开发日志：实现成员生命周期

## 1. 背景

P4-03 实现成员添加、列表、角色更新、移除、加入和退出。状态转换清晰：INVITED/PENDING/ACTIVE/LEFT/REMOVED，复用同一行记录，不为同一用户和组织创建多条当前权威 membership。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/service.py` | 修改 | 新增 add_member, list_members, update_member_role, remove_member, join_organization, leave_organization |
| `apps/api/src/modules/organizations/api.py` | 修改 | 新增成员管理端点（6 个） |
| `apps/api/tests/unit/test_organization_membership.py` | 新增 | 成员生命周期测试 (11) |
| `apps/api/tests/integration/test_organization_flow.py` | 新增 | 端到端集成测试 (5) |
| `apps/api/tests/unit/helpers_p4.py` | 新增 | P4 测试公共辅助函数 |

## 3. 设计说明

### 3.1 成员添加 (`add_member`)

- OWNER 可添加 OWNER/ADMIN/MEMBER/GUEST
- ADMIN 只能添加 MEMBER/GUEST
- SYSTEM_ADMIN/SCHOOL_ADMIN 可添加任何角色
- 如果 membership 已存在且 ACTIVE/PENDING/INVITED → `ORG_MEMBER_ALREADY_EXISTS`
- 如果 membership 为 LEFT/REMOVED → 复用行恢复为 ACTIVE
- 如果 capacity 满 → `ORG_CAPACITY_EXCEEDED`
- commit 后发布 `OrganizationMemberJoined` 事件

### 3.2 成员列表 (`list_members`)

- 只有有权用户（OWNER/ADMIN/MEMBER，或 SYSTEM_ADMIN/SCHOOL_ADMIN）可查看
- GUEST 只能查看 PUBLIC 组织的成员列表
- 非成员不能查看
- 返回安全字段：user_id, display_name, avatar_url, global_role, role, status, joined_at, created_at
- 不返回 email, student_no, password_hash

### 3.3 角色更新 (`update_member_role`)

- OWNER 可修改任何人的角色（受最后 OWNER 保护限制）
- ADMIN 只能修改 MEMBER/GUEST 的角色，不能升为 OWNER
- 最后一个 OWNER 不能被降级 → `ORG_LAST_OWNER_CANNOT_LEAVE`
- commit 后发布 `OrganizationMemberRoleChanged` 事件

### 3.4 成员移除 (`remove_member`)

- OWNER 可移除任何人（受最后 OWNER 保护限制）
- ADMIN 只能移除 MEMBER/GUEST
- 最后一个 OWNER 不能被移除 → `ORG_LAST_OWNER_CANNOT_LEAVE`
- 移除后 status=REMOVED, left_at 设置
- commit 后发布 `OrganizationMemberLeft` 事件（action="removed"）

### 3.5 加入组织 (`join_organization`)

- OPEN: membership ACTIVE, role MEMBER
- APPROVAL: membership PENDING, role MEMBER
- INVITE_ONLY/CLOSED: `ORG_INVALID_JOIN_POLICY`
- 已是成员: `ORG_MEMBER_ALREADY_EXISTS`
- capacity 满: `ORG_CAPACITY_EXCEEDED`
- LEFT/REMOVED 状态可重新加入（复用行）
- commit 后发布 `OrganizationMemberJoined` 事件

### 3.6 退出组织 (`leave_organization`)

- 只有当前用户可 leave 自己
- 最后一个 OWNER 不能退出 → `ORG_LAST_OWNER_CANNOT_LEAVE`
- 退出后 status=LEFT, left_at 设置
- commit 后发布 `OrganizationMemberLeft` 事件（action="left"）

### 3.7 测试辅助 (`helpers_p4.py`)

- `create_test_user`: 创建测试用户（指定全局角色）
- `create_test_org`: 创建测试组织（指定类型/可见性/加入策略）
- `add_member_to_org`: 添加成员到组织
- `get_csrf_headers`: 获取 CSRF 请求头
- `register_and_login`: 注册并登录用户，返回 user + auth headers

## 4. 测试覆盖

### 单元测试 (test_organization_membership.py)

| 测试 | 说明 |
|------|------|
| `test_owner_add_member_success` | OWNER 添加 MEMBER 成功 |
| `test_add_duplicate_member` | 重复添加返回 ORG_MEMBER_ALREADY_EXISTS |
| `test_list_members_permission` | 成员列表只对有权用户可见 |
| `test_owner_remove_member` | OWNER 移除 MEMBER 成功 |
| `test_removed_user_cannot_view_private` | 被移除用户不能查看私有组织 |
| `test_user_leave_sets_status_left` | 用户 leave 后 status=LEFT |
| `test_rejoin_after_left` | LEFT 状态用户重新加入 |
| `test_admin_add_member_guest` | ADMIN 添加 GUEST 成功 |
| `test_admin_cannot_add_owner` | ADMIN 不能添加 OWNER |
| `test_non_member_cannot_list_members` | 非成员不能查看成员列表 |
| `test_member_list_no_sensitive_fields` | 成员列表不含 email/student_no |

### 集成测试 (test_organization_flow.py)

| 测试 | 说明 |
|------|------|
| `test_full_org_lifecycle` | 完整组织生命周期：创建→添加成员→改角色→移除→退出 |
| `test_org_tree_navigation` | 组织树导航 |
| `test_directory_search_integration` | 目录搜索集成 |
| `test_user_organizations_endpoint` | 用户组织列表端点 |
| `test_cross_org_isolation` | 跨组织隔离验证 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_membership.py apps/api/tests/integration/test_organization_flow.py -q -p no:cacheprovider
# 16 passed (11 unit + 5 integration)
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- 权限策略的完整矩阵测试在 P4-04 中
- 最后 OWNER 保护逻辑在 P4-05 中深化
- 加入策略的详细测试在 P4-06 中
- 未修改冻结契约
- 未提交、未推送
