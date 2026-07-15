# 数据流图

> **版本**：v1.0  
> **基线日期**：2026-07-14  
> **状态**：已冻结  
> **维护者**：开发团队

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         信任边界                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Web 浏览器  │    │   Admin 管理  │    │   第三方模型   │         │
│  │  (用户端)     │    │   后台       │    │   API       │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │ HTTPS            │ HTTPS            │ HTTPS/OAuth    │
│         │ (加密)            │ (加密)            │ (可选)         │
└─────────┼──────────────────┼──────────────────┼───────────────┘
          │                  │                  │
          │ 信任边界          │ 信任边界          │ 外部依赖
          │ (浏览器→API)      │ (管理→API)       │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                 CampusAgent API (FastAPI)                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  API Layer → Service → Repository → Database    │  │
│  └──────────────────────────────────────────────────┘  │
│         │                  │                  │          │
│         │ 内部服务           │ 内部服务          │ 内部服务   │
│         ▼                  ▼                  ▼          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐         │
│  │  Redis   │   │PostgreSQL│   │Internal  │         │
│  │  (缓存)   │   │ (主数据库) │   │Model GW  │         │
│  └──────────┘   └──────────┘   └─────┬────┘         │
└────────────────────────────────────────┼──────────────┘
                                         │
                               ┌─────────┴──────────┐
                               │  信任边界            │
                               │ (API → 模型网关)      │
                               └─────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌───────────┐        ┌───────────┐        ┌───────────┐
            │ 本地边缘   │        │ 云端模型   │        │  Mock/    │
            │  节点     │        │  API     │        │ 规则引擎  │
            │ (优先)    │        │ (默认禁用) │        │ (备用)    │
            └───────────┘        └───────────┘        └───────────┘
```

## 2. 主要组件说明

### 2.1 前端层

**Web 浏览器**（Next.js）
- 用户交互界面
- 发起 HTTPS 请求
- 建立 WebSocket 连接
- 存储 Token（HttpOnly Cookie）

**Admin 管理后台**
- 独立界面或同一应用的管理路由
- 更高的权限要求
- 访问系统级数据

---

### 2.2 API 网关层

**CampusAgent API**（FastAPI）
- 统一入口
- 认证和授权
- 请求路由
- 响应统一格式
- 审计日志记录

**职责**：
- 解析 JWT Token
- 检查权限
- 调用对应的 Service
- 记录访问日志
- 错误处理和统一响应

---

### 2.3 业务服务层

**13个独立模块**（模块化单体）

```
API Layer
  ↓
Application Service（每个模块一个）
  ↓
Domain Logic
  ↓
Repository Interface
  ↓
Infrastructure（数据库、缓存、外部调用）
```

**关键服务**：
- Auth Service
- User Service
- Organization Service
- Conversation Service
- Agent Service
- Memory Service
- Scene Service
- Model Gateway Service
- Node Service
- Audit Service

---

### 2.4 数据存储层

**PostgreSQL**
- 主数据库
- 结构化数据
- 关系型数据
- pgvector（向量检索）

**Redis**
- 会话缓存
- WebSocket Pub/Sub
- 短期数据
- 限流计数器

---

### 2.5 AI 推理层

**模型网关**（统一封装）

**路由策略**：
```
输入 → Model Gateway → 路由决策
  ├─ 敏感数据？ → 优先本地节点
  ├─ 外部模型？ → 仅授权时允许（默认禁用）
  ├─ 节点不可用？ → 降级 Mock/规则
  └─ 统一封装 → 插件不直接调用厂商 SDK
```

**提供者**：
- **本地边缘节点**（优先）
- **外部模型 API**（默认禁用）
- **Mock 模型**（备用）
- **规则引擎**（备用）

---

## 3. 关键数据流

### 3.1 用户注册流程

```
用户浏览器
  → POST /api/v1/auth/register
  → API Gateway（认证中间件跳过）
  → Auth Service
  → User Repository（PostgreSQL）
  → 发布 UserRegistered 事件
  → Agent Service（监听事件）
  → 创建 Personal Agent
  → 返回 201 Created
