# P13 演示 Runbook

> 面向**演示者**的 5 分钟 CampusAgent 演示指南。
>
> 本 Runbook 是 P11 演示脚本的最终版本，覆盖完整主线演示和 4 个故障备用路径。
>
> **适用阶段**：P13 Release Candidate RC1
>
> **前置条件**：P0-P12 已完成，本机已安装 Conda 环境 `CampusAgent` 和 Node.js（corepack/pnpm）。

## 1. 演示前准备

### 1.1 环境检查（2 分钟）

```bash
cd /root/CampusAgent
git status --short --branch        # 确认工作树状态
git log -1 --oneline               # 确认基准提交
```

确认：
- 工作树干净或仅有 P13 文档改动。
- 基准提交为 P12 完成提交。

### 1.2 验证后端质量（1 分钟）

```bash
# 无需 Docker，使用 SQLite in-memory
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
```

期望：全部通过，1473 个测试（含 P13 新增 41 个 release 脚本测试）。

### 1.3 验证前端质量（1 分钟）

```bash
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

期望：全部通过，115 个测试。

### 1.4 验证演示数据可复现（1 分钟）

```bash
# 进程内 smoke 测试，11 步全通过
conda run -n CampusAgent python scripts/demo/run_demo_smoke.py
```

期望输出：
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

### 1.5 Demo 账号

所有 demo 账号使用同一密码：`CampusAgentDemo2026!`

| 账号 | 邮箱 | 角色 | 用途 |
|---|---|---|---|
| Demo Admin | `demo_admin@example.com` | 系统管理员 | 管理后台、demo 重置 |
| Alice Chen | `demo_alice@example.com` | 学生 | 聚餐场景参与者 |
| Bob Lin | `demo_bob@example.com` | 学生 | 聚餐场景参与者 |
| Carol Wang | `demo_carol@example.com` | 学生 | 聚餐场景参与者 |
| Deleted User | `demo_deleted@example.com` | 学生（软删除） | 登录失败演示 |

> 注意：这是公开的 demo 密码，仅用于演示数据，不得用于生产默认配置。

### 1.6 初始化 Demo 数据

**方式 A：CLI 脚本（推荐，无需运行服务器）**

```bash
conda run -n CampusAgent python scripts/demo/reset_demo.py
conda run -n CampusAgent python scripts/demo/seed_demo.py
```

**方式 B：内部 API（需要运行中的开发服务器）**

```bash
# 启动开发服务器
conda run -n CampusAgent uvicorn src.main:app --reload --app-dir apps/api

# 用 demo_admin 登录后调用内部 API
# POST /api/v1/internal/demo/reset
# POST /api/v1/internal/demo/seed
# GET  /api/v1/internal/demo/status
```

内部 API 仅在 `APP_ENV=development` 或 `APP_ENV=test` 下注册，生产环境不挂载。

## 2. 启动路径

### 2.1 Docker 可用时

```bash
docker compose up -d postgres redis mock-model
conda run -n CampusAgent python scripts/demo/seed_demo.py
```

### 2.2 Docker 不可用时（离线/无 Docker）

无需 Docker、Postgres 或 Redis 即可完成演示验证。Demo 数据和全部测试使用 SQLite in-memory。

**后端验证（无需 Docker）：**

```bash
cd /root/CampusAgent
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
```

**一键 Smoke 验证（无需 Docker、无需运行服务器）：**

```bash
conda run -n CampusAgent python scripts/demo/run_demo_smoke.py
```

**前端验证（无需 Docker）：**

```bash
cd /root/CampusAgent
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

## 3. 五分钟主线演示

假设 demo 数据已通过 `scripts/demo/seed_demo.py` 初始化，前端开发服务器运行在 `localhost:3000`。

