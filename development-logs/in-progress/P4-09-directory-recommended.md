---
task_id: P4-09
task_name: 实现推荐占位规则
status: in_review
started_at: 2026-07-17T17:45:00+08:00
completed_at: 2026-07-17T18:30:00+08:00
actual_hours: 0.75
owner: Claude
auditor: Codex
---

# P4-09 开发日志：实现推荐占位规则

## 1. 背景

P4-09 实现 `GET /api/v1/directory/recommended`，只使用非敏感组织关系进行推荐，不做隐性画像，不读取私有偏好/聊天/消息/记忆。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/directory/schemas.py` | 修改 | 新增 DirectoryRecommendedResponse |
| `apps/api/src/modules/directory/service.py` | 修改 | 新增 get_recommended_organizations |
| `apps/api/src/modules/directory/api.py` | 修改 | 新增 recommended 端点 |
| `apps/api/tests/unit/test_directory_recommended.py` | 新增 | 推荐测试 (6) |

## 3. 设计说明

### 3.1 推荐规则

**匿名用户**:
- 返回一些 PUBLIC 组织作为通用推荐
- reason: `"public_organization"`

**已登录用户**:
- **策略 1: 同父组织 PUBLIC 推荐**
  - 获取用户当前所有组织 membership
  - 对每个组织，查找同父组织下的兄弟 PUBLIC 组织
  - 排除用户已加入的组织
  - reason: `"same_parent_public_organization"`

- **策略 2: PUBLIC CLUB/COURSE/TEAM 推荐**
  - 查找用户未加入的 PUBLIC 类型 CLUB/COURSE/TEAM 组织
  - 按 created_at 降序排列
  - reason: `"public_club_course_team"`

- 如果无安全推荐，返回空数组

### 3.2 隐私保证

- **不做隐性画像**: 不读取用户偏好、聊天、消息、记忆
- **不使用敏感字段**: 不使用 email, student_no, bio, password_hash, token
- **只使用组织关系**: 基于用户已有的组织 membership 推导
- **可解释**: 每个推荐包含 `reason` 字段

### 3.3 返回字段

```json
{
  "recommendations": [
    {
      "id": "uuid",
      "name": "组织名称",
      "type": "CLUB",
      "visibility": "PUBLIC",
      "reason": "same_parent_public_organization"
    }
  ],
  "total": 1
}
```

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_anonymous_returns_public` | 未登录返回 PUBLIC 推荐 |
| `test_logged_in_no_orgs_returns_empty` | 登录但无组织关系返回空推荐 |
| `test_same_parent_recommendation` | 有组织关系时推荐同 parent PUBLIC 组织 |
| `test_private_not_recommended` | PRIVATE 不推荐给非成员 |
| `test_recommendation_includes_reason` | 推荐结果包含 reason |
| `test_no_sensitive_fields` | 不使用 email/student_no/bio/password_hash |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_directory_recommended.py -q -p no:cacheprovider
# 6 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- 推荐算法是 MVP 占位规则，后续可扩展（但不得引入隐性画像）
- 未使用协同过滤或用户画像
- 未修改冻结契约
- 未提交、未推送