```

**隐私控制**：
- 密码哈希存储
- 不返回密码字段
- 事件中不包含密码

---

### 3.2 私有偏好提交流程（核心隐私）

```
用户浏览器
  → POST /api/v1/scene-instances/{id}/private-submission
  → API Gateway（认证 + 权限检查）
  → Scene Service
  → 验证参与者身份
  → Memory Service（检查 ConsentRecord）
  → 加密存储 → PrivateSceneSubmission（PostgreSQL）
  → 更新 Participant 状态
  → 发布 scene.updated 事件
    → 只包含：submitted_count, total_count
    → 不含任何偏好内容
  → WebSocket → 群聊（其他成员只看到进度更新）
  → 返回 202 Accepted
```

**隐私控制点**：
1. ✅ 只接受 POST 请求（不允许 GET 读取）
2. ✅ 验证提交者身份（只能提交自己的）
3. ✅ 加密存储原始偏好
4. ✅ 生成偏好胶囊（最小化）
5. ✅ 发布事件不含内容
6. ✅ WebSocket 不推送内容
7. ❌ **消息表中无私有内容**

---

### 3.3 模型调用流程

```
场景插件/Agent
  → POST /internal/v1/model/chat
  → Model Gateway（隐私上下文检查）
  → 路由决策
    ├─ 本地节点健康？→ 路由到本地
    ├─ 包含敏感数据？→ 禁止路由到外部
    └─ 节点失败？→ 降级 Mock/规则
  → 调用模型
  → 记录 AgentRun（元数据，不含输入/输出）
  → 返回结构化结果
```

**隐私控制**：
- ❌ 不记录原始 Prompt
- ❌ 不记录完整响应
- ✅ 只记录：模型名、Token、延迟、哈希
- ✅ 敏感数据不路由到外部

---

### 3.4 私有偏好查询流程（禁止路径）

```
❌ 以下路径必须全部禁止：

1. 普通 GET /api/v1/messages 无法查询私有提交
   （私有提交不在 Message 表）

2. GET /api/v1/scene-instances/{id}/submissions 禁止
   （只有自己的提交可读，其他人都不能）

3. ORG_ADMIN 无法读取 PrivateSceneSubmission
   （权限矩阵明确禁止）

4. SCHOOL_ADMIN 无法读取 MemoryItem.content_encrypted
   （权限矩阵明确禁止）

5. 直接 SQL 查询被 ORM 权限层拦截
```

---

### 3.5 审计日志写入流程

```
任何敏感操作
  → 业务逻辑执行
  → Audit Service 记录
    → actor_id, action, resource_type, resource_id
    → purpose, result, request_id, timestamp
    → ❌ 不包含敏感内容
  → 写入 AuditLog（PostgreSQL）
  → 90天后自动清理
```

---

## 4. 信任边界

### 4.1 边界说明

| 边界 | 两侧 | 控制机制 | 说明 |
|------|------|---------|------|
| **浏览器 → API** | 用户端 → 服务端 | HTTPS + JWT | 认证和加密 |
| **管理后台 → API** | 管理员 → 服务端 | HTTPS + JWT + RBAC | 更高权限要求 |
| **API → 数据库** | 服务层 → 数据层 | 内部网络 + ORM | 无直接 SQL |
| **API → Redis** | 服务层 → 缓存层 | 内部网络 | 命名空间隔离 |
| **API → 模型网关** | 业务层 → AI层 | 内部服务调用 | 隐私上下文检查 |
| **模型网关 → 边缘节点** | AI层 → 边缘节点 | HTTPS + 节点身份认证 | 边缘节点是独立信任边界；校园内网不等于可信网络；生产使用 HTTPS；计划使用 mTLS 或等价节点身份认证；节点 endpoint 必须经过 allowlist 和 SSRF 校验；节点不得直接访问数据库、Redis 或其他业务模块；输入必须经过隐私上下文和数据最小化；输出必须经过 Schema 和敏感字段验证 |
| **模型网关 → 外部API** | AI层 → 第三方 | HTTPS + 授权 | 默认禁用 |

---

### 4.2 加密点

| 数据 | 加密时机 | 加密方式 | 解密时机 |
|------|---------|---------|---------|
| 用户密码 | 注册时 | bcrypt/argon2 | 登录验证时 |
| 智能体私有配置 | 写入时 | AES-256 | 所有者读取时 |
| 节点认证密钥 | 写入时 | AES-256 | 节点认证时 |
| 私有场景提交 | 写入时 | AES-256 | 所有者读取时（场景内） |
| 记忆内容 | 写入时 | AES-256 | 所有者读取时（授权后） |

**密钥管理**：
- 密钥存储在环境变量或 KMS
- 定期轮换
- 不同数据使用不同密钥

---

## 5. 敏感数据流标注

### P2 私有数据流（需加密 + 授权）

```
用户表单 → 加密 → PrivateSceneSubmission → 智能体提取 → 胶囊 → 评分 → 聚合 → 展示
```

**必须加密**：
- ✅ 写入时加密
- ✅ 传输加密（HTTPS）
- ✅ 存储加密（数据库加密）

**必须授权**：
- ✅ 读取需 ConsentRecord
- ✅ 通过 Memory Service

---

### P4 临时秘密数据流（自动销毁）

```
用户私有输入 → 加密 → PrivateSceneSubmission
                           ↓
                   场景结束后立即删除
                   最长24小时兜底
