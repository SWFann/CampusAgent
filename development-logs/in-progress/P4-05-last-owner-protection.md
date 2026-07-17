---
task_id: P4-05
task_name: 保护最后一个 Owner
status: in_review
started_at: 2026-07-17T14:00:00+08:00
completed_at: 2026-07-17T15:00:00+08:00
actual_hours: 1.0
owner: Claude
auditor: Codex
---

# P4-05 开发日志：保护最后一个 Owner

## 1. 背景

P4-05 确保组织的最后一个 OWNER 不能通过退出、被移除或被降级的方式离开组织，防止组织失去管理者。同时实现所有权转让逻辑。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/service.py` | 修改 | leave/remove/update_role 中加入最后 OWNER 保护 |
| `apps/api/src/modules/organizations/permissions.py` | 修改 | 新增 `can_transfer_ownership` 方法 |
| `apps/api/tests/unit/test_organization_owner_protection.py` | 新增 | 最后 OWNER 保护测试 (7) |

## 3. 设计说明

### 3.1 保护机制

在 `leave_organization`、`remove_member` 和 `update_member_role` 三个函数中，操作前检查目标是否为最后一个 OWNER：

```python
if membership.role == OrganizationRole.OWNER.value:
    owner_count = mem_repo.count_active_owners(org.id)
    if owner_count <= 1:
        raise OrganizationLastOwnerError(...)
```

### 3.2 保护路径

| 路径 | 保护行为 |
|------|---------|
| 最后 OWNER 退出 | `ORG_LAST_OWNER_CANNOT_LEAVE` (409) |
| 最后 OWNER 被移除 | `ORG_LAST_OWNER_CANNOT_LEAVE` (409) |
| 最后 OWNER 被降级 | `ORG_LAST_OWNER_CANNOT_LEAVE` (409) |
| 删除组织绕过 | 不适用（删除组织是 OWNER/SYSTEM_ADMIN 显式操作，不是 membership 删除绕过） |

### 3.3 所有权转让

- 只有当前 OWNER 或 SYSTEM_ADMIN 可以转让所有权
- 转让方式：通过 `update_member_role` 将目标用户升为 OWNER
- 如果当前 OWNER 是最后一个，先将当前 OWNER 降级为 ADMIN/MEMBER，再将目标升为 OWNER
- 但降级最后一个 OWNER 会触发保护 → 因此转让逻辑是先升新 OWNER（此时有两个 OWNER），再降旧 OWNER
- ADMIN 不能转让所有权（`can_transfer_ownership` 返回 False）

### 3.4 非最后 OWNER

- 如果组织有多个 OWNER（通过 `add_member` 添加 OWNER），则任何一个 OWNER 可以退出/被移除/被降级
- `count_active_owners` 只统计 status=ACTIVE 且 role=OWNER 的记录

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_last_owner_cannot_leave` | 最后 OWNER 退出返回 ORG_LAST_OWNER_CANNOT_LEAVE |
| `test_last_owner_cannot_be_removed` | 最后 OWNER 被移除返回 ORG_LAST_OWNER_CANNOT_LEAVE |
| `test_last_owner_cannot_be_demoted` | 最后 OWNER 降级返回 ORG_LAST_OWNER_CANNOT_LEAVE |
| `test_non_last_owner_can_leave` | 非最后 OWNER 可退出 |
| `test_non_last_owner_can_be_removed` | 非最后 OWNER 可被移除 |
| `test_admin_cannot_promote_to_owner` | ADMIN 不能把任何人升为 OWNER |
| `test_owner_transfer_ownership` | OWNER 转让所有权（先升新 OWNER，再降旧 OWNER） |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_owner_protection.py -q -p no:cacheprovider
# 7 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- 删除组织采用软删除，由 OWNER 或 SYSTEM_ADMIN 显式执行，不存在通过 membership 删除绕过最后 OWNER 保护的问题
- 一个组织 MVP 只允许一个 OWNER（通过 add_member 添加 OWNER 时需先处理转让）
- 未修改冻结契约
- 未提交、未推送
