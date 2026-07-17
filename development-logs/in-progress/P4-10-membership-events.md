---
task_id: P4-10
task_name: 发布成员领域事件
status: in_review
started_at: 2026-07-17T18:30:00+08:00
completed_at: 2026-07-17T19:15:00+08:00
actual_hours: 0.75
owner: Claude
auditor: Codex
---

# P4-10 开发日志：发布成员领域事件

## 1. 背景

P4-10 发布组织创建和成员变更领域事件，使用 P2 事件总线 `default_event_bus`，不新建不兼容事件总线。事件在 commit 成功后发布，只包含 ID、role、status 等安全字段。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/events.py` | 重写 | 5 个 DomainEvent 子类 |
| `apps/api/src/modules/organizations/service.py` | 修改 | 在所有 commit 后发布事件 |
| `apps/api/tests/unit/test_organization_events.py` | 新增 | 事件测试 (8) |

## 3. 设计说明

### 3.1 事件类型

| 事件 | 触发时机 | 继承 |
|------|---------|------|
| `OrganizationCreated` | 创建组织后 | DomainEvent |
| `OrganizationArchived` | 归档/删除组织后 | DomainEvent |
| `OrganizationMemberJoined` | 添加成员/加入后 | DomainEvent |
| `OrganizationMemberLeft` | 退出/移除成员后 | DomainEvent |
| `OrganizationMemberRoleChanged` | 修改成员角色后 | DomainEvent |

### 3.2 事件字段

所有事件使用 `@dataclass(frozen=True)`，字段只包含安全信息：

```python
@dataclass(frozen=True)
class OrganizationMemberJoined(DomainEvent):
    event_id: str          # 唯一事件 ID
    organization_id: UUID  # 组织 ID
    user_id: UUID          # 目标用户 ID
    actor_id: UUID         # 操作者 ID
    role: str              # 角色
    status: str            # 成员状态
    occurred_at: datetime  # 发生时间
```

### 3.3 隐私要求

- **不包含**: email, student_no, password_hash, token, session, bio
- **只包含**: ID, role, status, action, occurred_at
- 事件 ID 使用 `secrets.token_hex(16)` 生成

### 3.4 发布规则

- 事件在 `session.commit()` 成功后通过 `default_event_bus.publish()` 发布
- 测试中使用 `default_event_bus.clear()` 或 fixture 隔离订阅者
- handler 异常不阻断主流程（沿用 P2 EventBus 语义）
- 每个操作只发布一次事件

### 3.5 事件发布位置

| Service 函数 | 发布事件 |
|-------------|---------|
| `create_organization` | OrganizationCreated |
| `delete_organization` | OrganizationArchived (action="deleted") |
| `add_member` | OrganizationMemberJoined |
| `update_member_role` | OrganizationMemberRoleChanged |
| `remove_member` | OrganizationMemberLeft (action="removed") |
| `join_organization` | OrganizationMemberJoined |
| `leave_organization` | OrganizationMemberLeft (action="left") |

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_create_org_publishes_event` | 创建组织发布 OrganizationCreated 一次 |
| `test_add_member_publishes_event` | add_member 发布 OrganizationMemberJoined 一次 |
| `test_leave_publishes_event` | leave 发布 OrganizationMemberLeft 一次 |
| `test_role_change_publishes_event` | 角色变更发布 OrganizationMemberRoleChanged 一次 |
| `test_remove_publishes_event` | remove 发布 OrganizationMemberLeft 一次 |
| `test_event_no_email` | 事件不包含 email |
| `test_event_no_student_no` | 事件不包含 student_no |
| `test_event_no_password` | 事件不包含 password/token |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_events.py -q -p no:cacheprovider
# 8 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证
- 未实现跨进程事件发布（MVP 使用进程内事件总线）

## 7. 边界声明

- 事件使用 P2 `default_event_bus`，不新建不兼容事件总线
- 事件只包含 ID/role/status，不含敏感正文
- 未修改冻结契约
- 未提交、未推送
