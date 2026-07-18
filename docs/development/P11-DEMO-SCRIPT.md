# P11 演示脚本

> 面向人类演示者的 5 分钟 CampusAgent 演示指南。
>
> 适用阶段：P11 演示数据、端到端演练与可复现验收。
>
> 前置条件：P0–P10 已完成，本机已安装 Conda 环境 `CampusAgent` 和 Node.js（corepack/pnpm）。

## 1. 演示准备

### 1.1 环境检查

```bash
cd /root/CampusAgent
git status --short --branch
```

确认工作树干净或仅有 P11 相关改动。

### 1.2 Demo 账号

所有 demo 账号使用同一密码：`CampusAgentDemo2026!`

| 账号 | 邮箱 | 角色 | 用途 |
|---|---|---|---|
| Demo Admin | `demo_admin@example.com` | 系统管理员 | 管理后台、demo 重置 |
| Alice Chen | `demo_alice@example.com` | 学生 | 聚餐场景参与者 |
| Bob Lin | `demo_bob@example.com` | 学生 | 聚餐场景参与者 |
| Carol Wang | `demo_carol@example.com` | 学生 | 聚餐场景参与者 |
| Deleted User | `demo_deleted@example.com` | 学生（软删除） | 登录失败演示 |

> 注意：这是公开的 demo 密码，仅用于演示数据，不得用于生产默认配置。

### 1.3 初始化 Demo 数据

有两种方式初始化 demo 数据：

**方式 A：CLI 脚本（推荐，无需运行服务器）**

```bash
# 重置 demo 数据（仅删除 demo namespace，保留其他数据）
conda run -n CampusAgent python scripts/demo/reset_demo.py

# 种子 demo 数据（幂等，可重复运行）
conda run -n CampusAgent python scripts/demo/seed_demo.py
```

**方式 B：内部 API（需要运行中的开发服务器）**

```bash
# 启动开发服务器
conda run -n CampusAgent uvicorn src.main:app --reload --app-dir apps/api

# 用 demo_admin 登录后，调用内部 API
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

该脚本在进程内用 SQLite in-memory 启动完整应用，执行 reset → seed → 登录 → 浏览 → 隐私检查 → 登出全路径，11 个步骤全部通过即返回退出码 0。

**前端验证（无需 Docker）：**

```bash
cd /root/CampusAgent
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

**运行 demo 相关测试子集：**

```bash
# 后端 demo 单元 + 集成测试
conda run -n CampusAgent python -m pytest apps/api/tests -q -k demo

# 前端 demo 测试
cd apps/web && corepack pnpm test -- --testPathPattern="tests/demo"
```

## 3. 五分钟演示路径

假设 demo 数据已通过 `scripts/demo/seed_demo.py` 初始化，前端开发服务器运行在 `localhost:3000`。

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

### 步骤 4：聚餐场景（90 秒）

- 点击侧边栏「场景」
- 找到已完成的聚餐场景实例
- 展示候选餐厅列表、匹配分、聚合理由（脱敏后）
- 展示投票结果

**价值点：** 这是比赛核心场景。强调：
- 候选排名可复现（确定性聚合）
- 公共理由不暴露任何人的私有偏好
- 模型不可用时仍可运行（规则引擎备用）

### 步骤 5：隐私保护讲解（60 秒）

- 切换登录为 Alice（退出 → 登录页选 Alice）
- 进入聚餐场景的私有偏好页
- 展示隐私说明先于提交
- 指出：提交的私有备注包含唯一标记 `DEMO_PRIVATE_PHRASE_DO_NOT_RENDER`，但该标记不会出现在结果页、管理后台或审计日志中

**价值点：** 可证明的隐私边界——私有数据只进不出的端到端保障。

### 步骤 6：管理后台（60 秒）

- 退出，登录为 Demo Admin
- 进入「管理后台」
- 展示系统概览、模型节点状态、审计元数据
- 强调：审计日志只有 metadata（actor/action/resource/request_id），不含消息正文或偏好正文

**价值点：** 管理员可观测但不可窥探。

### 步骤 7：失败场景演示（30 秒）

- 尝试用 Deleted Demo User 登录——被拒绝
- 尝试用错误密码登录 Alice——统一错误，不泄露账号是否存在

**价值点：** 系统对失败状态的稳定处理。

## 4. 备用方案

### 4.1 模型不可用

Demo 数据使用确定性规则引擎生成候选和评分，不依赖任何真实模型。即使模型网关完全不可用，聚餐场景仍可完整运行。

如需展示模型增强：demo 数据中的 Mock Model Node 提供固定响应，可在管理后台查看其状态。

### 4.2 Docker 不可用

见第 2.2 节。所有演示验证均可通过 SQLite in-memory 完成，无需 Docker、Postgres 或 Redis。

### 4.3 网络不可用

- 后端：Mock/规则 Provider 完全离线可用
- 前端：构建产物可静态部署，不依赖 CDN
- 测试：`run_demo_smoke.py` 在进程内运行，无需任何网络连接

## 5. 隐私保护讲解点

在演示中重点强调以下隐私保障：

1. **私有偏好隔离**：每个参与者提交的私有偏好（含预算、菜系、禁忌、备注）只用于聚合，不回显、不存储在浏览器、不出现在结果页。

2. **管理员不可窥探**：管理员能看到审计元数据（谁在何时访问了什么），但看不到任何私有偏好正文或消息正文。

3. **确定性可审计**：候选排名由确定性算法生成，相同输入永远产生相同输出，可在审计中复现。

4. **场景清理**：场景结束后，原始私有提交、胶囊和中间评价会被清理，数据库中不留痕迹。

5. **浏览器零残留**：Token、偏好正文、消息正文不写入 localStorage/sessionStorage 或 URL。前端有存储审计工具自动检测泄漏。

6. **失败关闭**：加密服务或授权服务故障时，请求被拒绝而非降级为明文。

## 6. 重置与恢复

演示结束后或演示前需要恢复干净状态：

```bash
# 重置（删除所有 demo 数据，保留非 demo 数据）
conda run -n CampusAgent python scripts/demo/reset_demo.py

# 重新种子
conda run -n CampusAgent python scripts/demo/seed_demo.py
```

重置是幂等的，重复运行安全。重置只删除 `demo_` 前缀邮箱的用户和 `-demo-lab` 后缀的组织，不会影响任何真实数据。

生产环境（`APP_ENV=production`）下重置操作会被拒绝（fail-closed）。
