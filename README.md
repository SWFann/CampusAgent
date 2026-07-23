# CampusAgent

隐私优先的智能体原生校园通讯与协作平台。

CampusAgent 让每名学生拥有一个由本人控制、按场景授权的个人智能体。智能体可以在校园组织与群聊场景中代表用户提交最小化的结构化偏好、参与低风险协商，但平台、管理员和其他成员默认不能读取用户的原始偏好、敏感记忆或智能体内部推理过程。

> 当前状态：**MVP RC1**（Release Candidate 1）。P0-P13 全部完成，契约已冻结（API `v1.0-frozen`，71 个端点；WebSocket `v1.0-frozen`）。后端 1432 个测试 + 前端 115 个测试通过。聚餐协商场景完整可演示，无公网可运行。详见 [Release Notes](docs/development/P13-RELEASE-NOTES.md) 和 [RC Checklist](docs/development/P13-RC-CHECKLIST.md)。

## Demo 要证明什么

比赛 Demo 聚焦一个完整场景：**宿舍聚餐去哪**。

1. 四名宿舍成员进入组织群聊并发起聚餐场景；
2. 每个人在私有页面提交预算、口味、禁忌、距离和时间偏好；
3. 个人智能体把原始输入转换为最小化的结构化“偏好胶囊”；
4. 协调层只使用胶囊评价候选餐厅，不公开自由辩论过程；
5. 群聊只展示提交进度、候选方案、聚合理由、投票和最终结果；
6. 用户确认结果后，系统清理临时偏好与私有评价；长期记忆必须再次征得用户同意。

核心命题是：**不暴露个人真实偏好，也能提高校园集体决策效率。**

## 产品边界

MVP 包含校园身份、组织、通讯、个人智能体、记忆与授权、场景插件、模型网关和管理视图。其中只有聚餐协商场景需要完整可运行；课堂讨论、社团策划、学习小组、新生助手与情绪记录仅保留展示和扩展位。

MVP 明确不做：

- 自动心理诊断或全量聊天情绪监控；
- 未经同意的学生风险画像或数据上报；
- 对用户公开或持久化智能体思维链；
- 让智能体执行支付、报名等高风险不可逆操作；
- 微服务集群、复杂联邦学习、安全多方计算或原生移动端；
- 让场景插件、管理员或模型厂商绕过授权读取私有数据。

## 设计原则

- **用户拥有智能体**：个人智能体从属用户，而非学校或平台管理员。
- **默认私有、最小披露**：原始偏好留在私有域，跨模块只流转完成任务所需的最小结构化信息。
- **明确授权**：默认代理等级为 L1；聚餐场景最高 L2，且必须逐场景授权、可撤销、可过期。
- **人工确认**：最终结果、报名、支付、外部分享等关键动作必须由用户确认。
- **隐私故障时关闭**：授权、加密或数据隔离失效时拒绝执行，不能降级为公开处理。
- **模块化单体**：MVP 保持低运维复杂度，同时用公开服务接口和领域事件守住模块边界。
- **场景插件化**：场景只能调用公开服务，不能直接查询其他模块的数据表。

## 计划技术基线

| 层级 | 计划选型 |
|---|---|
| Web | Next.js、TypeScript、Tailwind CSS、shadcn/ui、Zustand |
| API | FastAPI、Pydantic、SQLAlchemy、Alembic、WebSocket |
| 数据 | PostgreSQL、pgvector、Redis，MinIO 可选 |
| AI | OpenAI-compatible Model Gateway、本地/边缘模型、Mock/规则降级 |
| 可观测性 | Prometheus、Grafana、DCGM Exporter（可选） |
| 部署 | Docker Compose，模块化单体 |

选型是当前设计基线，正式实现前通过 ADR 固化关键决定。

## 仓库结构

```text
CampusAgent/
├── apps/                       # 可部署应用
│   ├── web/                    # Next.js Web（待实现）
│   └── api/                    # FastAPI 模块化单体（待实现）
├── packages/                   # 跨应用共享包
│   ├── api-client/             # OpenAPI 生成客户端
│   ├── shared-types/           # 共享契约类型
│   ├── ui/                     # 设计系统与共享组件
│   └── config/                 # 工具配置基线
├── infra/                      # 本地运行、监控和部署资产
│   ├── docker/
│   ├── prometheus/
│   └── scripts/
├── docs/
│   ├── product/                # 产品范围与完整计划书
│   ├── architecture/           # 架构和模块边界
│   ├── api/                    # HTTP、WebSocket 与事件契约
│   ├── privacy/                # 数据分类、授权、保留与审计
│   ├── demo/                   # 比赛 Demo 流程与验收
│   ├── development/            # 仓库和协作规范
│   └── decisions/              # ADR 架构决策记录
├── tests/
│   ├── e2e/                    # 核心演示流程验收
│   └── fixtures/               # 纯虚构、无敏感信息的测试数据
├── .env.example                # 环境变量名称，不含真实密钥
├── .editorconfig
├── .gitignore
├── CONTRIBUTING.md
└── SECURITY.md
```

