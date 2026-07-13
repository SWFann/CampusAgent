# 架构与模块边界

## 架构风格

MVP 采用前后端分离、模块化单体后端、插件化场景、统一模型网关、PostgreSQL 主存储和 Redis 实时/缓存。暂不引入微服务或消息中间件集群。

依赖方向固定为：

```text
API → Application Service → Domain → Repository Interface → Infrastructure
```

非同步副作用优先通过领域事件解耦。模块可以依赖对方公开的 Service Interface、Schema 和事件，禁止直接导入对方 ORM Model 或访问对方内部表。

## 后端模块职责

| 模块 | 单一职责 |
|---|---|
| auth | 注册、登录、会话和身份凭据 |
| users | 用户资料和生命周期 |
| organizations | 组织树、成员与组织角色 |
| directory | 基于可见性策略的人员/组织搜索 |
| conversations | 会话、参与者、消息与实时事件 |
| agents | 个人/组织智能体、代理级别和运行元数据 |
| memories | 私有记忆、分类、访问策略与删除 |
| scenes | 场景注册、状态机、参与者、候选和结果 |
| model_gateway | 逻辑模型路由、隐私上下文和降级 |
| nodes | 边缘节点、部署、健康与资源指标 |
| notifications | 用户通知 |
| audit | 不含敏感正文的结构化审计 |
| admin | 经授权的系统管理视图 |
| wellbeing | 与通用校园域隔离的自愿式心理支持 |

## 场景插件边界

场景插件只能通过 `MemoryService`、`ConsentService`、`AgentService`、`ConversationService`、`ModelGateway` 和 `AuditService` 工作。插件不得直接查询记忆、用户或消息表，不得直接写群消息，不得直接调用模型厂商 SDK，也不得持久化未声明的数据。

统一生命周期：

```text
DRAFT
→ WAITING_FOR_PARTICIPANTS
→ WAITING_FOR_CONSENT
→ WAITING_FOR_PRIVATE_INPUT
→ PROCESSING
→ CANDIDATES_READY
→ VOTING
→ CONFIRMING
→ COMPLETED
```

异常终态为 `CANCELLED`、`FAILED`、`EXPIRED`。只有 Scene Service 可以推进状态。

## 数据隔离

- 普通消息不承载私有偏好；
- 私有提交、偏好胶囊和候选私有评价使用独立存储与 TTL；
- 记忆只能通过 Memory Service 按 owner、purpose、category 和 consent 查询；
- Agent Run 只记录模型、延迟、Token、状态和输入/输出哈希；
- Wellbeing 数据使用独立数据域、权限策略和审计类别；
- 管理后台只聚合运行指标，不提供私有内容入口。

## 关键领域事件

- `UserRegistered`：由 Agent 模块监听并创建个人智能体；
- 会话参与者变化：通知实时层更新订阅；
- 场景阶段变化：向群聊发布不含私有输入的状态卡；
- 场景完成/过期：触发私有临时数据清理和结构化审计。

具体字段和接口以完整计划书及后续冻结的 OpenAPI/事件契约为准。
