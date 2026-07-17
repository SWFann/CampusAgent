# P10 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P10「前端产品闭环与管理后台」完整执行指令。执行方必须在 `/root/CampusAgent` 中按顺序完成 P10-01 至 P10-15。不得跳任务，不得执行 P11+，不得提交，不得推送。完成后写入 `docs/development/P10-COMPLETION-REPORT.md`，等待 Codex 审计。

## 0. 一句话目标

P10 的目标是把 P3 账号体系、P4 组织目录、P5 会话消息、P6 智能体/记忆、P7 模型网关、P8 场景框架、P9 聚餐场景串成一个真实可演示、可回归测试、不会泄露敏感数据的前端产品闭环，并补齐最小管理后台。

## 1. 当前项目背景

项目路径固定为：

```bash
cd /root/CampusAgent
```

当前项目已经完成的阶段：

- P0/P1：冻结契约、威胁模型、隐私测试矩阵、工程边界已收口。
- P2：基础设施、配置、PostgreSQL、Redis、API Envelope、请求上下文、日志脱敏、事件总线、Repository/UoW、OpenAPI、Metrics 已完成。
- P3：账号、认证、JWT、HttpOnly Cookie、CSRF、用户资料、软删除、会话撤销、限流已完成。
- P4：组织、成员、邀请、组织内目录、权限边界、前端组织页面已完成。
- P5：会话、消息、参与者、WebSocket 已完成或将作为 P10 页面基础。
- P6：智能体、记忆、授权、审计、隐私边界已完成或将作为 P10 页面基础。
- P7：模型网关、Provider、路由、节点、观测接口已完成或将作为 P10 管理后台基础。
- P8：场景框架、参与者、状态机、策略接口、候选/投票/确认基础已完成。
- P9：聚餐场景最小闭环、私有偏好、候选生成、投票/确认、TTL 清理已完成。

P10 不负责重新实现后端业务逻辑。P10 只做前端产品闭环和最小管理视图。如果发现后端接口缺少必要字段，优先在前端做兼容展示；只有在页面无法完成最小闭环时，才允许增加很薄的 read-only API 或 response 字段，并必须补测试和说明。

## 2. 开始前必须执行的检查

执行方先运行：

```bash
cd /root/CampusAgent
git status --short --branch
git log -1 --oneline
```

要求：

- 确认当前分支是 `main`。
- 记录基准提交 hash。
- 如果存在未提交修改，必须判断是否属于 P4/P5/P6/P7/P8/P9 已完成但尚未提交的预期修改。
- 不得回滚他人修改。
- 不得使用 `git reset --hard`、`git checkout -- .`、`git clean -fd`。

## 3. 必读文件

执行前必须阅读下列文件，并在 P10 完成报告中写明已阅读：

```text
docs/project/README.md
docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
docs/development/DEVELOPMENT_PLAN.md
docs/api/API_CONTRACT.md
docs/api/WEBSOCKET_CONTRACT.md
docs/privacy/THREAT_MODEL.md
docs/privacy/PRIVACY_TEST_MATRIX.md
docs/development/P3-COMPLETION-REPORT.md
docs/development/P4-COMPLETION-REPORT.md
docs/development/P5-COMPLETION-REPORT.md
docs/development/P6-COMPLETION-REPORT.md
docs/development/P7-COMPLETION-REPORT.md
docs/development/P8-COMPLETION-REPORT.md
docs/development/P9-COMPLETION-REPORT.md
```

如果某个 P5-P9 完成报告暂不存在，执行方必须改读对应 `development-logs/in-progress/P*-*.md` 日志，并在完成报告中说明。

## 4. 冻结边界和禁止事项

P10 不允许修改以下文件的契约语义：

```text
docs/api/API_CONTRACT.md
docs/api/WEBSOCKET_CONTRACT.md
docs/privacy/THREAT_MODEL.md
docs/privacy/PRIVACY_TEST_MATRIX.md
docs/project/P0_COMPLETION_SUMMARY.md
docs/project/P1_COMPLETION_SUMMARY.md
```

P10 禁止：