| 步骤 | 页面 | 耗时 | 讲解点 |
|---|---|---|---|
| 1 | 登录 | 30s | demo 账号一键切换，密码不写入浏览器存储 |
| 2 | 首页工作台 | 30s | 产品主入口聚合关键信息 |
| 3 | 组织目录 | 30s | 学校—宿舍多级组织与成员关系 |
| 4 | 消息 | 30s | 私聊/群聊、WebSocket 实时、场景卡 |
| 5 | 智能体/记忆 | 30s | 个人智能体、代理等级、场景授权 |
| 6 | 聚餐场景 | 90s | 候选餐厅、匹配分、脱敏理由、投票 |
| 7 | 私有偏好 | 30s | 隐私说明先于提交、不回显正文 |
| 8 | 管理后台 | 30s | 审计 metadata、模型节点、不窥探偏好 |
| 9 | 失败场景 | 30s | 软删除用户拒绝、错误密码统一响应 |

### 步骤 1：登录（30 秒）

- 打开 `http://localhost:3000/login`
- 在登录页底部找到「Demo 账号快速登录」面板（仅开发环境可见）
- 点击「Demo Admin」——邮箱和密码自动填入
- 点击「登录」

**价值点：** 展示 demo 账号一键切换能力，密码不写入浏览器存储。

### 步骤 2：首页工作台（30 秒）

- 登录后自动跳转首页
- 展示用户信息、组织、最近会话、活跃场景概览

**价值点：** 产品主入口聚合了所有关键信息。

### 步骤 3：组织目录（30 秒）

- 点击侧边栏「目录」
- 展示 JNU Campus Demo Lab → Demo Dorm 301 组织树
- 展示成员列表

**价值点：** 学校—宿舍多级组织结构与成员关系。

### 步骤 4：消息（30 秒）

- 点击侧边栏「消息」
- 展示会话列表和消息流
- 指出：群聊中场景卡作为结构化消息占位

**价值点：** 私聊/群聊/组织群聊统一入口，WebSocket 实时同步。

### 步骤 5：智能体/记忆（30 秒）

- 点击侧边栏「智能体」
- 展示个人智能体、代理等级（L0-L3，MVP 禁用 L4）
- 展示场景权限列表

**价值点：** 每个用户拥有隔离的个人智能体，代理等级受控。

### 步骤 6：聚餐场景（90 秒）

- 点击侧边栏「场景」
- 找到已完成的聚餐场景实例
- 展示候选餐厅列表、匹配分、聚合理由（脱敏后）
- 展示投票结果

**价值点：** 这是比赛核心场景。强调：
- 候选排名可复现（确定性聚合）
- 公共理由不暴露任何人的私有偏好
- 模型不可用时仍可运行（规则引擎备用）

### 步骤 7：私有偏好（30 秒）

- 切换登录为 Alice（退出 → 登录页选 Alice）
- 进入聚餐场景的私有偏好页
- 展示隐私说明先于提交
- 指出：提交的私有备注包含唯一标记 `DEMO_PRIVATE_PHRASE_DO_NOT_RENDER`，但该标记不会出现在结果页、管理后台或审计日志中

**价值点：** 可证明的隐私边界——私有数据只进不出的端到端保障。

### 步骤 8：管理后台（30 秒）

- 退出，登录为 Demo Admin
- 进入「管理后台」
- 展示系统概览、模型节点状态、审计元数据
- 强调：审计日志只有 metadata（actor/action/resource/request_id），不含消息正文或偏好正文

**价值点：** 管理员可观测但不可窥探。

### 步骤 9：失败场景（30 秒）

- 尝试用 Deleted Demo User 登录——被拒绝
- 尝试用错误密码登录 Alice——统一错误，不泄露账号是否存在

**价值点：** 系统对失败状态的稳定处理。

## 4. 隐私保护讲解点

在演示中重点强调以下隐私保障：

1. **私有偏好隔离**：每个参与者提交的私有偏好（含预算、菜系、禁忌、备注）只用于聚合，不回显、不存储在浏览器、不出现在结果页。

2. **管理员不可窥探**：管理员能看到审计元数据（谁在何时访问了什么），但看不到任何私有偏好正文或消息正文。

3. **确定性可审计**：候选排名由确定性算法生成，相同输入永远产生相同输出，可在审计中复现。

