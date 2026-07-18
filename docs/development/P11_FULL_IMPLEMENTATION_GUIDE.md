# P11 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P11「演示数据、端到端演练与可复现验收」完整执行指令。执行方必须在 `/root/CampusAgent` 中按顺序完成 P11-01 至 P11-14。不得跳任务，不得执行 P12+，不得提交，不得推送。完成后写入 `docs/development/P11-COMPLETION-REPORT.md`，等待 Codex 审计。

## 0. 一句话目标

P11 的目标是建立一套可重复初始化、可一键重置、可演示完整产品路径的 demo 数据和自动化验收脚本，让评审或后续 Claude 在干净环境中能稳定复现 CampusAgent 的核心价值闭环。

## 1. 当前项目背景

项目路径固定为：

```bash
cd /root/CampusAgent
```

P11 默认 P10 已完成：

- 前端 App Shell、首页、消息页、组织页、智能体页、记忆页、场景页、聚餐结果页、管理后台已具备基本 UI。
- 后端已有 P3-P9 的核心能力。
- P10 已补齐前端安全边界：不把 token、私有偏好、消息正文写入浏览器 storage 或 URL。

P11 不新增产品大功能。P11 的重点是“可复现”和“可信演示”：

- 固定 demo 账号。
- 固定组织结构。
- 固定会话和场景。
- 固定聚餐输入。
- 固定模型 mock 响应。
- 固定验收脚本。
- 固定清理证明。

## 2. 开始前检查

先执行：

```bash
cd /root/CampusAgent
git status --short --branch
git log -1 --oneline
```

要求：

- 记录基准提交。
- 如果 P10 修改尚未提交，必须保留，不得回滚。
- 不得执行 `git reset --hard`。
- 不得提交或推送。

## 3. 必读文件

执行前阅读：

```text
docs/project/README.md
docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
docs/development/DEVELOPMENT_PLAN.md
docs/development/P10-COMPLETION-REPORT.md
docs/api/API_CONTRACT.md
docs/api/WEBSOCKET_CONTRACT.md
docs/privacy/THREAT_MODEL.md
docs/privacy/PRIVACY_TEST_MATRIX.md
apps/api/src/
apps/api/tests/
apps/web/src/
```

如果 `P10-COMPLETION-REPORT.md` 不存在，改读 `development-logs/in-progress/P10-frontend-product-loop.md`。

## 4. 冻结边界

P11 允许新增 demo seed、reset、E2E、文档和必要的 test-only API。P11 不允许：

- 修改 P0/P1 冻结契约语义。
- 新增真实密钥。
- 连接真实模型服务。
- 连接 Kuboard 或实验室 K8s。
- 把 demo 私有偏好当作真实用户数据。
- 在生产环境启用 demo reset。
- 把 reset 接口暴露给非 test/demo 环境。

## 5. 建议文件规划

执行方必须先查看现有目录，再按项目风格落地。建议新增或修改：

```text
apps/api/src/demo/__init__.py
apps/api/src/demo/data.py
apps/api/src/demo/seed.py
apps/api/src/demo/reset.py
apps/api/src/demo/routes.py
apps/api/src/demo/security.py
apps/api/tests/unit/test_demo_data.py
apps/api/tests/unit/test_demo_seed.py
apps/api/tests/unit/test_demo_reset.py
apps/api/tests/integration/test_demo_flow.py
apps/web/src/lib/demo/
apps/web/tests/demo/
scripts/demo/seed_demo.py
scripts/demo/reset_demo.py
scripts/demo/run_demo_smoke.py
docs/development/P11-DEMO-SCRIPT.md
docs/development/P11-COMPLETION-REPORT.md
development-logs/in-progress/P11-demo-e2e.md
```

如果项目已经有 `scripts/` 或 demo 目录，复用现有结构。

## 6. Demo 数据设计

必须包含最少但完整的数据集：

组织：

```text
JNU Campus Demo Lab
```

用户：

```text
demo_admin@example.com        管理员
demo_alice@example.com        学生用户
demo_bob@example.com          学生用户
demo_carol@example.com        学生用户
demo_deleted@example.com      软删除用户
```

密码：

```text
CampusAgentDemo2026!
```

注意：这是 demo 密码，只能写在 demo seed 和文档中，不得用于生产默认配置。

组织成员：

- demo_admin：organization owner/admin。
- demo_alice、demo_bob、demo_carol：member。
- demo_deleted：曾经存在，软删除后不可登录。

场景：

- 一个聚餐场景实例。
- 至少 3 个参与者。
- 每个参与者有公开约束和私有偏好。
- 至少 3 个候选餐厅。
- 至少 2 条投票。
- 1 个确认结果。

模型：

- 使用 P2 mock-model 或本地 deterministic mock。
- 不调用真实模型。

## 7. P11-01 Demo 数据 Schema 和常量

