---
name: campusagent-project-overview
description: CampusAgent 项目全面理解与核心架构
metadata:
  type: reference
---

# CampusAgent 项目深度理解

## 项目定位与核心价值

**CampusAgent** 是一个面向高校的隐私优先智能体原生校园通讯与协作平台。

### 核心命题
> **不暴露个人真实偏好，也能提高校园集体决策效率**

这个项目不是一个简单的聊天机器人或心理辅导工具，而是一个完整的校园数字协作底座。

## 解决的核心问题

### 1. 校园系统碎片化
- 教务、聊天、课程、心理平台分散，学生需要重复注册和填写
- 缺乏统一身份、组织、关系和上下文

### 2. 学生不愿公开真实想法
- 预算限制、饮食禁忌、时间冲突等偏好不愿在群聊中公开
- 直接表达可能造成尴尬、标签化和人际压力

### 3. 传统平台缺乏个体化协作
- 以"账号、表单、通知"为中心，而非"人、关系、智能体、上下文"
- 无法理解学生长期偏好，不能代表学生参与协商

## 核心技术架构

### 架构风格
**前后端分离 + 模块化单体后端 + 插件化场景 + 统一模型网关**

```
UI (Next.js) → FastAPI Application → 13个独立模块 → PostgreSQL + Redis
                                    ↓
                              统一模型网关
                                    ↓
                   本地边缘节点 / 外部模型 API
```

### 技术栈基线

| 层级 | 技术选型 |
|------|---------|
| 前端 | Next.js + TypeScript + Tailwind + shadcn/ui + Zustand |
| 后端 | FastAPI + Pydantic + SQLAlchemy + Alembic + WebSocket |
| 数据 | PostgreSQL + pgvector + Redis (+ MinIO) |
| AI | OpenAI-compatible Model Gateway + 本地/边缘模型 |
| 监控 | Prometheus + Grafana + DCGM Exporter |
| 部署 | Docker Compose |

### 13 个后端模块

1. **auth** - 注册、登录、会话和身份凭据
2. **users** - 用户资料和生命周期
3. **organizations** - 组织树、成员与角色
4. **directory** - 基于可见性的人员/组织搜索
5. **conversations** - 会话、消息与 WebSocket
6. **agents** - 个人/组织智能体、代理级别
7. **memories** - 私有记忆、分类、访问策略
8. **scenes** - 场景注册、状态机、协调
9. **model_gateway** - 逻辑模型路由与降级
10. **nodes** - 边缘节点、健康检查、指标
11. **notifications** - 用户通知
12. **audit** - 不含敏感正文的审计日志
13. **admin** - 经授权的系统管理视图

## 核心隐私设计

### 数据分类体系（5级）

| 等级 | 示例 | 存储要求 |
|------|------|---------|
| P0 公开 | 组织名称 | 普通存储 |
| P1 内部 | 班级成员关系 | 访问控制 |
| P2 私有 | 饮食偏好、预算 | 加密 + 授权 + 审计 |
| P3 高敏感 | 心理状态 | 独立域 + 强隔离 |
| P4 临时秘密 | 场景原始输入 | 临时存储 + 自动销毁 |

### 智能体代理权限（5级）

- **L0** 只读辅助
- **L1** 建议（默认）
- **L2** 受限代言（聚餐场景最高授权）
- **L3** 受限决策
- **L4** 受限执行（MVP不开放）

### 隐私协商协议（7阶段）

```
用户私有输入 → 个人智能体生成偏好胶囊 → 候选方案生成 → 私有评分 → 聚合 → 输出 → 销毁临时数据
```

关键设计：
- ✅ 原始偏好只进入用户私有域
- ✅ 协调层只接收最小化结构化胶囊
- ✅ 群聊只显示候选、理由、投票结果
- ❌ 不公开自由辩论过程
- ❌ 不长期保存原始辩论文本
- ❌ 不能推断心理或经济标签

### 聚合公式

```python
candidate_score = hard_constraint_gate × (
    0.60 × mean_utility          # 平均效用
  + 0.20 × fairness_score        # 公平性（避免只满足少数人）
  + 0.10 × distance_score        # 距离
  + 0.10 × budget_score          # 预算
)
```

## 首个演示场景：宿舍聚餐去哪

### 完整流程

1. **林晓**在宿舍群发起"周五聚餐"场景
2. 四名成员：**林晓、陈宇、周宁、许然**必须逐人确认 L2 授权
3. 每人**单独进入私有表单**填写偏好（预算、口味、禁忌、时间等）
4. 群聊**只显示进度**：`3/4`、`4/4`，**不显示任何个人偏好**
5. 系统启动协商：
   - 个人智能体抽取偏好胶囊
   - 协调层调用 Mock/规则引擎评分
   - 生成3项候选餐厅
6. 群聊展示：
   - 候选方案名称和匹配分
   - "满足全部硬性限制"等聚合理由
   - **隐私说明：个人偏好未公开**
