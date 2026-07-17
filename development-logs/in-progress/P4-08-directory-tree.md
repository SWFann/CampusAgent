---
task_id: P4-08
task_name: 实现组织树
status: in_review
started_at: 2026-07-17T17:00:00+08:00
completed_at: 2026-07-17T17:45:00+08:00
actual_hours: 0.75
owner: Claude
auditor: Codex
---

# P4-08 开发日志：实现组织树

## 1. 背景

P4-08 实现 `GET /api/v1/directory/tree`，按当前用户权限裁剪组织树。PRIVATE/MEMBERS_ONLY 节点对无权用户不可见，DELETED/ARCHIVED 节点不返回。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/api/src/modules/directory/schemas.py` | 修改 | 新增 DirectoryTreeNode, DirectoryTreeResponse |
| `apps/api/src/modules/directory/service.py` | 修改 | 新增 get_organization_tree 递归构建 |
| `apps/api/src/modules/directory/api.py` | 修改 | 新增 tree 端点 |
| `apps/api/tests/unit/test_directory_tree.py` | 新增 | 组织树测试 (8) |

## 3. 设计说明

### 3.1 端点参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `root_organization_id` | UUID \| None | None | 指定根节点，None 返回所有根节点 |
| `max_depth` | int | 3 | 最大深度，安全上限 5 |

### 3.2 递归构建逻辑

```python
def _build_node(org, depth):
    if not _can_view(org):
        return None  # 跳过无权查看的节点
    children = []
    if depth < max_depth:
        for child in repo.get_children(org.id):
            node = _build_node(child, depth + 1)
            if node is not None:
                children.append(node)
    return {id, name, type, visibility, status, parent_id, children}
```

### 3.3 权限裁剪

- 每个节点通过 `permission_service.can_view_organization` 检查
- PUBLIC 节点可见
- MEMBERS_ONLY/PRIVATE 节点仅对成员或系统权限可见
- 不可见的节点不返回，其子节点也不返回（整棵子树裁剪）
- 不返回成员列表和敏感字段，只返回组织安全投影

### 3.4 错误处理

| 错误码 | HTTP 状态 | 触发条件 |
|--------|----------|---------|
| DIRECTORY_TREE_TOO_DEEP | 400 | max_depth > 5 |
| DIRECTORY_ORG_NOT_FOUND | 404 | root 不存在或无权查看 |

### 3.5 max_depth 约束

- API 层不设 `le=5` 约束（避免 FastAPI 422 先于业务逻辑报错）
- Service 层检查 `max_depth > MAX_TREE_DEPTH` → 抛出 `DirectoryTreeTooDeepError`
- `MAX_TREE_DEPTH = 5`

## 4. 测试覆盖

| 测试 | 说明 |
|------|------|
| `test_tree_no_root_returns_public_roots` | 无 root 返回 PUBLIC 根节点 |
| `test_tree_with_root_returns_subtree` | 指定 root 返回子树 |
| `test_tree_root_not_found` | root 不存在返回 DIRECTORY_ORG_NOT_FOUND |
| `test_tree_max_depth_exceeded` | max_depth > 5 返回 DIRECTORY_TREE_TOO_DEEP |
| `test_tree_private_child_hidden` | PRIVATE 子节点对非成员裁剪 |
| `test_tree_members_only_visible_to_member` | MEMBERS_ONLY 子节点对成员可见 |
| `test_tree_excludes_deleted` | DELETED/ARCHIVED 节点不返回 |
| `test_tree_default_depth_3` | 默认 max_depth=3 |

## 5. 自检命令和结果

```bash
conda run -n CampusAgent python -m pytest apps/api/tests/unit/test_directory_tree.py -q -p no:cacheprovider
# 8 passed
```

## 6. 未执行项及原因

- 未执行 Docker compose 验证

## 7. 边界声明

- 递归构建在 service 层执行，未使用 SQL 递归 CTE（MVP 策略，组织数量有限）
- 深度限制在 service 层检查，不在 API 层使用 FastAPI 约束
- 未修改冻结契约
- 未提交、未推送
