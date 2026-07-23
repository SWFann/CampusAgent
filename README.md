# CampusAgent

> 让每个学生拥有自己的校园 Agent，让个人需求安全地进入群体协作与学校服务流程。

[![CI](https://github.com/zrliu2025-ctrl/CampusAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/zrliu2025-ctrl/CampusAgent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)

CampusAgent 是一个面向校园事务与群体协作的智能体平台。它不是把 AI 接进聊天框，而是把学生的个人 Agent 放进校园身份、组织关系、消息、任务和正式业务流程中。

每个学生都可以拥有一个由本人控制的 Agent。Agent 能整理信息、维护任务、代表用户表达已经确认的需求，并与其他 Agent 协商；但它不能替用户作出重要决定，也不能把私人对话、原始偏好或敏感记忆直接交给学校、群体或其他 Agent。

## 项目要解决什么

校园服务通常存在两类断裂：

1. **个人信息很多，但缺少持续协助。** 课程、通知、申请、报修和证明分散在不同入口，学生需要反复整理。
2. **群体决策很多，但真实需求难以安全表达。** 室友安排、共同时间、任务分工和聚餐选择都涉及个人边界，公开表达容易造成压力，只投票又无法处理硬性条件。

CampusAgent 用“个人 Agent + 组织关系 + 场景协议”连接这两类问题：

```text
个人需求
   │
   ▼
个人 Agent ── 整理信息、管理任务、解释意图、守住授权边界
   │
   ▼
校园组织 ─── 班级、学院、宿舍、课程、社团、项目组
   │
   ▼
协作场景 ─── 收集私有输入、生成候选、Agent 协商、成员确认
   │
   ▼
责任人审核 ─ 学校部门或群体负责人完成最终确认与正式执行
```

## 核心设计：Agent 代表表达，不替人决定

CampusAgent 将智能体能力划分为四个层级：

| 能力 | Agent 可以做什么 | 必须由谁确认 |
|---|---|---|
| 理解 | 整理通知、解释流程、识别用户需求 | 用户可随时修正 |
| 准备 | 生成日程、申请草稿、材料清单和候选方案 | 用户确认后才能继续 |
| 协商 | 在已授权范围内与其他 Agent 交换最小必要表达 | 新条件和最终方案必须由本人确认 |
| 执行 | 向校园服务提交已确认的数据或形成正式结果 | 高影响事项由本人和责任人共同确认 |

系统遵循以下约束：

- **每个 Agent 有明确所有者**：个人 Agent 属于学生本人，不属于学校或平台管理员。
- **先确认理解，再允许代表**：Agent 必须展示它如何理解每条需求，用户确认后才能进入协作。
- **硬性条件不可擅自让步**：例如“不接受寝室内吸烟”只用于筛选，不进入自动折中。
- **新增条件必须暂停**：其他 Agent 提出会影响用户的条件时，协商暂停，等待本人选择。
- **结果不是命令**：Agent 形成的是建议；正式住宿、申请、预约等结果仍由责任人确认。
- **退出始终可用**：用户可以退出某轮协作，不因“必办任务”而被迫接受某个方案。

## 产品结构

### 1. 个人工作台

个人工作台是学生与自己 Agent 的私有空间：

- 按线程持续对话，整理课程、通知、材料和校园事务；
- 保存加密的工作线程和消息历史；
- 从课程查询、通知摘要、请假、在读证明、场地预约、宿舍报修等模板创建任务；
- 展示任务状态、执行时间线、已使用数据和明确排除的数据；
- 支持立即执行、定时任务和周期任务的交互设计；
- 在需要提交或产生外部影响前请求用户确认。

工作台消息以密文存储。服务端解密仅发生在经过授权的当前请求中，数据库不保存明文会话内容。

### 2. 我的 Agent 与模型路由

用户可以选择：

- 使用平台提供的模型；
- 配置个人 OpenAI-compatible 模型服务；
- 保存多个模型配置并切换当前路由；
- 测试模型连通性和延迟；
- 使用 OpenAI、DeepSeek、StepFun 或自定义兼容端点。

个人 API Key 和模型路由配置加密保存，接口只返回“是否已配置”，不会回传密钥。自定义地址还会阻止私网和不安全目标，降低 SSRF 风险。

### 3. 组织与群体

组织是协作上下文，而不是普通通讯录。当前模型覆盖：

- 学校、学院、院系、班级、课程、宿舍、社团、实验室、项目组和临时群体；
- 学校身份同步、开放加入、审批加入和仅邀请加入；
- Owner、Admin、Member、Guest 等成员角色；
- 邀请、申请、审核、退出、成员管理和所有权转移；
- 将协作场景绑定到组织，并自动邀请当前有效成员。

### 4. 消息、通知与校园服务

平台把个人工作和群体关系连接到统一入口：

- 私聊、群聊、联系人和群成员管理；
- 学院、课程、班级和个人通知聚合；
- Agent 摘要、去重、截止时间识别和待办提示；
- 校园事务入口、负责部门、材料要求和办理进度；
- WebSocket 实时事件与场景通知。

### 5. 协作空间

协作空间同时承载两类任务：

- **学校发起的必办流程**：例如新生宿舍共识安排；
- **群体自主创建的协作**：例如聚餐、共同时间协调和任务分工。

通用场景生命周期为：

```text
草稿
  → 发布并邀请
  → 成员自主接受
  → 收集私有输入
  → 生成公开候选
  → 表决或协商
  → 负责人确认
  → 完成并清理临时数据
```

每个场景插件只能通过受限的服务门面访问模型、记忆、会话和审计能力，不能直接读取其他模块的数据表。

## 重点场景：新生宿舍共识安排

宿舍场景体现了 CampusAgent 当前最完整的设计思路。目标不是用算法给学生打“性格分”，也不是让学校直接读取学生隐私，而是在正式分配宿舍前形成一个所有成员都能接受、学校可以审核的住宿建议。

### 完整流程

```text
学校发布住宿任务
      │
      ▼
学生逐条表达生活需求，并标记重要程度
      │
      ▼
本人确认 Agent 对每条需求的理解
      │
      ▼
候选同学自主加入，系统等待成员准备完成
      │
      ▼
多个 Agent 在确认边界内自动协商（最多 3 次）
      │
      ├── 出现新增条件 → 暂停并请求本人决定
      ├── 有成员退出   → 保留任务并重新匹配或人工协调
      └── 无法达成共识 → 不使用多数票强制分配
      │
      ▼
所有成员分别确认建议组合
      │
      ▼
学校住宿工作组审核必要住宿条件
      │
      ▼
正式分配寝室并建立寝室协作群
```

### 这个场景的重要规则

- 原始表达仅本人可见；
- 心理健康信息、私人对话和性格评价不参与匹配；
- 硬性排除、必须满足、可协商和偏好项分别处理；
- Agent 只交换与共同生活直接相关的最小必要表达；
- 推荐理由来自已确认需求、硬性筛选和协商承诺，不是人格评分；
- 最终室友组合需要所有成员确认，不以简单多数票决定；
- 学校只能查看最终组合、必要住宿条件和审计记录；
- 必办的是完成住宿安排流程，不是强制接受某组室友。

### 当前实现说明

宿舍共识安排目前是完整的交互演示流程，覆盖需求表达、意图确认、等待、自主参加、多 Agent 协商、反提案、补充需求、重试、退出、无共识、全员确认和学校审核。页面明确标记为演示模式，部分状态使用浏览器本地状态模拟。

通用场景后端已经实现组织绑定、参与者邀请、私有提交加密、候选聚合、投票、确认、审计和清理机制。将宿舍演示完全接入真实住宿系统、候选池和学校审核系统仍属于后续集成工作。

## 其他协作场景

| 场景 | 主要输入 | 输出与确认方式 | 当前形态 |
|---|---|---|---|
| 新生宿舍共识安排 | 作息、声音、卫生、相处距离及逐条生活边界 | 全员接受的室友建议，学校审核后正式分配 | 完整交互演示 |
| 宿舍聚餐 | 时间、预算、位置、饮食限制 | 候选餐厅、公开聚合理由、投票和最终确认 | 前后端场景实现 |
| 共同时间协调 | 成员可用时间 | 选项级聚合计数，负责人确认时段 | 通用结构化场景插件 |
| 任务分工认领 | 可认领任务 | 任务负责人和汇总进度 | 通用结构化场景插件 |
| 校园事务任务 | 课程、通知、申请、证明、预约、报修所需字段 | 草稿、时间线、回执和人工确认 | 工作台交互演示与扩展位 |

## 隐私数据流

场景插件不会直接公开用户提交。通用处理流程为：

```text
原始偏好（用户私有）
      │  加密存储
      ▼
最小化偏好胶囊
      │  只包含硬性条件、软偏好、权重和允许公开的理由码
      ▼
候选私有评估
      │  单人评分和异议不公开
      ▼
聚合结果
      │  只保留候选级分数和安全的公开理由
      ▼
人工确认后的公开结果
      │
      ▼
清理原始提交和场景临时数据
```

核心安全原则包括：

- 私有输入加密存储，不在响应或日志中回显；
- 管理员不能读取个人场景提交内容；
- 工作台消息、个人模型配置和 API Key 加密保存；
- 领域事件只携带 ID、状态和计数，不携带偏好正文；
- 外部模型调用按用途和数据分类路由；
- 授权、隔离或加密失败时拒绝执行；
- 关键操作写入不含私密内容的审计日志。

详见 [隐私工程基线](docs/privacy/PRIVACY_BASELINE.md)、[权限矩阵](docs/architecture/PERMISSION_MATRIX.md) 和 [威胁模型](docs/security/THREAT_MODEL.md)。

## 技术架构

```text
┌──────────────────────────────────────────────────────────────┐
│ Next.js Web                                                  │
│ 首页 · 消息 · 个人工作台 · 组织 · 协作空间 · Agent · 知识库 │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP / WebSocket
┌───────────────────────────▼──────────────────────────────────┐
│ FastAPI 模块化单体                                           │
│ Auth │ Users │ Agents │ Organizations │ Conversations        │
│ Contacts │ Memories │ Scenes │ Audit │ Model Gateway         │
└──────────────┬───────────────────────┬───────────────────────┘
               │                       │
┌──────────────▼────────────┐  ┌───────▼──────────────────────┐
│ PostgreSQL / SQLite       │  │ Redis / Domain Events       │
│ 业务数据 · 密文 · 审计    │  │ 缓存 · 状态通知 · 实时事件  │
└───────────────────────────┘  └───────┬──────────────────────┘
                                      │
                           ┌──────────▼───────────────────────┐
                           │ OpenAI-compatible Model Gateway │
                           │ 平台模型 · 个人模型 · 校园节点   │
                           └──────────────────────────────────┘
```

| 层级 | 技术 |
|---|---|
| Web | Next.js 14、React 18、TypeScript、Zustand、Jest、Playwright |
| API | FastAPI、Pydantic、SQLAlchemy、Alembic、WebSocket |
| 数据 | PostgreSQL 15、Redis 7；测试和 fallback 支持 SQLite |
| AI | OpenAI-compatible Model Gateway、平台/个人模型路由、Mock Provider |
| 工程 | pnpm workspace、uv、Ruff、mypy、pytest、Docker Compose |
| 架构 | 模块化单体、领域事件、状态机、场景插件、受限服务门面 |

## 当前实现状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 身份、用户、联系人和组织 | 已接后端 | 具备真实 API、权限和数据库模型 |
| 消息与会话 | 已接后端 | 支持私聊、群聊、成员和实时事件 |
| 个人 Agent 对话线程 | 已接后端 | 线程与消息持久化，消息内容加密 |
| 个人模型路由 | 已接后端 | 多配置、切换、测试和密钥加密 |
| 记忆、授权与审计 | 已接后端 | 按所有者和用途控制访问 |
| 通用协作场景引擎 | 已接后端 | 状态机、组织绑定、邀请、私有提交、聚合、投票和确认 |
| 聚餐、时间协调、任务认领 | 已接场景插件 | 聚餐使用专用插件，后两者使用结构化选择插件 |
| 新生宿舍共识安排 | 交互演示 | 完整产品流程，待连接真实候选池和学校住宿系统 |
| 校园事务任务中心 | 交互演示 | 展示任务授权、时间线和回执，待连接各校务系统 |

## 仓库结构

```text
CampusAgent/
├── apps/
│   ├── web/                    # Next.js 前端与交互演示
│   │   ├── src/app/workspace/  # 个人 Agent 工作台与任务中心
│   │   ├── src/app/scenes/     # 协作空间与宿舍、聚餐场景
│   │   ├── src/app/organizations/
│   │   └── src/components/
│   └── api/                    # FastAPI 模块化单体
│       ├── src/modules/agents/
│       ├── src/modules/organizations/
│       ├── src/modules/conversations/
│       ├── src/modules/memories/
│       ├── src/modules/scenes/
│       ├── src/modules/model_gateway/
│       ├── alembic/            # 数据库迁移
│       └── tests/
├── packages/                   # 共享类型、UI、配置与 API 客户端
├── infra/                      # Docker、Mock 模型、监控与部署资产
├── scripts/                    # 启动、Demo、安全、发布与运维脚本
├── docs/                       # 产品、架构、API、隐私和开发文档
├── compose.yaml
├── Makefile
└── .env.example
```

## 快速开始

### 环境要求

| 工具 | 要求 |
|---|---|
| Git | 2.30+ |
| Node.js | 18.18+ |
| pnpm | 8.15，建议通过 Corepack 使用 |
| Python | 3.11 |
| uv | 0.5+ |
| Docker | 可选，用于 PostgreSQL、Redis 和 Mock Model |

### 一键启动

macOS、Linux 或 WSL：

```bash
git clone https://github.com/zrliu2025-ctrl/CampusAgent.git
cd CampusAgent
./scripts/start.sh
```

Windows PowerShell：

```powershell
git clone https://github.com/zrliu2025-ctrl/CampusAgent.git
cd CampusAgent
.\scripts\start.ps1
```

启动脚本会检测 Docker。Docker 可用时使用 PostgreSQL、Redis 和 Mock Model；不可用时使用 SQLite fallback。

| 服务 | 默认地址 |
|---|---|
| Web | <http://localhost:3000> |
| API | <http://localhost:8000> |
| Swagger API 文档 | <http://localhost:8000/docs> |
| Mock Model | <http://localhost:8001> |

详细说明见 [一键启动说明](docs/development/ONE_CLICK_START.md)。

### 手动启动

```bash
cp .env.example .env

corepack enable
corepack prepare pnpm@8.15.0 --activate
pnpm install --frozen-lockfile

uv sync --project apps/api --extra dev --frozen

make docker-up
make db-migrate
make demo-seed
make dev
```

后端依赖统一由 `uv` 管理，项目虚拟环境位于 `apps/api/.venv`。

## Demo 账号

所有 Demo 账号使用公开演示密码：`CampusAgentDemo2026!`

| 账号 | 邮箱 | 角色 |
|---|---|---|
| Demo Admin | `demo_admin@example.com` | 系统管理员 |
| Alice Chen | `demo_alice@example.com` | 学生、场景参与者 |
| Bob Lin | `demo_bob@example.com` | 学生、场景参与者 |
| Carol Wang | `demo_carol@example.com` | 学生、场景参与者 |
| Deleted User | `demo_deleted@example.com` | 软删除账号，用于失败演示 |

这些账号仅用于虚构 Demo 数据，不得作为生产默认配置。

## 常用命令

```bash
make help              # 查看全部命令
make dev               # 启动 Web 和 API
make test              # 运行全部测试
make lint              # 代码检查
make typecheck         # 类型检查
make build             # 构建项目
make validate          # API + Web 完整验证
make demo-smoke        # 无服务器 Demo smoke 测试
make demo-reset        # 清理 Demo namespace
make demo-seed         # 幂等生成 Demo 数据
make release-check     # 发布候选检查
```

## 模型配置

默认配置不会向外部模型发送数据。需要使用 OpenAI-compatible 服务时，在本地 `.env` 中设置：

```dotenv
MODEL_GATEWAY_BASE_URL=https://your-model-gateway.example.com/v1
MODEL_GATEWAY_MODEL=your-model-name
MODEL_GATEWAY_API_KEY=your-api-key
MODEL_GATEWAY_IS_EXTERNAL=true
ENABLE_EXTERNAL_MODEL=true
```

也可以登录后在个人工作台配置个人模型路由。`.env` 已被 Git 忽略，请勿提交真实 API Key、数据库密码或加密密钥。

## 文档导航

| 主题 | 文档 |
|---|---|
| 产品范围 | [项目概览](docs/product/PROJECT_OVERVIEW.md) · [MVP 范围](docs/product/MVP_SCOPE.md) |
| 系统架构 | [模块边界](docs/architecture/MODULE_BOUNDARIES.md) · [数据流](docs/architecture/DATA_FLOW.md) |
| 场景机制 | [场景状态机](docs/architecture/SCENE_STATE_MACHINE.md) · [Demo 规范](docs/demo/DEMO_SPEC.md) |
| API 与实时通信 | [API 文档](docs/api/README.md) · [WebSocket 契约](docs/api/WEBSOCKET_CONTRACT.md) |
| 隐私与安全 | [隐私基线](docs/privacy/PRIVACY_BASELINE.md) · [权限矩阵](docs/architecture/PERMISSION_MATRIX.md) · [威胁模型](docs/security/THREAT_MODEL.md) |
| 本地开发 | [快速开始](docs/development/QUICK_START.md) · [工具链](docs/development/TOOLING.md) · [uv 环境](docs/development/UV_ENV.md) |
| 部署与运维 | [公网演示部署](docs/development/DEPLOYMENT_PUBLIC_DEMO_PLAN.md) · [恢复手册](docs/development/P12-RECOVERY-RUNBOOK.md) |

## 项目边界

CampusAgent 当前是可运行的校园智能体平台原型。项目明确不提供：

- 自动心理诊断、人格评分或全量聊天情绪监控；
- 未经同意的学生画像、风险标记或数据上报；
- 将智能体思维链公开给用户、管理员或其他成员；
- 用多数票或模型评分强制决定室友等高影响关系；
- 绕过本人确认自动完成正式申请、支付或不可逆操作；
- 允许学校、管理员、场景插件或模型服务绕过授权读取私有数据。

## 贡献与许可

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [安全策略](SECURITY.md)。

本项目尚未加入开源许可证。在许可证文件加入仓库前，默认保留全部权利。
