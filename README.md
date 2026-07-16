# CampusAgent

隐私优先的智能体原生校园通讯与协作平台。

CampusAgent 让每名学生拥有一个由本人控制、按场景授权的个人智能体。智能体可以在校园组织与群聊场景中代表用户提交最小化的结构化偏好、参与低风险协商，但平台、管理员和其他成员默认不能读取用户的原始偏好、敏感记忆或智能体内部推理过程。

> 当前状态：P0 契约已冻结（API `v1.0-frozen`，68 个 MVP HTTP 端点 + 3 个 internal 端点 = 71 个总文档化端点；WebSocket `v1.0-frozen`），P1 工程骨架已可安装、测试和构建，FastAPI/Next.js 健康基线可运行；业务模块、数据库和 Demo 场景尚未实现。R1-E 已完成本地冻结提交，远端 CI 观察需推送后确认。

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

目录内的 README 是责任边界说明，不代表对应模块已经实现。

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

## Python 虚拟环境

本项目使用 **Conda 虚拟环境** 管理 Python 依赖，确保环境隔离和一致性。

### 环境信息

- **环境名称**：`CampusAgent`
- **Python 版本**：3.11.15
- **Windows 当前环境位置**：`D:\Conda\Soft\envs\CampusAgent`（其他系统以 `conda env list` 为准）

### 使用说明

```bash
# 激活虚拟环境（后端开发前必须执行）
conda activate CampusAgent

# 验证环境
python --version  # 应显示 Python 3.11.15

# 停用环境
conda deactivate
```

### 重要说明

⚠️ **所有后端 Python 代码必须在 `CampusAgent` 虚拟环境中运行**：

- 启动 FastAPI 服务前，先激活环境
- 运行测试前，先激活环境
- 安装 Python 依赖前，先激活环境
- 执行数据库迁移前，先激活环境

### 已安装的核心依赖

- fastapi 0.139.0
- uvicorn 0.51.0
- pydantic 2.13.4
- sqlalchemy 2.0.51
- alembic 1.18.5
- redis 8.0.1

详细说明请参阅 [Conda 环境文档](docs/development/CONDA_ENV.md)。

## 开发命令

```bash
# 启动开发环境
corepack pnpm dev

# 运行测试
corepack pnpm test

# 代码检查
corepack pnpm lint

# 类型检查
corepack pnpm typecheck

# 构建项目
corepack pnpm build
```

**注意**：首次使用请阅读 [快速开始指南](docs/development/QUICK_START.md)。

## 后续实施顺序

1. 冻结核心领域模型、OpenAPI、WebSocket 事件和隐私威胁模型；
2. 初始化 Web/API 工程、PostgreSQL、Redis、迁移与统一配置；
3. 完成身份、用户、组织和 RBAC；
4. 完成会话、消息与 WebSocket；
5. 完成个人智能体、记忆、授权和审计；
6. 完成 Scene Core、聚餐插件、Mock 模型与数据清理；
7. 完成模型/节点管理、演示数据、E2E 与一键启动。

当前工程底座已提供 `corepack pnpm dev`、`corepack pnpm test`、`corepack pnpm lint`、`corepack pnpm typecheck`、`corepack pnpm build` 和 `corepack pnpm seed`。数据库、迁移和 Demo 业务流程将在 P2 之后逐步实现。

## 贡献与许可

提交代码前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。本项目尚未选择开源许可证；在许可证文件加入仓库前，默认保留全部权利。
