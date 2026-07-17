---
task_id: P4-07
task_name: 实现目录搜索
status: in_review
started_at: 2026-07-17T16:00:00+08:00
completed_at: 2026-07-17T17:00:00+08:00
actual_hours: 1.0
owner: Claude
auditor: Codex
---

# P4-07 开发日志：实现目录搜索

## 1. 背景

P4-07 实现 `GET /api/v1/directory/search`，支持用户和组织搜索。隐私投影安全：不搜索/不返回 email、student_no、password_hash、bio 等敏感字段；组织搜索按 visibility 过滤。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/directory/schemas.py` | 重写 | DirectorySearchType, DirectoryUserResult, DirectoryOrganizationResult, DirectorySearchResponse |
| `apps/api/src/modules/directory/exceptions.py` | 重写 | 4 个 AppError 子类 |
| `apps/api/src/modules/directory/service.py` | 重写 | search_directory + _search_users + _search_organizations |
| `apps/api/src/modules/directory/api.py` | 重写 | search/tree/recommended 端点 |
| `apps/api/src/main.py` | 修改 | 注册 directory 路由 |
| `apps/api/tests/unit/test_directory_search.py` | 新增 | 搜索测试 (11) |

## 3. 设计说明

### 3.1 搜索参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `q` | str | — | 搜索关键词（必填） |
| `type` | str | "all" | all/users/organizations |
| `limit` | int | 20 | 每类最大返回数 |
| `offset` | int | 0 | 分页偏移 |

### 3.2 用户搜索隐私投影

- **搜索字段**: 只搜 `display_name`（ilike 模糊匹配）
- **不搜索**: email, student_no, bio
- **不返回**: email, student_no, password_hash, bio
- **返回字段**: id, display_name, avatar_url, profile_visibility
- **过滤**: 只返回 status=ACTIVE 的用户（排除 DELETED/DISABLED）

### 3.3 组织搜索隐私投影

- **搜索字段**: name, slug（ilike 模糊匹配）
- **可见性过滤**:
  - PUBLIC: 对所有人可见
  - MEMBERS_ONLY: 对组织成员可见
  - PRIVATE: 对组织成员或系统权限可见
- **过滤**: 排除 DELETED/ARCHIVED 组织
- **返回字段**: id, name, type, visibility, status, member_count

### 3.4 错误处理

| 错误码 | HTTP 状态 | 触发条件 |
|--------|----------|---------|
| DIRECTORY_QUERY_TOO_SHORT | 400 | q.strip() 长度 < 2 |
| DIRECTORY_INVALID_TYPE | 400 | type 非 all/users/organizations |

### 3.5 分页策略

- MVP 使用 limit + offset 简单分页
- 搜索结果按 display_name/name 升序排序
- 如果 API_CONTRACT 后续要求 cursor 分页，报告中说明 MVP 处理

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_query_too_short` | query < 2 字符返回 DIRECTORY_QUERY_TOO_SHORT |
| `test_invalid_type` | 无效 type 返回 DIRECTORY_INVALID_TYPE |
| `test_search_users_by_name` | 按 display_name 搜索用户 |
| `test_search_users_no_email` | 用户结果不含 email |
| `test_search_users_no_student_no` | 用户结果不含 student_no |
| `test_search_excludes_deleted_users` | 已删除用户不返回 |
| `test_search_organizations_public` | PUBLIC 组织可被搜索 |
| `test_search_private_hidden` | PRIVATE 对非成员不返回 |
| `test_member_can_search_private` | 成员可搜索到自己的 PRIVATE 组织 |
| `test_search_excludes_deleted_orgs` | 已删除组织不返回 |
| `test_search_all_type` | type=all 同时返回用户和组织 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_directory_search.py -q -p no:cacheprovider
# 11 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- 分页使用 limit+offset，未实现 cursor 分页（MVP 策略）
- 用户搜索不搜索 bio（MVP 统一不返回 bio）
- 未修改冻结契约
- 未提交、未推送
