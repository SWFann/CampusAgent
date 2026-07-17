---
task_id: P4-11
task_name: 完成越权测试矩阵
status: in_review
started_at: 2026-07-17T19:15:00+08:00
completed_at: 2026-07-17T20:30:00+08:00
actual_hours: 1.25
owner: Claude
auditor: Codex
---

# P4-11 开发日志：完成越权测试矩阵

## 1. 背景

P4-11 系统性覆盖 P4 所有越权路径和隐私投影。覆盖所有角色（anonymous → SYSTEM_ADMIN）和所有场景（查看组织 → 删除组织 → 目录搜索 → 组织树 → 用户组织列表），确保后端强制权限，不依赖前端隐藏按钮。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/tests/unit/test_organization_authorization_matrix.py` | 新增 | 越权测试矩阵 (13) |

## 3. 设计说明

### 3.1 角色覆盖

| 角色 | 说明 |
|------|------|
| anonymous | 未登录用户 |
| non-member | 已登录但非组织成员 |
| GUEST | 组织 GUEST 成员 |
| MEMBER | 组织 MEMBER 成员 |
| ADMIN | 组织 ADMIN 成员 |
| OWNER | 组织 OWNER |
| SYSTEM_ADMIN | 全局系统管理员 |
| SCHOOL_ADMIN | 全局学校管理员 |
| ORG_ADMIN | 全局组织管理员（不自动有权限） |

### 3.2 场景覆盖

| 场景 | 说明 |
|------|------|
| 查看 PUBLIC 组织 | 所有角色可查看 |
| 查看 MEMBERS_ONLY 组织 | 只有成员/管理员可查看 |
| 查看 PRIVATE 组织 | 只有成员/管理员可查看 |
| 查看成员列表 | OWNER/ADMIN/MEMBER 可查看 |
| 添加成员 | OWNER/ADMIN（限 MEMBER/GUEST）/系统管理员 |
| 修改角色 | OWNER/ADMIN（限 MEMBER/GUEST）/系统管理员 |
| 移除成员 | OWNER/ADMIN（限 MEMBER/GUEST）/系统管理员 |
| 删除组织 | OWNER/SYSTEM_ADMIN |
| 加入组织 | 受 join_policy 限制 |
| 退出组织 | 只有自己可退出 |
| 目录搜索 | 隐私投影安全 |
| 组织树 | 权限裁剪 |
| 用户组织列表 | PUBLIC 可见，PRIVATE 不泄露 |

### 3.3 特殊场景

| 场景 | 说明 |
|------|------|
| deleted user | 已删除用户的组织不返回 |
| archived org | 已归档组织不可见 |
| deleted org | 已删除组织不可见 |
| 跨组织隔离 | A 组织成员不能管理 B 组织 |
| ORG_ADMIN 无自动权限 | 全局 ORG_ADMIN 不等于任意组织 OWNER |

### 3.4 测试辅助

使用 `helpers_p4.py` 中的辅助函数创建不同角色的用户和组织：
- `create_test_user(global_role=...)`: 创建指定全局角色的用户
- `create_test_org(visibility=..., join_policy=...)`: 创建指定配置的组织
- `add_member_to_org(role=...)`: 添加指定角色的成员

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_anonymous_access_matrix` | 匿名用户权限矩阵 |
| `test_non_member_access_matrix` | 非成员权限矩阵 |
| `test_guest_access_matrix` | GUEST 权限矩阵 |
| `test_member_access_matrix` | MEMBER 权限矩阵 |
| `test_admin_access_matrix` | ADMIN 权限矩阵 |
| `test_owner_access_matrix` | OWNER 权限矩阵 |
| `test_system_admin_access_matrix` | SYSTEM_ADMIN 权限矩阵 |
| `test_school_admin_access_matrix` | SCHOOL_ADMIN 权限矩阵 |
| `test_org_admin_no_auto_power` | ORG_ADMIN 无自动组织权限 |
| `test_deleted_user_orgs_hidden` | 已删除用户的组织不返回 |
| `test_archived_org_invisible` | 已归档组织不可见 |
| `test_deleted_org_invisible` | 已删除组织不可见 |
| `test_cross_org_isolation` | 跨组织隔离验证 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_authorization_matrix.py -q -p no:cacheprovider
# 13 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- 测试矩阵覆盖所有角色和主要场景
- ORG_ADMIN 全局角色不自动赋予组织管理权限（按设计验证）
- 未修改冻结契约
- 未提交、未推送