- 不允许把 access token、refresh token 写入 `localStorage` 或 `sessionStorage`。
- 不允许在 URL query 中放 token、私有偏好、消息正文、记忆正文。
- 不允许在 console、错误边界、指标、日志面板中展示私有偏好正文。
- 不允许管理后台提供个人私有偏好正文读取入口。
- 不允许把未实现功能伪装为已可用。
- 不允许新增真实密钥、真实模型 endpoint、Kuboard 账号密码、飞书 token。
- 不允许提交或推送。

## 5. 技术栈和既有约定

前端通常位于：

```text
apps/web/src/app/
apps/web/src/components/
apps/web/src/lib/
apps/web/src/styles/
apps/web/tests/
```

后端通常位于：

```text
apps/api/src/
apps/api/tests/
```

优先复用项目现有技术栈：

- Next.js App Router
- TypeScript
- React
- pnpm workspace
- Python FastAPI
- pytest
- ruff
- mypy

前端请求必须使用已有 API client 或统一封装。所有跨站写请求必须携带 CSRF。所有浏览器 API 调用必须使用 `credentials: "include"`。

## 6. 建议文件规划

执行方需要先查看实际项目结构，再按现有命名风格落地。建议文件如下：

```text
apps/web/src/components/app/AppShell.tsx
apps/web/src/components/app/NavRail.tsx
apps/web/src/components/app/TopBar.tsx
apps/web/src/components/app/RouteGuard.tsx
apps/web/src/components/ui/LoadingState.tsx
apps/web/src/components/ui/EmptyState.tsx
apps/web/src/components/ui/ErrorState.tsx
apps/web/src/components/ui/OfflineState.tsx
apps/web/src/components/ui/StatusBadge.tsx
apps/web/src/components/privacy/PrivacyNotice.tsx
apps/web/src/components/privacy/DangerConfirm.tsx
apps/web/src/lib/api/client.ts
apps/web/src/lib/api/types.ts
apps/web/src/lib/security/storage-audit.ts
apps/web/src/app/page.tsx
apps/web/src/app/messages/page.tsx
apps/web/src/app/organizations/page.tsx
apps/web/src/app/organizations/[organizationId]/page.tsx
apps/web/src/app/agents/page.tsx
apps/web/src/app/memory/page.tsx
apps/web/src/app/scenes/page.tsx
apps/web/src/app/scenes/dinner/page.tsx
apps/web/src/app/scenes/dinner/result/page.tsx
apps/web/src/app/preferences/private/page.tsx
apps/web/src/app/admin/page.tsx
apps/web/src/app/admin/models/page.tsx
apps/web/src/app/admin/audit/page.tsx
apps/web/tests/
development-logs/in-progress/P10-frontend-product-loop.md
docs/development/P10-COMPLETION-REPORT.md
```

如果已有同名文件，必须增量修改，不要重写整套目录。

## 7. 全局设计要求

P10 前端应该是一个产品界面，不是宣传页。

视觉和交互要求：

- 首页第一屏直接进入工作台，不做营销 hero。
- 操作型页面采用安静、紧凑、可扫描布局。
- 不使用大面积单色渐变。
- 不使用解释性大段文字描述功能。
- 卡片圆角不超过 8px，除非项目已有设计系统不同。
- 工具按钮优先使用图标加 tooltip。
- 每个页面必须有 loading、empty、error 状态。
- 移动端至少保证 375px 宽度无文字重叠。
- 桌面端至少检查 1280、1440、1920 宽度。

隐私和安全要求：

- 任何提交私有偏好的页面，隐私说明必须在输入框之前出现。
- 聚餐结果页只能展示聚合理由，不展示个人私有偏好正文。
- 管理后台只能展示审计 metadata，不展示敏感 payload。
- 错误边界不能把 API error detail 中的敏感字段原样渲染。

## 8. P10-01 统一 API Client 和类型边界

目标：前端所有页面使用一个统一 API client，自动携带 cookie 和 CSRF，统一处理 envelope。

建议步骤：