7. 用户投票 → 发起人确认 → 询问是否写入长期记忆
8. **拒绝写入** → 系统清理临时偏好、胶囊、私有评价
9. 演示审计页：显示"聚餐场景在某时间读取了饮食偏好"
10. 演示管理员视图：**证明没有查看个人偏好的入口**

### 隐私特性证明

- ✅ A用户看不到B的预算
- ✅ 群主看不到成员自由文本
- ✅ 群聊无智能体辩论记录
- ✅ 管理员后台无"查看偏好"入口
- ✅ 最终理由不指认具体成员
- ✅ 场景结束后私有输入自动删除
- ✅ 用户能看到结构化访问记录

## 模块边界与依赖规则

### 依赖方向固定

```
API → Application Service → Domain → Repository Interface → Infrastructure
```

### 允许的跨模块依赖

- 公开 Service Interface
- Schema
- 领域事件
- 公共基础设施

### 严格禁止

- ❌ 直接导入其他模块的 ORM Model
- ❌ 直接查询其他模块的数据表
- ❌ 场景插件直接查询用户/记忆/消息表
- ❌ 场景插件直接写群消息
- ❌ 直接调用模型厂商 SDK
- ❌ 在普通消息接口提交私有偏好

## 场景插件规范

场景插件（如聚餐、课堂、社团）只能通过以下公开服务工作：

```
MemoryService
ConsentService
AgentService
ConversationService
ModelGateway
AuditService
```

### 统一生命周期状态机

```
DRAFT → WAITING_FOR_PARTICIPANTS → WAITING_FOR_CONSENT
  → WAITING_FOR_PRIVATE_INPUT → PROCESSING → CANDIDATES_READY
  → VOTING → CONFIRMING → COMPLETED

异常终态：CANCELLED, FAILED, EXPIRED
```

只有 SceneService 可以推进状态转换。

## 数据保留策略

| 数据类型 | 保留期限 |
|---------|---------|
| 原始私有场景提交 | 场景结束立即删除，最长 24h |
| 偏好胶囊 | 场景结束删除，最长 24h |
| 私有候选评价 | 场景结束删除，最长 24h |
| 最终场景结果 | 可保留 |
| Agent Run 元数据 | 30 天 |
| 系统审计元数据 | 90 天 |
| 长期记忆 | 用户主动确认后保留 |

## 模型与边缘节点管理

### 模型网关设计

```
场景插件 → Model Gateway → 路由决策
  ├─ 敏感数据？ → 优先本地节点
  ├─ 外部模型？ → 仅用户授权时允许
  ├─ 节点不可用？ → 降级规则/Mock
  └─ 统一封装 → 插件不直接调用厂商SDK
```

### 核心原则

- 外部模型默认关闭
- 敏感数据不记录 Prompt
- 模型失败可降级，**隐私能力不可降级**
- 日志只记录：ID、模型名、Token、延迟、哈希

## 用户角色体系

### 全局角色

- **STUDENT** - 学生
- **TEACHER** - 教师
- **COUNSELOR** - 辅导员/心理支持
- **ORG_ADMIN** - 组织管理员
- **SCHOOL_ADMIN** - 校方管理员
- **SYSTEM_ADMIN** - 系统管理员

### 组织内角色（独立）

- **OWNER**
- **ADMIN**
- **MEMBER**
- **GUEST**

一个学生可以同时是：全局 `STUDENT` + 社团 `OWNER` + 课程 `MEMBER`

## 实施路线图

### 阶段 0：项目初始化
- Monorepo、Docker Compose、CI
- PostgreSQL + Redis
- FastAPI + Next.js 骨架
- OpenAPI + Mock Server

### 阶段 1：身份与组织底座
- Auth/User/Organization/Membership/Directory/RBAC

### 阶段 2：聊天底座
- Conversation/Participant/Message/WebSocket

### 阶段 3：智能体与记忆
- Personal Agent/Memory/Consent/Audit

### 阶段 4：聚餐场景（核心）
- Scene Core + Meal Plugin + 完整流程

### 阶段 5：模型与节点管理
- Model Gateway/Node Management/Admin Dashboard

### 阶段 6：演示与质量
- 演示数据、E2E测试、一键启动、备用Mock

## 关键设计原则

1. **用户拥有智能体** - 从属用户，而非学校/管理员
2. **默认私有、最小披露** - 只流转完成任务所需的最小信息
3. **明确授权** - 逐场景授权、可撤销、可过期
4. **人工确认** - 高风险动作必须用户确认
5. **隐私故障时关闭** - 拒绝执行而非降级为公开
6. **模块化单体** - 低运维复杂度 + 清晰模块边界
7. **场景插件化** - 通过公开接口接入，不直接访问数据

## 测试重点

### 必测隐私断言（9条）

1. A 无法读取 B 的偏好
2. 群主和 SchoolAdmin 无法读取 P2/P3 正文
3. 普通聊天接口查不到私有提交
4. 插件不能绕过 MemoryService
5. 日志和指标不含敏感正文
6. 场景结束后临时数据确实删除
7. 取消授权后新访问被拒绝
8. 数据导出只包含当前用户数据
9. 隐私依赖故障时场景失败关闭

