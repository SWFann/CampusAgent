# P11 Completion Report

## 1. 基准信息

- **项目路径**：`/root/CampusAgent`
- **分支**：`main`
- **基准提交**：`2579eb6 feat(web): complete P10 frontend product loop and admin dashboard`
- **开始前工作树**：P11 部分文件已存在（demo 后端模块、单元测试、CLI 脚本），集成测试有 1 个失败。

## 2. 完成任务

- **P11-01**：Demo 数据 Schema 和常量。5 个 demo 用户、2 个组织、聚餐场景完整生命周期、私有偏好（含 `DEMO_PRIVATE_PHRASE` 标记）、投票数据。环境守卫 `assert_demo_env` 实现 production fail-closed。
- **P11-02**：Seed 服务。幂等 seed（用户/组织/成员/会话/场景全生命周期），密码 bcrypt 哈希不存明文，`idempotency_key` 传递给 `create_scene_instance`，候选查询同时查 ACTIVE+SELECTED。
- **P11-03**：Reset 服务。只删除 demo namespace 数据（`demo_` 前缀邮箱 + `-demo-lab` 后缀 slug），保留非 demo 行。`get_demo_status` 返回非敏感计数。
- **P11-04**：Demo API/CLI 入口。内部路由 `/api/v1/internal/demo/{seed,reset,status}`（admin + CSRF + demo env）+ CLI 脚本 `scripts/demo/seed_demo.py`、`scripts/demo/reset_demo.py`。路由前缀 `/api/v1/internal/demo` 确保 access_token cookie 可用。
- **P11-05**：前端 Demo 账号登录切换。登录页 `DemoAccountPicker` 组件，5 个 demo 账号一键填充邮箱和密码（密码仅存于 React state，不写入 storage），登录走真实 `/api/v1/auth/login`。`NODE_ENV` 网关确保生产环境不显示。
- **P11-06**：主路径 E2E smoke。`scripts/demo/run_demo_smoke.py` 在进程内运行 11 步主路径（reset→seed→登录→目录→会话→场景→状态→隐私→失败→登出），全部通过。
- **P11-07**：隐私 E2E。`DEMO_PRIVATE_PHRASE` 不出现在场景结果、目录、demo status、auth/me 响应中。
- **P11-08**：清理证明 E2E。reset 保留非 demo 用户（通过 register 创建），reset+reseed（服务层）恢复完整 demo 数据。
- **P11-09**：失败场景 E2E。错误密码登录、软删除用户登录、非管理员访问 demo 路由、CSRF 缺失写请求，均有明确错误码且不泄露敏感 detail。
- **P11-10**：离线/无 Docker 启动路径。Docker 可用（compose + seed）和不可用（SQLite in-memory + smoke 脚本）两套说明，文档见 `P11-DEMO-SCRIPT.md` 第 2 节。
- **P11-11**：演示脚本 `docs/development/P11-DEMO-SCRIPT.md`。面向人类演示者的 5 分钟演示路径，含 demo 账号、reset/seed 命令、7 步演示、备用方案、隐私讲解点。
- **P11-12**：测试夹具稳定化。独立 db session fixture、场景插件注册（`reset_scene_registry` + `DormDinnerPlugin`）、不依赖测试顺序、不依赖真实模型。
- **P11-13**：`docs/development/DEVELOPMENT_PLAN.md` 更新。P11 全部 14 个任务标记完成，进度记录表更新，未提前勾选 P12/P13。
- **P11-14**：完成报告（本文件）+ dev log（`development-logs/in-progress/P11-demo-e2e.md`）。

## 3. Demo 数据清单

- **组织**：JNU Campus Demo Lab（school）、Demo Dorm 301（dorm）
- **用户**：demo_admin（SYSTEM_ADMIN）、demo_alice、demo_bob、demo_carol（STUDENT）、demo_deleted（软删除）
- **场景**：1 个聚餐场景实例（dorm_dinner），状态 COMPLETED，3 个参与者
- **候选**：3 个候选餐厅（确定性聚合生成）
- **投票**：2 条 APPROVE 投票
- **私有偏好**：3 份（Alice/Bob/Carol），每份 notes 含 `DEMO_PRIVATE_PHRASE_DO_NOT_RENDER` 标记
- **会话**：1 个群聊（Demo Dorm 301 Group Chat），3 条消息
- **密码**：统一 `CampusAgentDemo2026!`（公开 demo 常量，bcrypt 哈希存储）

## 4. Seed/Reset 说明

### Seed（幂等）
- 通过邮箱查找用户：不存在则创建，存在则更新字段和密码哈希。
- 通过 slug 查找组织：不存在则创建，存在则更新。
- 通过 `DEMO_SCENE_IDEMPOTENCY_KEY` 查找场景：存在则跳过完整生命周期，不存在则运行到 COMPLETED。
- 多次运行结果一致，不产生重复行。

### Reset（fail-closed）
- `APP_ENV=production` 下 `assert_demo_env` 抛出 `DemoResetForbiddenError`（403）。
- 只删除 `demo_` 前缀邮箱的用户和 `-demo-lab` 后缀的组织，不影响非 demo 数据。
- 删除顺序：场景数据 → 会话数据 → 成员关系 → 组织 → Agent/Audit → AuthSession/RefreshToken → 用户。
- reset 后可立即重新 seed。

### CLI 入口
- `scripts/demo/seed_demo.py`：reset + seed 一起做（服务层），输出 JSON 摘要。
- `scripts/demo/reset_demo.py`：仅 reset，输出 JSON 摘要。
- `scripts/demo/run_demo_smoke.py`：进程内 smoke 测试，11 步全路径。