1. 阅读 `apps/web/src/lib/` 下已有 client。
2. 如果已有统一 client，只补齐缺口；如果没有，创建 `apps/web/src/lib/api/client.ts`。
3. client 必须满足：
   - GET 请求 `credentials: "include"`。
   - POST/PATCH/DELETE 请求自动读取 CSRF token 并发送。
   - 解析 P2 API Envelope。
   - 对 401、403、409、422、429、500 提供稳定错误对象。
   - 不在错误对象中保留敏感 request body。
4. 增加单元测试或组件测试：
   - `fetch` 被调用时包含 `credentials: "include"`。
   - 写请求包含 CSRF header。
   - envelope success 返回 `data`。
   - envelope error 返回 `{ code, message, requestId }`。
   - error 不包含原始私有字段。

验收：

```bash
corepack pnpm test -- --runInBand
```

如果项目 test runner 不支持 `--runInBand`，使用项目现有前端测试命令。

## 9. P10-02 App Shell、导航和路由守卫

目标：建立真实应用壳，把登录态、组织上下文、主导航、错误状态统一起来。

必须实现：

- `AppShell`：桌面左侧导航或顶部导航，移动端折叠菜单。
- `TopBar`：当前用户、当前组织、连接状态、退出入口。
- `RouteGuard`：未登录跳转 `/login`，无权限展示 forbidden 状态。
- 全局错误边界：只展示安全错误摘要和 request_id。
- 会话过期状态：401 显示“登录已过期”，不展示 token。
- 账号撤销/软删除状态：403 或业务错误显示“账号不可用”。

导航至少包含：

```text
首页 /
消息 /messages
组织 /organizations
智能体 /agents
记忆 /memory
场景 /scenes
私有偏好 /preferences/private
管理 /admin
```

管理入口必须根据角色显示。普通用户不应该看到管理入口。

测试要求：

- 未登录访问受保护页面时显示登录引导。
- 普通用户看不到管理入口。
- 管理员可看到管理入口。
- 401 不渲染 token。
- 403 不渲染后端敏感 detail。

## 10. P10-03 首页工作台

目标：首页成为实际应用入口，不做营销页。

首页必须展示：

- 当前用户和当前组织。
- 最近会话摘要。
- 待处理组织邀请。
- 当前活跃场景，至少包含聚餐场景入口。
- 智能体状态摘要。
- 隐私提醒摘要。

边界：

- 如果接口暂无数据，显示 empty state。
- 不允许硬编码“测试通过”“模型已上线”等虚假状态。
- 可以使用 mock fallback，但必须标注为本地占位，且不能影响真实 API 路径。

测试要求：

- 数据为空时页面仍可渲染。
- 最近会话 item 点击进入 `/messages`。
- 聚餐场景入口进入 `/scenes/dinner`。
- 隐私提醒不包含私有偏好正文。

## 11. P10-04 消息页产品化

目标：把 P5 会话/消息/WebSocket 能力呈现成可演示消息页面。

布局建议：

- 左栏：会话列表、搜索、未读状态、场景标签。
- 中栏：消息流、发送框、连接状态。
- 右栏：成员列表、场景卡、智能体状态。

必须实现：

- 会话列表 loading/empty/error。
- 消息发送 optimistic 状态或 pending 状态。
- WebSocket connected/reconnecting/offline 状态。
- 消息失败可重试。
- 不在浏览器存储消息正文。

测试要求：

- 输入消息后调用发送 API。
- WebSocket 断开时显示 reconnecting/offline。
- API error 时消息显示失败状态。
- `localStorage` 和 `sessionStorage` 不包含消息正文。

## 12. P10-05 组织和联系人页面整合

目标：整合 P4 组织目录能力，让用户能查看组织、成员、邀请、角色。

必须实现：

- `/organizations`：组织列表、创建/加入入口、待处理邀请。
- `/organizations/[organizationId]`：成员列表、角色、组织资料、邀请状态。
- 搜索框：按姓名、邮箱、角色过滤。
- 权限反馈：普通成员尝试管理操作时显示 forbidden。

边界：

- 不允许前端绕过后端权限。
- 不允许把未授权成员信息从隐藏字段泄露。

测试要求：