目标：建立统一 demo 数据定义，避免测试、脚本、文档各写一套。

实现要求：

- 创建 `apps/api/src/demo/data.py`。
- 使用 dataclass 或 Pydantic model 描述 demo 用户、组织、场景、偏好、候选。
- 所有 demo email、display name、scenario id seed key 集中定义。
- 密码常量命名为 `DEMO_PASSWORD`。
- 不要把 demo 密码混入 `Settings` 默认值。

测试要求：

- demo email 唯一。
- demo 用户至少 5 个。
- 至少 1 个 admin。
- 聚餐参与者至少 3 个。
- 私有偏好样例不为空。

## 8. P11-02 Seed 服务

目标：实现幂等 demo seed。

实现要求：

- 创建 `apps/api/src/demo/seed.py`。
- seed 函数接收 `Session` 或 `UnitOfWork`。
- 多次运行不会重复创建用户、组织、场景、候选。
- 已存在数据时更新 demo 数据到期望状态。
- 密码使用 P3 密码哈希逻辑，不存明文。
- seed 完成后返回摘要：
  - users_created
  - users_updated
  - organizations_created
  - scenes_created
  - messages_created
  - preferences_created

测试要求：

- 第一次 seed 创建数据。
- 第二次 seed 不重复。
- 用户密码哈希不等于明文。
- demo_deleted 被标记为不可登录。
- seed 摘要字段稳定。

## 9. P11-03 Reset 服务

目标：实现 demo 数据可清理和可恢复。

实现要求：

- 创建 `apps/api/src/demo/reset.py`。
- reset 只删除 demo namespace 内数据。
- reset 不删除非 demo 用户和非 demo 组织。
- reset 后可立即重新 seed。
- reset 返回摘要：
  - deleted_users
  - deleted_organizations
  - deleted_sessions
  - deleted_messages
  - deleted_scenes
  - deleted_preferences

安全要求：

- reset 只能在 `APP_ENV=development` 或 `APP_ENV=test` 下执行。
- `APP_ENV=production` 必须失败关闭。
- reset API 必须要求 admin 或本地 CLI，不允许匿名公网调用。

测试要求：

- production 下 reset 抛出明确异常。
- reset 不影响非 demo 数据。
- reset 后 seed 能恢复完整数据。

## 10. P11-04 Demo API 或 CLI 入口

目标：提供可执行入口，方便演示前初始化。

允许两种方案：

方案 A：CLI 脚本。

```text
scripts/demo/seed_demo.py
scripts/demo/reset_demo.py
```

方案 B：只在 development/test 启用的 API。

```text
POST /internal/demo/seed
POST /internal/demo/reset
GET /internal/demo/status
```

推荐同时提供 CLI 和受限 API，但最少必须有 CLI。

要求：

- CLI 使用项目 Settings 读取 DATABASE_URL。
- CLI 输出 JSON 摘要。
- API 必须挂 internal tag。
- API 在 production 下返回 403 或启动时不注册。

测试要求：

- CLI main 可被测试调用。
- internal route 在 test 环境可用。
- production 环境 route 不可用或拒绝。

## 11. P11-05 Demo 账号登录切换

目标：前端支持快速进入 demo，但不能破坏真实登录逻辑。

实现要求：

- 在登录页或 demo 页面提供 demo 账号选择。
- 点击 demo 账号会填入 email，不自动展示密码明文，或只在开发环境展示“使用 demo 密码”说明。
- 不保存 demo 密码到 storage。
- 登录仍走真实 P3 login API。

测试要求：

- 选择 demo_admin 后 email 输入框填充。
- 密码不会写入 localStorage/sessionStorage。
- 登录请求仍走 `/auth/login` 或项目既有 login endpoint。

## 12. P11-06 主路径 E2E Smoke

目标：一条脚本验证产品主路径。

如果项目已有 Playwright，写 Playwright E2E。没有 Playwright 时，写 API integration smoke 加前端 component smoke。

主路径：

1. reset demo。
2. seed demo。
3. demo_admin 登录。
4. 进入首页。
5. 查看组织。
6. 进入消息页。
7. 进入聚餐场景。
8. 提交或查看私有偏好。
9. 生成/查看候选。
10. 投票。
11. 确认结果。
12. 打开管理后台查看 metadata。
13. 退出登录。

验收：

- 脚本返回 0。
- 每一步有明确断言。
- 失败时输出 request_id 或页面状态。

## 13. P11-07 隐私 E2E

目标：用自动化证明 P9/P10 隐私边界没有被 demo 破坏。

必须验证：

- 私有偏好提交后，结果页不展示个人私有正文。
- 管理后台不展示私有偏好正文。
- audit 页面不展示 message body 或 preference body。
- storage 不包含 token、偏好正文、消息正文。
- URL 不包含 token、偏好正文、消息正文。

