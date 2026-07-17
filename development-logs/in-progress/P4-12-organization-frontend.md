---
task_id: P4-12
task_name: 完成组织与联系人页面
status: in_review
started_at: 2026-07-17T20:30:00+08:00
completed_at: 2026-07-17T22:00:00+08:00
actual_hours: 1.5
owner: Claude
auditor: Codex
---

# P4-12 开发日志：完成组织与联系人页面

## 1. 背景

P4-12 增加基础组织和目录前端页面，不做完整 P10 App Shell。实现组织列表/创建、组织详情/成员管理、目录搜索/推荐三个页面，以及对应的 API helper。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web/src/app/organizations/page.tsx` | 新增 | 组织列表与创建页面 (193 行) |
| `apps/web/src/app/organizations/[organizationId]/page.tsx` | 新增 | 组织详情与成员管理页面 (200 行) |
| `apps/web/src/app/directory/page.tsx` | 新增 | 目录搜索与推荐页面 (154 行) |
| `apps/web/src/lib/organizations.ts` | 新增 | 组织 API helper (195 行) |
| `apps/web/src/lib/directory.ts` | 新增 | 目录 API helper (113 行) |

## 3. 设计说明

### 3.1 API Helper

**`organizations.ts`**:
- 所有请求 `credentials: "include"`
- 写请求使用 `getWriteHeaders()` 带 CSRF
- API base 使用 `NEXT_PUBLIC_API_URL` + `/api/v1`
- 不使用 localStorage/sessionStorage 存 token
- 函数: createOrganization, listOrganizations, getOrganization, updateOrganization, deleteOrganization, listMembers, addMember, updateMemberRole, removeMember, joinOrganization, leaveOrganization

**`directory.ts`**:
- 同样的安全模式
- 函数: searchDirectory, getOrganizationTree, getRecommendedOrganizations

### 3.2 组织列表页 (`/organizations`)

- 组织列表展示（name, type, visibility, member_count）
- 创建组织表单（name, type, description, visibility, join_policy）
- loading/error/empty 状态处理
- 创建成功后刷新列表

### 3.3 组织详情页 (`/organizations/[organizationId]`)

- 组织详情展示
- 成员列表展示（display_name, role, status）
- 添加成员表单（user_id, role）
- 修改角色按钮
- 移除成员按钮
- 加入/退出按钮
- 根据 API 返回权限状态隐藏无权操作入口
- 权限错误展示

### 3.4 目录页 (`/directory`)

- 搜索框
- 类型筛选：全部/用户/组织
- 搜索结果安全字段展示（不含 email/student_no）
- 推荐组织区域
- loading/error/empty 状态处理

### 3.5 前端设计原则

- 不做营销页，直接进入可用工具界面
- 保持简洁、密集、可扫描
- 不用夸张 hero
- 不用大量装饰渐变
- 不展示无权操作入口
- 显示权限错误

## 4. 测试覆盖

前端页面通过 lint/typecheck/build 验证：
- ESLint 无错误
- TypeScript 严格类型检查通过
- Next.js 生产构建成功

## 5. 自检命令和结果

```bash
corepack pnpm --filter @campus-agent/web lint
# ✓ No ESLint warnings or errors

corepack pnpm --filter @campus-agent/web typecheck
# ✓ tsc --noEmit passed

corepack pnpm --filter @campus-agent/web build
# ✓ Compiled successfully
```

## 6. 未执行项及原因

- 未配置 Playwright E2E 测试（P10/P11 阶段）
- 未实现完整的权限态前端管理（P10 App Shell 阶段）

## 7. 边界声明

- 前端只做基础可用页面，不做完整 P10 App Shell
- 前端隐藏无权操作入口，但后端仍强制权限
- 不使用 localStorage/sessionStorage 存 token
- 未修改冻结契约
- 未提交、未推送