4. **场景清理**：场景结束后，原始私有提交、胶囊和中间评价会被清理，数据库中不留痕迹。

5. **浏览器零残留**：Token、偏好正文、消息正文不写入 localStorage/sessionStorage 或 URL。前端有存储审计工具自动检测泄漏。

6. **失败关闭**：加密服务或授权服务故障时，请求被拒绝而非降级为明文。

**文案要求**：不写"万能 AI"，不承诺真实生产能力，强调隐私、协作、校园场景。

## 5. 故障备用路径

### 场景 A：Docker 不可用

**触发条件**：比赛现场机器没有 Docker，或 Docker daemon 无法启动。

**备用路径**：

```bash
# 后端：使用 SQLite in-memory 运行全部测试
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider

# 前端：构建验证
corepack pnpm --filter @campus-agent/web build

# 演示：进程内 smoke 测试
conda run -n CampusAgent python scripts/demo/run_demo_smoke.py
```

**讲解要点**：
- 所有核心逻辑验证不需要 Docker。
- SQLite in-memory 覆盖了完整的业务流程测试。
- 生产部署使用 PostgreSQL，但演示验证不需要。

### 场景 B：模型 Mock 不可用

**触发条件**：mock-model 服务无法启动，或模型网关无响应。

**备用路径**：
- 展示 deterministic mock 结果（规则引擎生成的候选和评分）。
- 说明真实模型接入在 P7 的 provider abstraction 后面。
- 不展示真实实验室地址或密钥。

**讲解要点**：
- 聚餐场景使用确定性规则引擎，不依赖任何真实模型。
- 即使模型网关完全不可用，聚餐场景仍可完整运行。
- Mock Model Node 在管理后台可查看状态。

### 场景 C：数据库不可用

**触发条件**：PostgreSQL 无法连接，或数据库进程崩溃。

**备用路径**：
- 展示 `/health/ready` degraded（数据库标记为 unavailable，但 `/health/live` 仍 ok）。
- 展示 recovery runbook（`docs/development/P12-RECOVERY-RUNBOOK.md`）。
- 使用测试和截图证据说明功能。
- 运行恢复演练脚本：

```bash
conda run -n CampusAgent python scripts/ops/recovery_drill.py
```

**讲解要点**：
- 数据库不可用时系统优雅降级，不崩溃。
- 恢复操作手册有完整步骤。
- demo reset/seed 可在恢复后重建数据。

### 场景 D：前端无法启动

**触发条件**：Next.js 开发服务器无法启动，或端口被占用。

**备用路径**：
- 展示 `corepack pnpm --filter @campus-agent/web build` 成功记录。
- 展示 API tests 和 demo script 输出。
- 使用录屏或截图作为备用证据。
- 展示 API Docs（`http://localhost:8000/docs`）说明后端能力。

**讲解要点**：
- 前端构建成功证明代码可编译。
- API 文档展示完整的 71 个端点。
- demo smoke 测试证明业务逻辑正确。

## 6. 恢复操作

演示结束后或演示前需要恢复干净状态：

```bash
# 重置（删除所有 demo 数据，保留非 demo 数据）
conda run -n CampusAgent python scripts/demo/reset_demo.py

# 重新种子
conda run -n CampusAgent python scripts/demo/seed_demo.py
```

重置是幂等的，重复运行安全。重置只删除 `demo_` 前缀邮箱的用户和 `-demo-lab` 后缀的组织，不会影响任何真实数据。

生产环境（`APP_ENV=production`）下重置操作会被拒绝（fail-closed）。

## 7. 演示后自检

```bash
# 确认无敏感数据残留
conda run -n CampusAgent python scripts/security/check_no_secrets.py

# 确认 release candidate 检查通过
conda run -n CampusAgent python scripts/release/check_release_candidate.py
```

---

**最后更新**：2026-07-18
**关联文档**：`docs/development/P11-DEMO-SCRIPT.md`、`docs/development/P12-RECOVERY-RUNBOOK.md`、`docs/development/P13-RC-CHECKLIST.md`