目录内的 README 是责任边界说明。MVP RC1 中 `apps/web` 和 `apps/api` 已完整实现。

## 文档导航

- [项目概览](docs/product/PROJECT_OVERVIEW.md)
- [完整项目计划书](docs/product/CampusAgent_Project_Plan.md)
- [架构与模块边界](docs/architecture/MODULE_BOUNDARIES.md)
- [API 契约说明](docs/api/README.md)
- [隐私工程基线](docs/privacy/PRIVACY_BASELINE.md)
- [Demo 规范与验收](docs/demo/DEMO_SPEC.md)
- [详细开发计划表](docs/development/DEVELOPMENT_PLAN.md)
- [快速开始指南](docs/development/QUICK_START.md)
- [工具链规范](docs/development/TOOLING.md)
- [UI 初步设计与自然语言规范](docs/design/UI_DESIGN_GUIDE.md)
- [仓库协作规范](docs/development/REPOSITORY_CONVENTIONS.md)
- [架构决策记录](docs/decisions/README.md)
- [安全策略](SECURITY.md)
- [Release Notes (RC1)](docs/development/P13-RELEASE-NOTES.md)
- [RC Checklist](docs/development/P13-RC-CHECKLIST.md)
- [演示 Runbook](docs/development/P13-DEMO-RUNBOOK.md)
- [公网演示部署计划](docs/development/DEPLOYMENT_PUBLIC_DEMO_PLAN.md)
- [宿舍聚餐群聊化计划](docs/development/DORM_DINNER_CHAT_SCENE_REDESIGN_PLAN.md)
- [验收证据](docs/development/P13-ACCEPTANCE-EVIDENCE.md)
- [恢复操作手册](docs/development/P12-RECOVERY-RUNBOOK.md)

## 环境要求

| 工具 | 版本 | 用途 |
|---|---|---|
| uv | >= 0.5 | Python 版本、虚拟环境与依赖管理 |
| Python | 3.11.15 | 由 uv 按 `apps/api/.python-version` 管理 |
| Node.js | >= 18.18 | 前端 Next.js |
| corepack/pnpm | pnpm >= 8 | 前端包管理 |
| Docker（可选）| 任意现代版本 | 容器化部署 PostgreSQL/Redis/Mock Model |
| Git | >= 2.30 | 版本控制 |

### Python 环境（uv）

后端统一由 **uv** 管理。虚拟环境位于 `apps/api/.venv`，缓存与 uv 可选下载的 Python 运行时位于仓库 `.local/`，不向系统 Python 安装任何依赖。

```bash
# 创建/同步项目环境（含开发依赖）
uv sync --project apps/api --extra dev --frozen

# 在项目环境中运行 Python，无需手动激活
uv run --project apps/api --extra dev --frozen python --version
```

不要使用裸 `python`、`pip install` 或全局环境安装后端依赖。`Makefile` 和启动脚本已统一调用 uv。

### 已安装的核心依赖

- fastapi 0.139.0、uvicorn 0.51.0、pydantic 2.13.4
- sqlalchemy 2.0.51、alembic 1.18.5、redis 8.0.1

详细说明请参阅 [uv 环境文档](docs/development/UV_ENV.md)。

## 快速开始

### 一键启动（推荐）

Linux / WSL / macOS：

```bash
cd /root/CampusAgent
./scripts/start.sh
```

Windows PowerShell：

```powershell
cd C:\path\to\CampusAgent
.\scripts\start.ps1
```

启动脚本会自动检测 Docker：

- Docker 可用：启动 PostgreSQL、Redis、Mock Model，迁移数据库并种子 demo 数据。
- Docker 不可用：自动使用 SQLite fallback，仍可打开网站和 API。

启动后访问：

```text
Web:      http://localhost:3000
API:      http://localhost:8000
API Docs: http://localhost:8000/docs
```

如果默认端口已被占用，脚本会自动选择下一个可用端口，并在终端输出实际访问地址。

更多参数见 [One-Click Start](docs/development/ONE_CLICK_START.md)。

