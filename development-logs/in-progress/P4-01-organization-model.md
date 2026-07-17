---
task_id: P4-01
task_name: 设计组织模型
status: in_review
started_at: 2026-07-17T08:00:00+08:00
completed_at: 2026-07-17T09:30:00+08:00
actual_hours: 1.5
owner: Claude
auditor: Codex
---

# P4-01 开发日志：设计组织模型

## 1. 背景

P4-01 是 P4 阶段的基础任务，建立组织与成员关系的数据库模型、Repository 基线和 Alembic 迁移。需要创建 `Organization` 和 `OrganizationMembership` 两个 ORM 模型、六个枚举类型和对应的数据库迁移，为后续 CRUD、成员生命周期和权限控制奠定数据基础。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/models.py` | 重写 | Organization、OrganizationMembership ORM 模型及 6 个枚举 |
| `apps/api/alembic/versions/0003_organization_membership_tables.py` | 新增 | 创建两张表、7 个索引、1 个唯一约束的迁移 |
| `apps/api/tests/conftest.py` | 修改 | 导入组织模型以便 Base.metadata.create_all 注册 |
| `apps/api/tests/unit/test_alembic.py` | 修改 | 更新迁移测试反映新表 |
| `apps/api/tests/unit/test_organization_models.py` | 新增 | 模型和迁移测试 (9) |

## 3. 设计说明

### 3.1 Organization 模型

- **表名**: `organizations`
- **主键**: UUID v4（通过 `new_uuid()` 生成）
- **自引用关系**: `parent_id` → `organizations.id`，支持组织树结构
- **枚举字段**:
  - `type`: SCHOOL/COLLEGE/DEPARTMENT/CLASS/DORM/CLUB/COURSE/TEAM/OTHER
  - `visibility`: PUBLIC/MEMBERS_ONLY/PRIVATE
  - `join_policy`: OPEN/APPROVAL/INVITE_ONLY/CLOSED
  - `status`: ACTIVE/ARCHIVED/DELETED
- **软删除**: `status=DELETED` + `deleted_at`
- **时间戳**: `created_at`、`updated_at`（UTC timezone-aware）
- **关系**: `parent`/`children`（自引用）、`memberships`（一对多）
- **`__repr__`**: 只输出 id、name、type、status，不泄露敏感字段

### 3.2 OrganizationMembership 模型

- **表名**: `organization_memberships`
- **主键**: UUID v4
- **外键**: `organization_id` → `organizations.id`、`user_id` → `users.id`、`invited_by` → `users.id`
- **唯一约束**: `(organization_id, user_id)` — 同一用户在同一组织只有一条权威记录
- **枚举字段**:
  - `role`: OWNER/ADMIN/MEMBER/GUEST
  - `status`: INVITED/PENDING/ACTIVE/LEFT/REMOVED
- **状态转换**: INVITED → ACTIVE → LEFT/REMOVED，复用同一行
- **`__repr__`**: 只输出 id、org_id、user_id、role、status

### 3.3 迁移设计

- 迁移文件 `0003_organization_membership_tables.py`，`down_revision = "0002_user_auth_tables"`
- 创建 `organizations` 表（含 parent_id 自引用外键）
- 创建 `organization_memberships` 表（含两个外键到 users、一个外键到 organizations）
- 7 个索引：parent_id、type、status、organization_id、user_id、role、status
- 1 个唯一约束：`uq_organization_memberships_org_user`
- 使用 `server_default` 设置枚举默认值
- 降级按依赖逆序删除表

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_create_organization_success` | 创建 Organization 成功 |
| `test_organization_defaults` | 默认 visibility/join_policy/status 正确 |
| `test_parent_child_relationship` | 父子关系可用 |
| `test_create_membership_success` | 创建 OrganizationMembership 成功 |
| `test_membership_unique_constraint` | (org_id, user_id) 唯一约束 |
| `test_membership_defaults` | role/status 默认值正确 |
| `test_org_repr_no_sensitive_data` | repr 不泄露敏感字段 |
| `test_alembic_upgrade_creates_tables` | 迁移后两张表存在 |
| `test_alembic_downgrade_upgrade_cycle` | 升级→降级→升级可重复 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent ruff check apps/api/src/modules/organizations/models.py apps/api/alembic/versions/0003_organization_membership_tables.py --no-cache
# All checks passed!

conda run -n CampusAgent mypy apps/api/src/modules/organizations/models.py --no-incremental
# Success: no issues found

conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_models.py apps/api/tests/unit/test_alembic.py -q -p no:cacheprovider
# 15 passed (9 org model + 6 alembic)
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证（Docker 在本环境不可用）
- 未执行完整 `pip check`（在后续 P4 全量验证中统一执行）

## 7. 边界声明

- 未实现组织 CRUD API（P4-02）
- 未实现成员生命周期（P4-03）
- 未修改 P0/P1 冻结契约
- 未提交、未推送