## 心理健康模块边界（谨慎原则）

### 允许
- 用户主动倾诉、情绪日记
- 校园心理资源推荐
- 咨询预约入口
- 自愿授权提醒

### 禁止
- ❌ 自动分析全部聊天
- ❌ 生成不可见风险标签
- ❌ 未授权上报辅导员
- ❌ 临床诊断
- ❌ 心理数据用于奖惩

**数据域隔离**：心理数据使用独立表、权限策略和审计类别

## 代码约束

### 后端

- 全部函数类型注解
- Pydantic Schema 与 ORM Model 分离
- Repository 不含业务规则
- Service 不返回 ORM 对象
- API 只负责参数解析、鉴权、响应
- 带时区 UTC 存储
- UUID 作为所有 ID
- Alembic 迁移（禁止手工修改数据库）
- 敏感字段不出现于 `repr`
- 外部调用设置超时、重试、熔断
- 场景状态转换必须用状态机

### 日志禁止

```python
# 禁止
logger.info(f"user preference: {payload}")
logger.debug(f"prompt: {messages}")

# 允许
logger.info(
    "scene_submission_received",
    extra={
        "scene_instance_id": scene_id,
        "user_id_hash": hash_user_id(user_id),
        "payload_size": len(encrypted_payload)
    }
)
```

### 环境变量约束

```env
LOG_PROMPT_CONTENT=false  # 必须
ENABLE_EXTERNAL_MODEL=false  # 默认关闭
PRIVATE_SCENE_TTL_HOURS=24
```

## 当前项目状态

**阶段**：项目初始化阶段
**状态**：只包含项目边界、Demo规范、架构约束与目录骨架
**已完成**：文档体系、架构设计、隐私基线
**未实现**：任何业务代码或可运行服务

### 文件结构

```
CampusAgent/
├── apps/                    # 可部署应用（空）
│   ├── web/                 # Next.js Web
│   └── api/                 # FastAPI
├── packages/                # 共享包
│   ├── api-client/
│   ├── shared-types/
│   ├── ui/
│   └── config/
├── infra/                   # 部署资产
│   ├── docker/
│   ├── prometheus/
│   └── scripts/
├── docs/                    # 完整文档体系
│   ├── product/            # 产品文档
│   ├── architecture/       # 架构文档
│   ├── api/                # API规范
│   ├── privacy/            # 隐私基线
│   ├── demo/               # Demo规范
│   ├── development/        # 开发规范
│   └── decisions/          # ADR
├── tests/                   # 测试目录（空）
└── README.md
```

## 关键设计决策

### 为什么模块化单体而非微服务？

**理由**：
- MVP 保持低运维复杂度
- 清晰模块边界，未来可拆分
- 适合小团队并行开发
- 避免分布式系统复杂性

**决策记录**：待创建 ADR `0001-modular-monolith.md`

### 为什么私有输入必须独立于消息系统？

**理由**：
- 消息系统有可见性控制、历史查询、全文搜索
- 私有偏好需要独立加密、TTL、访问审计
- 混合存储会增加误读风险
- 便于未来独立扩展或替换

### 为什么协调层只返回结构化胶囊？

**理由**：
- 防止原始偏好泄露
- 防止智能体辩论文本暴露
- 防止推断用户敏感属性
- 减少协调层权限和信任需求

### 为什么模型调用必须经过统一网关？

**理由**：
- 统一隐私上下文检查
- 统一降级策略
- 便于监控和审计
- 防止场景插件绕过安全策略

## 后续实施关键步骤

1. **冻结核心契约**
   - 领域模型
   - OpenAPI 规范
   - WebSocket 事件格式
   - 隐私威胁模型

2. **初始化工程**
   - Docker Compose 环境
   - 数据库迁移 (Alembic)
   - 统一配置管理

3. **按模块顺序实现**
   - 优先级：身份组织 → 聊天 → 智能体记忆 → 场景 → 模型节点

4. **并行开发策略**
   - 先冻结接口 + Mock Server
   - 各组通过契约并行开发
   - 定期集成测试

5. **隐私从第一天开始**
   - 单元测试包含隐私断言
   - 集成测试验证数据隔离
   - 代码审查检查日志规范

## 演示价值

这个项目的最大创新点不在于使用 AI，而在于：

1. **建立新的隐私范式**：学生可以保留不愿公开的偏好，同时参与集体决策
2. **智能体代表协作**：智能体在授权范围内参与，但不替代最终决策
3. **平台非侵入性**：校方提供基础设施，但不借此获得对学生的无限知情权
4. **模块化可扩展**：同一底座可接入多种校园场景

**比赛 Demo 的核心证明**：
> 5分钟内展示四名学生在不互相公开预算、禁忌和私人理由的前提下完成宿舍聚餐决策

---
**文档生成时间**：2026-07-13
**项目状态**：设计完成，待实现
**核心参考**：[完整项目计划书](docs/product/CampusAgent_Project_Plan.md)、[架构边界](docs/architecture/MODULE_BOUNDARIES.md)、[隐私基线](docs/privacy/PRIVACY_BASELINE.md)