- 普通成员看不到危险管理按钮。
- 管理员可看到邀请和角色调整入口。
- 搜索不会改变原始数据。
- forbidden 状态无敏感 detail。

## 13. P10-06 智能体中心

目标：展示 P6 智能体和 P7 模型路由的安全摘要。

页面 `/agents` 必须展示：

- 智能体列表。
- 代理等级 L0/L1/L2/L3。
- 当前启用场景。
- 最近运行状态。
- 模型 provider 摘要。
- 是否需要人工确认。

禁止：

- 不展示 prompt 原文。
- 不展示私有记忆正文。
- 不展示模型 API key、endpoint 密钥、Kuboard 信息。

测试要求：

- L2/L3 智能体显示人工确认或风险提示。
- prompt 字段即使后端返回，也必须在 UI 中脱敏或忽略。
- provider secret 不出现在 DOM。

## 14. P10-07 记忆中心

目标：让用户能查看、管理、撤销自己的记忆授权。

页面 `/memory` 必须展示：

- 记忆分类。
- 来源场景。
- 敏感等级。
- 创建/更新时间。
- 授权状态。
- 删除/撤销授权入口。
- 访问记录 metadata。

边界：

- 默认不展开敏感正文。
- 如果确需显示用户自己的记忆正文，必须二次确认，并且不写入日志/URL/storage。
- 管理员页面不得复用这个正文读取组件。

测试要求：

- 默认视图不包含敏感正文。
- 撤销授权调用正确 API。
- 删除操作需要确认。
- access log 只显示 metadata。

## 15. P10-08 场景中心

目标：给所有场景统一入口，并明确区分“可用”和“概念”。

页面 `/scenes` 必须展示：

- 聚餐场景：可进入。
- 其他未来场景：概念/即将上线。
- 每个场景的隐私说明摘要。
- 每个场景需要的数据类型。

边界：

- 概念场景按钮不能进入假流程。
- 不允许写“已上线”除非后端和测试已支持。

测试要求：

- 聚餐场景按钮可用。
- 未实现场景按钮 disabled 或展示 waitlist。
- 未实现场景不会创建真实 scene instance。

## 16. P10-09 私有偏好页

目标：提供聚餐私有偏好录入/编辑入口，符合 P9 隐私约束。

页面 `/preferences/private` 必须满足：

- 隐私说明位于输入框之前。
- 明确说明可见性、用途、保留时间、删除方式。
- 输入框只用于私有偏好，不复用聊天输入框。
- 提交前可预览将提交的数据分类。
- 提交后显示成功状态，不回显完整私有正文。

禁止：

- 不允许 localStorage/sessionStorage 保存偏好正文。
- 不允许 URL query 保存偏好正文。
- 不允许 console.log 偏好正文。

测试要求：

- 提交调用 P9 私有偏好 API。
- DOM 中成功页不包含完整正文。
- storage 中不包含偏好正文。
- 隐私说明存在并位于表单前。

## 17. P10-10 聚餐结果页

目标：把 P9 候选生成、聚合理由、投票、确认做成可演示闭环。

页面 `/scenes/dinner/result` 必须展示：

- 候选列表。
- 匹配分。
- 聚合理由。
- 参与者投票状态。
- 人工确认按钮。
- 已确认结果。

隐私要求：

- 聚合理由不能包含“张三不吃辣”这类个人偏好归因。
- 只允许“多数成员偏好清淡”“预算匹配”这类聚合表达。
- 若后端返回敏感 explanation，前端必须脱敏或拒绝展示。

测试要求：

- 候选为空时显示 empty state。
- 投票按钮调用正确 API。
- 确认按钮需要权限。
- 页面不渲染个人私有偏好。

## 18. P10-11 管理后台

目标：提供比赛演示需要的最小管理视图。

页面 `/admin` 和子页面至少包含：

- 系统概览：用户数、组织数、会话数、场景数、模型请求数。
- 模型节点：provider、状态、最近错误、平均延迟。
- 审计元数据：request_id、user_id、action、resource_type、created_at。
- 安全状态：CSRF、cookie、rate limit、redaction、metrics。

禁止：

