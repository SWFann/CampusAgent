---
task_id: P4-06
task_name: 实现加入策略
status: in_review
started_at: 2026-07-17T15:00:00+08:00
completed_at: 2026-07-17T16:00:00+08:00
actual_hours: 1.0
owner: Claude
auditor: Codex
---

# P4-06 开发日志：实现加入策略

## 1. 背景

P4-06 实现 OPEN/APPROVAL/INVITE_ONLY/CLOSED 四种加入策略和 capacity 限制。确保不同策略下自助加入行为明确，capacity 满时拒绝加入。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/organizations/service.py` | 修改 | `join_organization` 实现完整加入策略 |
| `apps/api/src/modules/organizations/api.py` | 修改 | join/leave 端点（auth + CSRF） |
| `apps/api/tests/unit/test_organization_join_policy.py` | 新增 | 加入策略测试 (8) |

## 3. 设计说明

### 3.1 加入策略行为

| 策略 | 自助 join 行为 | membership status | role |
|------|---------------|-------------------|------|
| OPEN | 直接加入 | ACTIVE | MEMBER |
| APPROVAL | 需审批 | PENDING | MEMBER |
| INVITE_ONLY | 拒绝 | — | — |
| CLOSED | 拒绝 | — | — |

- INVITE_ONLY 和 CLOSED 自助 join 返回 `ORG_INVALID_JOIN_POLICY` (400)
- APPROVAL 策略下 join 后 `joined_at` 为 None（待审批通过后设置）

### 3.2 Capacity 限制

- `capacity` 为 None 时不限制
- `capacity` >= 1 时，当前 ACTIVE 成员数 >= capacity 则拒绝
- OPEN 策略下 join 前检查 capacity
- 管理员通过 `add_member` 添加成员时也检查 capacity
- 返回 `ORG_CAPACITY_EXCEEDED` (409)

### 3.3 重复加入处理

- 已是 ACTIVE/PENDING/INVITED 成员 → `ORG_MEMBER_ALREADY_EXISTS` (409)
- LEFT/REMOVED 状态 → 复用行恢复（按 join_policy 决定新 status）
- 不为同一用户和组织创建多条当前权威 membership

### 3.4 加入策略与成员添加的区别

- `join_organization`: 自助加入，受 join_policy 限制
- `add_member`: 管理员添加，不受 join_policy 限制（但受 capacity 限制和权限限制）
- ADMIN 通过 add_member 可以添加成员到 INVITE_ONLY/CLOSED 组织

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_open_join_active` | OPEN join → ACTIVE MEMBER |
| `test_approval_join_pending` | APPROVAL join → PENDING MEMBER |
| `test_invite_only_join_denied` | INVITE_ONLY join → ORG_INVALID_JOIN_POLICY |
| `test_closed_join_denied` | CLOSED join → ORG_INVALID_JOIN_POLICY |
| `test_already_member_join` | 已是成员 join → ORG_MEMBER_ALREADY_EXISTS |
| `test_capacity_exceeded_join` | capacity 满 join → ORG_CAPACITY_EXCEEDED |
| `test_admin_add_bypasses_join_policy` | 管理员添加不受 join_policy 限制 |
| `test_admin_add_respects_capacity` | 管理员添加也受 capacity 限制 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_organization_join_policy.py -q -p no:cacheprovider
# 8 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证
- APPROVAL 策略的审批流程（PENDING → ACTIVE）未在 P4 实现（MVP 仅记录 PENDING 状态）

## 7. 边界声明

- APPROVAL 策略下 PENDING 成员的审批接口未实现（P5+ 或后续迭代）
- capacity 检查在 service 层执行，不依赖数据库约束
- 未修改冻结契约
- 未提交、未推送
