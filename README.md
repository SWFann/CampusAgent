# CampusAgent

> 隐私优先、智能体原生的校园通信与协作平台

[![CI](https://github.com/zrliu2025-ctrl/CampusAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/zrliu2025-ctrl/CampusAgent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)

CampusAgent 为每名学生提供一个由本人控制的个人智能体。智能体可以在校园组织、会话和场景任务中协助用户整理信息、表达偏好与参与协商，同时遵守按场景授权、最小披露、人工确认和到期清理原则。

平台不会默认公开用户的原始偏好、敏感记忆或智能体内部推理过程。管理员、场景插件和模型服务只能访问完成当前任务所必需的数据。

## 项目亮点

- **个人智能体工作台**：与个人智能体对话，管理工作线程和任务上下文。
- **可配置模型路由**：支持 OpenAI-compatible 模型网关、连接测试、模型配置与 Mock 降级。
- **校园组织协作**：覆盖组织创建、邀请、申请加入、成员管理、角色权限和所有权转移。
- **会话与联系人**：提供私聊、群聊、联系人申请、成员管理和实时事件能力。
- **隐私记忆系统**：记忆按用途授权，可查看、修改、撤销同意和删除。
- **插件化校园场景**：场景通过公开服务接口运行，不直接绕过模块边界访问私有数据。
- **宿舍聚餐协商**：基于最小化偏好胶囊完成候选生成、投票、结果确认和临时数据清理。
- **宿舍匹配与结构化选择**：支持可扩展的结构化偏好收集和校园场景匹配。
- **审计与管理能力**：提供个人审计记录、系统管理、节点与模型部署管理入口。
- **完整演示与运维工具**：包含虚构 Demo 数据、一键启动、数据重置、恢复演练和发布检查。

## 核心场景：宿舍聚餐去哪

CampusAgent 用一个常见的校园集体决策展示“隐私与协作可以同时成立”：

1. 宿舍成员在组织会话中发起聚餐场景；
2. 每个人在私有页面提交预算、口味、禁忌、距离和时间偏好；
3. 个人智能体将原始输入转换成最小化的结构化偏好胶囊；
4. 协调层仅使用偏好胶囊评价候选方案；
5. 群聊展示提交进度、聚合理由、候选项和投票结果；
6. 用户确认最终结果后，系统清理临时偏好与私有评价。

核心命题是：**不暴露个人真实偏好，也能提高校园集体决策效率。**

## 隐私与安全原则

| 原则 | 项目中的体现 |
|---|---|
| 用户拥有智能体 | 智能体从属用户，而非学校、组织或平台管理员 |
| 默认私有 | 原始偏好和敏感记忆保留在用户私有域 |
| 最小披露 | 跨模块只传递完成任务所需的结构化信息 |
| 明确授权 | 授权按场景、用途和有效期管理，可随时撤销 |
| 人工确认 | 最终选择、外部分享等关键操作需要用户确认 |
| 隐私故障关闭 | 授权、加密或隔离异常时拒绝执行，不降级为公开处理 |
| 不暴露思维链 | 系统仅展示可审计的结构化理由和结果 |
| 生命周期管理 | 临时场景数据到期或完成后清理，长期记忆需单独同意 |

更完整的设计见 [隐私工程基线](docs/privacy/PRIVACY_BASELINE.md) 和 [威胁模型](docs/security/THREAT_MODEL.md)。

## 技术架构

```text
┌──────────────────────────────────────────────────────────┐
│ Next.js Web                                              │
│ 工作台 · 会话 · 组织 · 智能体 · 记忆 · 场景 · 管理后台   │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼───────────────────────────────┐
│ FastAPI 模块化单体                                       │
│ Auth · Users · Agents · Organizations · Conversations    │
│ Contacts · Memories · Scenes · Audit · Model Gateway     │
└───────────────┬──────────────────────┬───────────────────┘
                │                      │
┌───────────────▼──────────┐  ┌────────▼──────────────────┐
│ PostgreSQL / SQLite      │  │ Redis / Event Bus         │
│ 业务数据 · 审计 · 迁移   │  │ 缓存 · 实时事件          │
└──────────────────────────┘  └────────┬──────────────────┘
                                      │
                             ┌────────▼──────────────────┐
                             │ OpenAI-compatible Gateway │
                             │ 外部模型 · 校园节点 · Mock │
                             └───────────────────────────┘
```

| 层级 | 技术 |
|---|---|
| Web | Next.js 14、React 18、TypeScript、Zustand、Jest、Playwright |
| API | FastAPI、Pydantic、SQLAlchemy、Alembic、WebSocket |
| 数据 | PostgreSQL 15、Redis 7；测试和无 Docker 场景支持 SQLite |
| AI | OpenAI-compatible Model Gateway、本地或边缘节点、规则与 Mock 降级 |
| 工程 | pnpm workspace、uv、Ruff、mypy、pytest、Docker Compose |
| 架构 | 模块化单体、领域事件、公开服务接口、插件化场景 |

## 仓库结构

```text
CampusAgent/
├── apps/
│   ├── web/                    # Next.js 前端
│   │   ├── src/app/            # 页面与路由
│   │   ├── src/components/     # 应用与隐私 UI 组件
│   │   └── tests/              # 前端单元、Demo 与安全测试
│   └── api/                    # FastAPI 后端
│       ├── src/modules/        # 领域模块
│       ├── src/demo/           # Demo 数据与生命周期管理
│       ├── alembic/            # 数据库迁移
│       └── tests/              # 单元、集成、架构、安全与性能测试
├── packages/                   # 共享类型、UI、配置与 API 客户端
├── infra/                      # Docker、Mock 模型、监控与部署资产
├── scripts/                    # 启动、Demo、发布、安全与运维脚本
├── docs/                       # 产品、架构、API、隐私和开发文档
├── compose.yaml                # 本地完整环境
├── Makefile                    # 常用开发命令
└── .env.example                # 不含真实密钥的环境变量模板
```

## 快速开始

### 环境要求

| 工具 | 要求 |
|---|---|
| Git | 2.30+ |
| Node.js | 18.18+ |
| pnpm | 8.15（建议通过 Corepack 使用） |
| Python | 3.11 |
| uv | 0.5+ |
| Docker | 可选；用于 PostgreSQL、Redis 和 Mock Model |

检查本机工具版本：

```bash
./scripts/check-versions.sh
```

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

启动脚本会检测 Docker：

- Docker 可用时，启动 PostgreSQL、Redis 和 Mock Model，并执行迁移与 Demo 数据初始化；
- Docker 不可用时，使用 SQLite fallback 启动可演示环境；
- 默认端口被占用时，自动选择可用端口并打印实际地址。

启动后访问：

| 服务 | 默认地址 |
|---|---|
| Web | <http://localhost:3000> |
| API | <http://localhost:8000> |
| Swagger API 文档 | <http://localhost:8000/docs> |
| Mock Model | <http://localhost:8001> |

详细参数见 [一键启动说明](docs/development/ONE_CLICK_START.md)。

### 手动启动开发环境

```bash
# 1. 准备配置
cp .env.example .env

# 2. 安装前端依赖
corepack enable
corepack prepare pnpm@8.15.0 --activate
pnpm install --frozen-lockfile

# 3. 同步后端环境
uv sync --project apps/api --extra dev --frozen

# 4. 启动 PostgreSQL、Redis 和 Mock Model
make docker-up

# 5. 执行迁移并生成 Demo 数据
make db-migrate
make demo-seed

# 6. 启动 Web 与 API
make dev
```

> 后端依赖统一由 `uv` 管理。不要向系统 Python 执行裸 `pip install`；项目虚拟环境位于 `apps/api/.venv`。

## Demo 账号

所有 Demo 账号使用公开演示密码：`CampusAgentDemo2026!`

| 账号 | 邮箱 | 角色 |
|---|---|---|
| Demo Admin | `demo_admin@example.com` | 系统管理员 |
| Alice Chen | `demo_alice@example.com` | 学生、场景参与者 |
| Bob Lin | `demo_bob@example.com` | 学生、场景参与者 |
| Carol Wang | `demo_carol@example.com` | 学生、场景参与者 |
| Deleted User | `demo_deleted@example.com` | 软删除账号，用于失败演示 |

这些账号和密码仅用于虚构 Demo 数据，不得作为生产默认配置。完整演示流程见 [Demo Runbook](docs/development/P13-DEMO-RUNBOOK.md)。

## 常用命令

```bash
make help              # 查看全部命令
make dev               # 启动 Web 和 API
make test              # 运行全部测试
make lint              # 运行代码检查
make typecheck         # 运行类型检查
make build             # 构建项目
make format            # 格式化代码
make validate          # 执行完整验证
make demo-smoke        # 运行无服务器 Demo smoke 测试
make demo-reset        # 清理 Demo namespace
make demo-seed         # 幂等生成 Demo 数据
make release-check     # 执行发布候选检查
```

也可以分别验证：

```bash
make validate-api      # Ruff + mypy + pytest
make validate-web      # ESLint + TypeScript + Jest + Next.js build
```

## 配置模型服务

默认配置不会向外部模型发送数据。要使用 OpenAI-compatible 服务，请在本地 `.env` 中设置：

```dotenv
MODEL_GATEWAY_BASE_URL=https://your-model-gateway.example.com/v1
MODEL_GATEWAY_MODEL=your-model-name
MODEL_GATEWAY_API_KEY=your-api-key
MODEL_GATEWAY_IS_EXTERNAL=true
ENABLE_EXTERNAL_MODEL=true
```

`.env` 已被 Git 忽略。请勿将真实 API Key、数据库密码或加密密钥提交到仓库。

校园内部的 vLLM、llama.cpp 或其他服务只要提供兼容的 `/v1/chat/completions` 接口，也可以接入模型网关。

## 文档导航

| 主题 | 文档 |
|---|---|
| 产品范围 | [项目概览](docs/product/PROJECT_OVERVIEW.md) · [MVP 范围](docs/product/MVP_SCOPE.md) |
| 系统架构 | [模块边界](docs/architecture/MODULE_BOUNDARIES.md) · [数据流](docs/architecture/DATA_FLOW.md) |
| API 与实时通信 | [API 文档](docs/api/README.md) · [WebSocket 契约](docs/api/WEBSOCKET_CONTRACT.md) |
| 隐私与安全 | [隐私基线](docs/privacy/PRIVACY_BASELINE.md) · [权限矩阵](docs/architecture/PERMISSION_MATRIX.md) · [威胁模型](docs/security/THREAT_MODEL.md) |
| 场景设计 | [场景状态机](docs/architecture/SCENE_STATE_MACHINE.md) · [Demo 规范](docs/demo/DEMO_SPEC.md) |
| 本地开发 | [快速开始](docs/development/QUICK_START.md) · [工具链](docs/development/TOOLING.md) · [uv 环境](docs/development/UV_ENV.md) |
| 部署与运维 | [公网演示部署](docs/development/DEPLOYMENT_PUBLIC_DEMO_PLAN.md) · [恢复手册](docs/development/P12-RECOVERY-RUNBOOK.md) |
| 发布状态 | [RC1 Release Notes](docs/development/P13-RELEASE-NOTES.md) · [RC Checklist](docs/development/P13-RC-CHECKLIST.md) |

## 项目边界

CampusAgent 当前定位为可运行的校园智能体协作 MVP。项目明确不提供：

- 自动心理诊断或全量聊天情绪监控；
- 未经同意的学生风险画像、监控或数据上报；
- 智能体思维链的公开展示或长期持久化；
- 支付、报名等高风险不可逆操作的全自动执行；
- 允许场景插件、管理员或模型服务绕过授权读取私有数据的能力。

## 贡献与许可

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [安全策略](SECURITY.md)。

本项目尚未加入开源许可证。在许可证文件加入仓库前，默认保留全部权利。