测试数据中应包含一条独特私有短语，例如：

```text
DEMO_PRIVATE_PHRASE_DO_NOT_RENDER
```

测试必须搜索 DOM、storage、URL，确认该短语只出现在允许的输入页或用户本人编辑页，不出现在结果页/管理页。

## 14. P11-08 清理证明 E2E

目标：证明 reset 真的清掉 demo 数据且不伤害非 demo 数据。

步骤：

1. 创建一个非 demo 用户或记录。
2. seed demo。
3. reset demo。
4. 查询 demo 用户不存在或标记清理。
5. 查询非 demo 用户仍存在。
6. 再次 seed demo。
7. 主路径仍可运行。

测试要求：

- reset 摘要数值合理。
- 非 demo 数据保留。
- 二次 seed 幂等。

## 15. P11-09 失败场景 E2E

目标：演示系统对常见失败状态的稳定处理。

至少覆盖：

- 错误密码登录失败，不区分用户不存在/密码错误。
- 软删除用户登录失败。
- 普通用户访问管理后台失败。
- CSRF 缺失写请求失败。
- WebSocket 或模型 mock 不可用时页面 degraded，不白屏。
- 聚餐候选为空时结果页 empty state。

测试要求：

- 每个失败场景有明确错误码或 UI 状态。
- 不泄露敏感 detail。

## 16. P11-10 离线和无 Docker 启动路径

目标：适配当前环境可能无 Docker 的事实。

必须提供两套说明：

1. Docker 可用：

```bash
docker compose up -d postgres redis mock-model
```

2. Docker 不可用：

```bash
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

如果 demo 脚本需要数据库，必须说明如何使用 SQLite test database 或 Postgres。不能假设 Docker 一定存在。

## 17. P11-11 演示脚本文件

新增：

```text
docs/development/P11-DEMO-SCRIPT.md
```

内容必须包含：

- 演示准备。
- reset/seed 命令。
- demo 账号。
- 5 分钟演示路径。
- 每一步要展示的价值点。
- 如果模型不可用的备用说法。
- 如果 Docker 不可用的备用验证方式。
- 隐私保护讲解点。

脚本要求写给人类演示者，不是测试报告。

## 18. P11-12 测试夹具稳定化

目标：让 demo 测试和现有单元测试互不污染。

要求：

- demo test 使用独立 db session fixture。
- 每个测试结束清理数据。
- 不依赖测试顺序。
- 不依赖真实时间，必要时复用 P9/P2 clock 工具。
- 不依赖真实模型，必须 mock。

测试要求：

- 单独运行 demo 测试通过。
- 全量 `pytest apps/api/tests` 通过。

## 19. P11-13 DEVELOPMENT_PLAN 更新

修改：

```text
docs/development/DEVELOPMENT_PLAN.md
```

要求：

- 将 P11 标记为完成或进行中。
- 更新 P11 任务摘要。
- 不提前勾选 P12/P13。
- 不改变 P0/P1/P2/P3/P4/P5/P6/P7/P8/P9 已完成事实。

## 20. P11-14 完成报告

新增：

```text
development-logs/in-progress/P11-demo-e2e.md
docs/development/P11-COMPLETION-REPORT.md
```

完成报告模板：

```markdown
# P11 Completion Report

## 1. 基准信息
- 项目路径：
- 分支：
- 基准提交：
- 开始前工作树：

## 2. 完成任务
- P11-01：
- ...
- P11-14：

## 3. Demo 数据清单
- 组织：
- 用户：
- 场景：
- 候选：

## 4. Seed/Reset 说明

## 5. E2E/Smoke 结果

## 6. 隐私验证结果

## 7. 修改文件列表

## 8. 验证命令结果

## 9. 未执行项与原因

## 10. 边界声明
- 未执行 P12+
- 未提交、未推送
- 未修改冻结契约语义
- 未引入真实密钥
- 未调用真实模型
```

## 21. 最终验证命令

必须运行：

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

如果新增了 Playwright 或 E2E 命令，必须运行对应命令并写入报告，例如：

```bash
corepack pnpm --filter @campus-agent/web test:e2e
```

如果 Docker 可用，额外运行：

```bash
docker compose config
docker compose up -d postgres redis mock-model
conda run -n CampusAgent python scripts/demo/reset_demo.py
conda run -n CampusAgent python scripts/demo/seed_demo.py
docker compose down
```

如果 Docker 不可用，报告中写明 `docker command not found` 或实际原因。

## 22. 交付要求

交付时不要提交，不要推送。输出摘要必须包含：

- P11-01 至 P11-14 是否全部完成。
- Demo seed/reset 是否幂等。
- 主路径 smoke 是否通过。
- 隐私短语是否未泄露。
- Docker/E2E 是否有未执行项。
- 是否需要 Codex 修小问题。