### 公网演示

如果需要让同学通过公网参与真实投票，可以选择：

- 快速演示：Cloudflare Tunnel / Tailscale Funnel 暴露本机 `web` 和 `api`。
- 稳定演示：VPS + Docker Compose + Caddy 自动 HTTPS。

部署前阅读 [公网演示部署计划](docs/development/DEPLOYMENT_PUBLIC_DEMO_PLAN.md)。项目提供 `compose.public-demo.yaml`、`infra/caddy/Caddyfile.public-demo.example` 和 `scripts/check_public_demo.sh` 用于生产演示配置检查。

### 方式 A：Docker 可用时（完整环境）

```bash
# 1. 克隆仓库
git clone <repo-url> CampusAgent
cd CampusAgent

# 2. 安装前端依赖
corepack pnpm install --frozen-lockfile

# 3. 按锁文件同步后端项目环境
uv sync --project apps/api --extra dev --frozen

# 4. 复制环境变量
cp .env.example .env

# 5. 启动核心依赖（PostgreSQL、Redis、Mock Model）
make docker-up
# 或: docker compose up -d postgres redis mock-model

# 6. 运行数据库迁移
(cd apps/api && uv run --project . --extra dev --frozen alembic -c alembic.ini upgrade head)

# 7. 种子演示数据
make demo-seed

# 8. 启动开发服务
make dev
# Web: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### 方式 B：Docker 不可用时（离线/无 Docker）

无需 Docker、PostgreSQL 或 Redis 即可完成全部验证。测试和演示数据使用 SQLite in-memory。

```bash
# 1. 安装依赖
corepack pnpm install --frozen-lockfile
uv sync --project apps/api --extra dev --frozen

# 2. 验证后端（ruff + mypy + pytest）
make validate-api

# 3. 验证前端（lint + typecheck + test + build）
make validate-web

# 4. 运行演示 smoke 测试（进程内 SQLite，11 步全通过）
make demo-smoke
```

## 验证命令

```bash
# 全量验证（API + Web）
make validate

# 单独验证后端
make validate-api    # ruff + mypy + pytest

# 单独验证前端
make validate-web    # lint + typecheck + test + build

# 依赖一致性检查
uv run --project apps/api --extra dev --frozen python -m pip check

# Release Candidate 检查
make release-check

# 收集验收证据
make release-evidence
```

## 演示数据

```bash
# 重置演示数据（仅删除 demo namespace，保留其他数据，生产环境 fail-closed）
make demo-reset

# 种子演示数据（幂等，可重复运行）
make demo-seed

# 运行演示 smoke 测试（进程内，无需服务器）
make demo-smoke
```

### Demo 账号

所有 demo 账号使用同一密码：`CampusAgentDemo2026!`

| 账号 | 邮箱 | 角色 | 用途 |
|---|---|---|---|
| Demo Admin | `demo_admin@example.com` | 系统管理员 | 管理后台、demo 重置 |
| Alice Chen | `demo_alice@example.com` | 学生 | 聚餐场景参与者 |
| Bob Lin | `demo_bob@example.com` | 学生 | 聚餐场景参与者 |
| Carol Wang | `demo_carol@example.com` | 学生 | 聚餐场景参与者 |
| Deleted User | `demo_deleted@example.com` | 学生（软删除） | 登录失败演示 |

> 注意：这是公开的 demo 密码，仅用于演示数据，不得用于生产默认配置。

完整演示流程见 [演示 Runbook](docs/development/P13-DEMO-RUNBOOK.md)。

## Docker Compose 开发

项目根目录的 `compose.yaml` 提供完整的本地开发编排：

```bash
# 启动核心依赖（PostgreSQL、Redis、Mock Model）
make docker-up

# 或直接使用 docker compose
docker compose up -d postgres redis mock-model

# 启动全部服务（包括 web 和 api）
docker compose up -d

# 查看服务状态
docker compose ps

# 停止服务
docker compose down
```

服务端口：
- Web: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Mock Model: http://localhost:8001

详见 [infra/docker/README.md](infra/docker/README.md)。

## 开发命令

```bash
# 启动开发环境（Web + API）
make dev

# 运行全部测试
make test

# 代码检查
make lint

# 类型检查
make typecheck

# 构建项目
make build

# 格式化代码
make format
```

完整命令列表运行 `make help` 查看。首次使用请阅读 [快速开始指南](docs/development/QUICK_START.md)。

## 贡献与许可

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。本项目尚未选择开源许可证；在许可证文件加入仓库前，默认保留全部权利。