- 不提供私有偏好正文入口。
- 不提供 message body 全文检索入口。
- 不展示 token、cookie、API key。
- 不展示模型真实内网 endpoint，如果 endpoint 包含敏感地址则只展示 host hash 或 provider name。

测试要求：

- 普通用户访问 `/admin` 被拒绝。
- 管理员可访问 overview。
- 审计列表不包含 payload。
- 模型页面不包含 secret。

## 19. P10-12 敏感入口清理和前端安全扫描

目标：确认 P10 没有引入隐私泄漏入口。

实现一个前端测试或脚本，建议路径：

```text
apps/web/tests/security/sensitive-ui.test.ts
```

检查：

- `localStorage` 不出现 token、message、private preference、memory content。
- `sessionStorage` 不出现 token、message、private preference、memory content。
- DOM 不出现 `refresh_token`、`access_token`、`MODEL_GATEWAY_API_KEY`。
- URL 不出现 `token=`、`preference=`、`message=`.
- error boundary 不展示 raw response body。

如果项目测试框架不适合浏览器 storage，至少写纯函数测试和组件测试，并在完成报告中说明未覆盖的浏览器 E2E。

## 20. P10-13 状态组件全覆盖

目标：所有核心页面具备稳定状态，不因 API 异常白屏。

页面必须覆盖：

```text
/
/messages
/organizations
/organizations/[organizationId]
/agents
/memory
/scenes
/scenes/dinner
/scenes/dinner/result
/preferences/private
/admin
```

每页至少覆盖：

- loading
- empty
- error
- forbidden

消息页额外覆盖：

- offline
- reconnecting

认证相关额外覆盖：

- expired
- revoked

测试要求：

- 每个状态可渲染。
- 文案不溢出按钮/卡片。
- error state 只展示安全摘要。

## 21. P10-14 响应式和无障碍

目标：确保比赛演示和评审使用时页面稳定。

必须检查：

- 键盘可达主要按钮。
- focus 样式可见。
- 表单 input 有 label。
- icon button 有 aria-label 或 tooltip。
- 颜色对比不低于常规可读标准。
- 375px、768px、1280px、1440px、1920px 无明显重叠。

如果项目中有 Playwright，新增基础截图/可访问性 smoke 测试。没有 Playwright 时，至少使用现有测试框架验证关键组件属性，并在完成报告中列出人工检查项。

## 22. P10-15 文档、日志和完成报告

必须新增：

```text
development-logs/in-progress/P10-frontend-product-loop.md
docs/development/P10-COMPLETION-REPORT.md
```

日志必须包含：

- 基准提交。
- 开始前 git status。
- 每个子任务完成情况。
- 修改文件列表。
- 测试命令和结果。
- 未执行项和原因。
- 隐私边界声明。

完成报告必须包含：

```markdown
# P10 Completion Report

## 1. 基准信息
- 项目路径：
- 分支：
- 基准提交：
- 开始前工作树：

## 2. 完成任务
- P10-01：
- ...
- P10-15：

## 3. 修改文件列表

## 4. 页面清单

## 5. 隐私与安全检查

## 6. 验证命令结果

## 7. 未执行项

## 8. 边界声明
- 未执行 P11+
- 未提交、未推送
- 未修改 P0/P1 冻结契约语义
- 未引入真实密钥
```

同时更新：

```text
docs/development/DEVELOPMENT_PLAN.md
```

只允许把 P10 标记为完成或进行中，不允许提前标记 P11+。

## 23. 最终验证命令

P10 完成后必须运行：

```bash
cd /root/CampusAgent
git diff HEAD --check
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

如果 Docker 可用，额外运行：

```bash
docker compose config
docker compose up -d postgres redis mock-model
docker compose ps
docker compose down
```

如果 gitleaks 可用，额外运行：

```bash
gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner
```

## 24. 交付要求

交付时只输出完成报告摘要，不要提交，不要推送。报告必须明确：

- P10-01 至 P10-15 是否全部完成。
- 后端测试数量和前端测试数量。
- 是否有 Docker/gitleaks 未执行。
- 是否存在需要 Codex 修复的小问题。
- 是否改动冻结契约。
