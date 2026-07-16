---
task_id: P3-12
task_name: 完成登录注册页面
status: in_review
started_at: 2026-07-16T23:45:00+08:00
completed_at: 2026-07-17T00:05:00+08:00
actual_hours: 0.33
owner: Claude
auditor: Codex
---

# P3-12 开发日志：完成登录注册页面

## 1. 背景

P3-12 在 Next.js 前端增加登录和注册页面，并提供 API client 与 CSRF helper。P3 前端只做身份入口，不实现完整 App Shell 和路由守卫；这些留给 P10。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web/src/app/login/page.tsx` | 新增 | 登录页面 |
| `apps/web/src/app/register/page.tsx` | 新增 | 注册页面 |
| `apps/web/src/lib/api.ts` | 新增/修改 | API client，`credentials: include`，支持 `NEXT_PUBLIC_API_URL` |
| `apps/web/src/lib/csrf.ts` | 新增 | 从 cookie 读取 csrf_token 并写入 `X-CSRF-Token` |

## 3. 核心行为

- 登录表单提交 email/password 到 `/api/v1/auth/login`。
- 注册表单提交 email/password/display_name/student_no 到 `/api/v1/auth/register`。
- API client 所有请求使用 `credentials: "include"`，配合 HttpOnly Cookie。
- 写请求通过 `getWriteHeaders()` 自动带 JSON content-type 和 CSRF header。
- API base URL 使用 `NEXT_PUBLIC_API_URL`，未设置时回退同源 `/api/v1`。

## 4. Codex 审计修正

- 原 API client 固定 `"/api/v1"`，在前后端不同端口部署时会打到 web origin。已改为读取 `NEXT_PUBLIC_API_URL` 后拼接 `/api/v1`。
- `next build` 确认生成 `/login` 与 `/register` 两个路由。

## 5. 验证

```bash
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

结果：lint/typecheck/test/build 均通过；构建路由包含 `/login` 和 `/register`。

## 6. 边界声明

- 未实现完整登录态 App Shell。
- 未实现前端 E2E。
- 未使用 localStorage 保存 token。