### 内部 API（仅 development/test 注册）
- `POST /api/v1/internal/demo/seed` — SYSTEM_ADMIN + CSRF
- `POST /api/v1/internal/demo/reset` — SYSTEM_ADMIN + CSRF
- `GET /api/v1/internal/demo/status` — SYSTEM_ADMIN（返回计数，无敏感数据）

## 5. E2E/Smoke 结果

### 后端集成测试（`test_demo_flow.py`）
```
16 passed, 1 warning in 9.74s
```
覆盖：主路径 smoke（5）、隐私 E2E（4）、清理证明 E2E（2）、失败场景 E2E（5）。

### 后端单元测试
```
test_demo_data.py:  29 passed
test_demo_seed.py:  14 passed
test_demo_reset.py: 15 passed
```

### Smoke 脚本（`run_demo_smoke.py`）
```
[PASS] build_app
[PASS] seed_demo
[PASS] admin_login
[PASS] directory_tree
[PASS] list_conversations
[PASS] list_scenes
[PASS] demo_status
[PASS] privacy_no_leak
[PASS] deleted_user_blocked
[PASS] non_admin_blocked
[PASS] logout
Result: 11 passed, 0 failed -> ALL PASSED
```

## 6. 隐私验证结果

- `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/scenes` 响应中。
- `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/directory/tree` 响应中。
- `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/internal/demo/status` 响应中。
- `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/auth/me` 响应中。
- Smoke 脚本的 `privacy_no_leak` 步骤扫描 4 个端点响应，均未发现泄漏。
- 前端测试验证 demo 密码不写入 `localStorage` 和 `sessionStorage`。

## 7. 修改文件列表

### 新增
| 文件 | 说明 |
|---|---|
| `apps/web/src/lib/demo/accounts.ts` | 前端 demo 账号常量和工具 |
| `apps/web/src/lib/demo/index.ts` | demo 模块导出 |
| `apps/web/tests/demo/accounts.test.ts` | 前端 demo 账号单元测试（17 个） |
| `apps/web/tests/demo/login-demo.test.tsx` | 登录页 demo 选择器测试（9 个） |
| `scripts/demo/run_demo_smoke.py` | 进程内 smoke 测试脚本 |
| `docs/development/P11-DEMO-SCRIPT.md` | 演示脚本文档 |
| `docs/development/P11-COMPLETION-REPORT.md` | 本完成报告 |
| `development-logs/in-progress/P11-demo-e2e.md` | 开发日志 |

### 修改
| 文件 | 说明 |
|---|---|
| `apps/api/tests/integration/test_demo_flow.py` | 修复 reset+reseed 测试（改用服务层） |
| `apps/web/src/app/login/page.tsx` | 添加 demo 账号选择器 |
| `docs/development/DEVELOPMENT_PLAN.md` | P11 状态更新 |

### 已存在（前序 P11 会话创建，本次验证通过）
| 文件 | 说明 |
|---|---|
| `apps/api/src/demo/__init__.py` | demo 包初始化 |
| `apps/api/src/demo/data.py` | demo 数据 Schema 和常量 |
| `apps/api/src/demo/seed.py` | 幂等 seed 服务 |
| `apps/api/src/demo/reset.py` | reset 服务 |
| `apps/api/src/demo/security.py` | 环境守卫 |
| `apps/api/src/demo/routes.py` | 内部 demo API 路由 |
| `apps/api/tests/unit/test_demo_data.py` | 数据 Schema 单元测试（29 个） |
| `apps/api/tests/unit/test_demo_seed.py` | seed 单元测试（14 个） |
| `apps/api/tests/unit/test_demo_reset.py` | reset 单元测试（15 个） |
| `scripts/demo/seed_demo.py` | seed CLI |
| `scripts/demo/reset_demo.py` | reset CLI |
| `apps/api/src/main.py` | demo router 条件注册 |
| `apps/api/src/modules/scenes/plugins/dorm_dinner/algorithm.py` | Carol dietary 修复 |

## 8. 验证命令结果

| 命令 | 结果 |
|---|---|
| `pytest apps/api/tests -q -k demo` | 77 passed |
| `pytest apps/api/tests/integration/test_demo_flow.py` | 16 passed |
| `python scripts/demo/run_demo_smoke.py` | 11 passed, exit 0 |
| `pnpm test -- --testPathPattern="tests/demo"`（apps/web） | 26 passed |
| `ruff check apps/api` | 通过 |
| `mypy apps/api/src apps/api/tests` | 通过 |
| `pnpm lint`（apps/web） | 通过 |
| `pnpm typecheck`（apps/web） | 通过 |
| `pnpm --filter @campus-agent/web build` | 通过 |

> 完整最终验证结果见第 10 节边界声明。Docker 在本环境不可用（`docker command not found`）。

## 9. 未执行项与原因

| 项目 | 原因 |
|---|---|
| Docker compose 验证 | 本环境 `docker command not found`，所有验证通过 SQLite in-memory 完成 |
| Playwright E2E | 项目 Playwright 为 stub（`e2e/example.spec.ts`），按指南允许使用 API integration smoke + 前端 component smoke 替代 |
| gitleaks | 本轮未执行，留待 Codex 审计 |

## 10. 边界声明

- 未执行 P12+。
- 未提交、未推送。
- 未修改冻结契约语义（P0/P1）。
- 未引入真实密钥（`DEMO_PASSWORD` 是公开 demo 常量，`FIELD_ENCRYPTION_KEY` 在测试中使用测试值）。
- 未调用真实模型（demo 使用确定性规则引擎和 Mock Model Node）。
- 未在生产环境启用 demo reset（`assert_demo_env` fail-closed，路由仅在 development/test 注册）。
- demo 私有偏好完全是虚构数据，不涉及任何真实个人信息。