```

**必须满足**：
- ✅ 加密存储
- ✅ TTL 过期时间
- ✅ 定期清理任务
- ✅ 场景结束立即删除

---

## 6. 第三方依赖

### 6.1 外部模型 API（默认禁用）

**提供者**：
- OpenAI
- Anthropic
- 其他兼容 OpenAI 协议的模型

**调用条件**：
- 用户明确授权
- 配置允许外部模型
- 不包含敏感数据（根据隐私上下文）

**默认状态**：`ENABLE_EXTERNAL_MODEL=false`

---

### 6.2 其他外部依赖

**MVP 不依赖**：
- ❌ 地图 API
- ❌ 餐厅 API
- ❌ 支付 API
- ❌ 短信服务
- ❌ 邮件服务（可选）

**替代方案**：
- 内置餐厅数据（固定种子）
- 规则引擎降级
- Mock 数据

---

## 7. 部署拓扑

### 7.1 Docker Compose 部署

```yaml
services:
  frontend:
    - Next.js
    - 端口：3000

  api:
    - FastAPI
    - 端口：8000
    - 依赖：postgres, redis

  postgres:
    - PostgreSQL
    - 端口：5432
    - 数据卷：pgdata

  redis:
    - Redis
    - 端口：6379

  mock-model:
    - Mock 模型服务
    - 端口：8001
    - 备用路径

  # 可选
  prometheus:
    - 监控
    - 端口：9090
```

**网络**：
- 所有服务在同一个 Docker 网络
- 内部调用不经过公网
- 外部访问通过反向代理

---

### 7.2 边缘节点部署（比赛 Demo 可选）

```
校园内网

  CampusAgent Model Gateway
          ↕ HTTPS + 节点身份认证
  ┌─────────────┐
  │ Edge Node 1 │  ← 部署本地模型
  │ (GPU 服务器) │
  └─────────────┘

  Model Gateway 发起推理/健康检查请求 → Edge Node
  Edge Node 返回结果 → Model Gateway
  双向流量均受安全传输和节点认证约束
  EdgeNode 不直接访问业务 API、数据库或 Redis
```

**说明**：
- 真实边缘硬件在比赛 Demo 中可选，可以使用 Mock 或规则引擎演示
- 但 EdgeNode 管理、模型路由和安全契约属于 MVP
- 一旦配置真实节点，T-09 控制必须适用
- 不能因为真实硬件可选就把节点风险排除在威胁模型之外

---

## 8. 数据流检查清单

### 8.1 私有数据流检查

- [x] 用户表单 → 加密存储
- [x] 加密存储 → 智能体提取胶囊
- [x] 胶囊 → 协调层评分
- [x] 评分 → 聚合结果
- [x] 聚合结果 → 公开展示
- [x] 临时数据 → 清理

### 8.2 禁止路径检查

- [x] ❌ 私有偏好不经过 Message 表
- [x] ❌ 私有提交不经过 WebSocket
- [x] ❌ 管理员无法读取私有内容
- [x] ❌ 私有内容不进入日志

---

## 9. 相关文档

- [数据清单](../architecture/DATA_INVENTORY.md)
- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)

---

**下一步**：P0-07（完成威胁建模，依赖本数据流图）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
| 2026-07-15 | R1-28 新增"模型网关 → 边缘节点"信任边界；修正边缘节点部署表述，明确真实硬件可选但安全契约属于 MVP | - |
