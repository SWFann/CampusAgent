---
task_id: P4-04
task_name: 实现组织角色
status: in_review
started_at: 2026-07-17T12:30:00+08:00
completed_at: 2026-07-17T14:00:00+08:00
actual_hours: 1.5
owner: Claude
auditor: Codex
---

# P4-04 开发日志：实现组织角色

## 1. 背景

P4-04 建立集中权限策略服务 `OrganizationPermissionService`，覆盖全局角色（SYSTEM_ADMIN, SCHOOL_ADMIN, ORG_ADMIN）和组织角色（OWNER, ADMIN, MEMBER, GUEST）的完整权限矩阵。所有组织动作由权限服务判定，不依赖前端隐藏按钮。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/permissions.py` | 重写 | OrganizationPermissionService 集中权限服务 |
| `apps/api/src/modules/organizations/service.py` | 修改 | 所有 service 函数接入权限服务 |
| `apps/api/tests/unit/test_organization_permissions.py` | 新增 | 权限矩阵测试 (20) |

## 3. 设计说明

### 3.1 OrganizationPermissionService

集中式权限服务，单例 `permission_service` 供全局复用。

**核心方法**:

| 方法 | 说明 |
|------|------|
| `can_view_organization` | 查看组织详情 |
| `can_view_members` | 查看成员列表 |
| `can_update_organization` | 更新组织信息 |
| `can_delete_organization` | 删除组织 |
| `can_add_member` | 添加成员（按目标角色） |
| `can_remove_member` | 移除成员 |
| `can_change_member_role` | 修改成员角色 |
| `can_transfer_ownership` | 转让所有权 |

### 3.2 权限矩阵

| Actor | View PUBLIC | View PRIVATE/MEMBERS_ONLY | View Members | Add Member | Change Role | Delete Org |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| anonymous | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| non-member | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GUEST | ✅ | limited | PUBLIC only | ❌ | ❌ | ❌ |
| MEMBER | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| ADMIN | ✅ | ✅ | ✅ | MEMBER/GUEST | MEMBER/GUEST | ❌ |
| OWNER | ✅ | ✅ | ✅ | all | all | ✅ |
| SYSTEM_ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SCHOOL_ADMIN | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (P4 MVP 可管理) |
| ORG_ADMIN | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 3.3 关键设计决策

- **ORG_ADMIN 不自动等于任意组织 OWNER**: 全局 ORG_ADMIN 角色不赋予任何组织管理权限，只有组织 membership 才可管理组织
- **SCHOOL_ADMIN P4 MVP**: 可管理全部组织，后续按学校范围收窄（已在日志声明）
- **ADMIN 不能操作 OWNER**: ADMIN 不能移除、修改 OWNER，不能把任何人升为 OWNER
- **GUEST 受限**: 只能查看 PUBLIC 组织的成员列表，不能查看 MEMBERS_ONLY/PRIVATE 的成员
- **非成员只能查看 PUBLIC**: MEMBERS_ONLY/PRIVATE 对非成员完全不可见

### 3.4 权限检查集成

所有 service 函数在执行操作前调用 `permission_service` 对应方法：
- `create_organization`: 任何 authenticated user 可创建
- `get_organization`: `can_view_organization`
- `update_organization`: `can_update_organization`
- `delete_organization`: `can_delete_organization`
- `add_member`: `can_add_member`
- `list_members`: `can_view_members`
- `update_member_role`: `can_change_member_role` + `can_transfer_ownership`（如果升为 OWNER）
- `remove_member`: `can_remove_member`
- `join_organization`: 任何 authenticated user 可尝试（受 join_policy 限制）
- `leave_organization`: 只有自己可 leave

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_anonymous_view_public` | 匿名可查看公开组织 |
| `test_anonymous_cannot_view_private` | 匿名不能查看私有组织 |
| `test_non_member_view_public` | 非成员可查看公开组织 |
| `test_non_member_cannot_view_private` | 非成员不能查看私有组织 |
| `test_guest_view_limited` | GUEST 受限查看 |
| `test_guest_cannot_view_private_members` | GUEST 不能查看私有组织成员 |
| `test_member_view_all` | MEMBER 可查看所有可见组织 |
| `test_member_cannot_manage` | MEMBER 不能管理 |
| `test_admin_add_member_guest` | ADMIN 可添加 MEMBER/GUEST |
| `test_admin_cannot_add_owner` | ADMIN 不能添加 OWNER |
| `test_admin_cannot_operate_owner` | ADMIN 不能操作 OWNER |
| `test_owner_full_access` | OWNER 完全访问 |
| `test_owner_delete_org` | OWNER 可删除组织 |
| `test_system_admin_full_access` | SYSTEM_ADMIN 完全访问 |
| `test_system_admin_delete_any` | SYSTEM_ADMIN 可删除任何组织 |
| `test_school_admin_manage` | SCHOOL_ADMIN 可管理 |
| `test_org_admin_no_auto_power` | ORG_ADMIN 不自动有权限 |
| `test_admin_can_update_org` | ADMIN 可更新组织 |
| `test_admin_cannot_delete_org` | ADMIN 不能删除组织 |
| `test_member_can_leave` | MEMBER 可退出 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_permissions.py -q -p no:cacheprovider
# 20 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- ORG_ADMIN 全局角色不自动赋予组织管理权限（按设计）
- SCHOOL_ADMIN 可管理全部组织是 P4 MVP 策略，后续需按学校范围收窄
- 未修改冻结契约
- 未提交、未推送
