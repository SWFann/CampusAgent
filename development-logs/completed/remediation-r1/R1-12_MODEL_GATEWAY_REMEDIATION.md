# R1-12 任务日志：补全 Model Gateway API

> **任务编号**：R1-12
> **执行日期**：2026-07-14
> **执行人**：Claude
> **任务目标**：补全 Model Gateway API 契约，包括 chat、embedding、health，重点定义 privacy_context、超时、结构化输出、模型降级、失败关闭和审计元数据

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：补全 Model Gateway
- **具体操作**：chat、embedding、health
- **完成标准**：`privacy_context`、超时、结构化输出和降级规则明确

### 前置条件验证

✅ R1-06 已完成：建立端点对照清单（68 个唯一端点）
✅ R1-07 已完成：补全 Directory API（3 个端点）
✅ R1-08 已完成：补全 Conversation API（5 个端点）
✅ R1-09 已完成：补全 Agent API（6 个端点）
✅ R1-10 已完成：补全 Memory API（7 个端点）
✅ R1-11 已完成：补全 Scene API（12 个端点）

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
4. ✅ docs/architecture/DATA_FLOW.md - 数据流架构（第112-227行）
5. ✅ docs/security/THREAT_MODEL.md - 威胁模型（第183-221行）
6. ✅ docs/decisions/0004-model-routing.md - ADR-004 模型路由决策
7. ✅ docs/privacy/PRIVACY_BASELINE.md - 隐私基线

## 执行过程

### 1. 现状分析

#### 1.1 API_CONTRACT.md 中已有的内部端点

从文档阅读结果看，API_CONTRACT.md 中已存在以下内部引用：
- **Line 1006**：Agent API 中有内部 Model Gateway 调用说明
- **Line 1286**：Memory API 中有 embedding 接口引用

但这些引用是说明性的，缺少完整的端点定义。

#### 1.2 MVP_SCOPE.md 中的 Model Gateway 端点（共 3 个）

根据 MVP 范围，Model Gateway 应包含以下内部端点：

```
POST /internal/v1/model/chat - 对话调用
POST /internal/v1/model/embedding - Embedding 生成
GET /internal/v1/model/health - 健康检查
```

#### 1.3 ADR-004 中的路由策略

从 ADR-004 文档（`docs/decisions/0004-model-routing.md`）提取关键规则：

**路由优先级**：
1. **本地边缘节点**（敏感数据时优先）
2. **外部模型 API**（仅授权且启用时）
3. **Mock 模型**（备用）
4. **规则引擎**（最终降级）

**隐私上下文（privacy_context）结构**：
```json
{
  "contains_sensitive_data": boolean,
  "allow_external_provider": boolean,
  "purpose": string
}
```

**降级策略**：
- 永远不降级到公开处理
- 只能降级为 Mock/规则
- 隐私能力不可降级

**审计元数据**（不记录输入/输出）：
- call_id、model_name、tokens、latency、status
- 记录哈希而非内容

#### 1.4 DATA_FLOW.md 中的信任边界

从 DATA_FLOW.md（第112-227行）提取：

**信任边界**：
```
API → Model Gateway → 外部供应商
```

**关键规则**：
- ✅ 不能直接接收未经授权的原始私密数据
- ✅ 敏感数据不路由到外部模型
- ✅ 隐私失败时关闭执行，不降级公开处理
- ✅ 降级策略不会绕过隐私限制

#### 1.5 THREAT_MODEL.md 中的威胁 T-04

从 THREAT_MODEL.md（第183-221行）提取：

**威胁 T-04**：模型 Prompt 注入
- **缓解措施**：
  - 最小化胶囊（minimal capsule）
  - Prompt 模板化
  - 输出验证
  - 从不路由敏感数据到外部

### 2. 关键设计决策

#### 2.1 privacy_context 字段定义

基于 ADR-004 和隐私基线，定义完整的 privacy_context 结构：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `purpose` | string | 是 | 调用目的（如 `meal_planning`、`agent_chat`） |
| `data_classification` | string | 是 | 数据分类：P0/P1/P2/P3/P4 |
| `retention` | string | 是 | 保留策略：session/permanent/none |
| `consent_scope` | string | 是 | 授权范围（如 `scene_instance:{id}`） |
| `allowed_outputs` | array | 是 | 允许的输出类型（TEXT/STRUCTURED/EMBEDDING） |
| `user_id` | uuid | 是 | 关联用户 ID |
| `scene_instance_id` | uuid | 否 | 关联场景实例 ID（可选） |

**扩展说明**：
- `data_classification`：P4 = 临时密钥需立即清理，P3 = 加密存储，P0 = 公开数据
- `retention`：session = 会话结束清理，permanent = 长期存储，none = 不存储
- `consent_scope`：明确用户授权范围，用于权限校验
- `allowed_outputs`：防止输出超出授权范围的数据类型

#### 2.2 超时规则

**默认超时**：30 秒
**可配置范围**：最大 300 秒（5 分钟）

**超时处理策略**：
1. 超时后降级到 Mock/规则（如果允许）
2. 否则返回超时错误
3. 审计日志记录超时事件

#### 2.3 结构化输出支持

**支持格式**：
- JSON Schema（推荐）
- 简单类型（TEXT/STRUCTURED/EMBEDDING）

**请求示例**：
```json
{
  "response_format": {
    "type": "json_schema",
    "schema": {
      "type": "object",
      "properties": {...}
    }
  }
}
```

#### 2.4 降级策略

**降级路径**：
```
本地节点 → Mock → 规则引擎
```

**不可降级情况**：
- ❌ 降级到公开/外部（隐私禁止）
- ❌ 绕过隐私检查
- ❌ 暴露 P3/P4 数据

**降级触发条件**：
1. 本地节点不可用 → Mock
2. Mock 失败 → 规则引擎
3. 所有路径失败 → 返回错误

#### 2.5 失败关闭行为

**原则**：隐私失败时关闭执行，不降级公开处理

**失败分类**：

| 失败类型 | 原因 | 处理策略 |
|---------|------|---------|
| 隐私校验失败 | 缺少 privacy_context、数据分类不符 | 立即拒绝，不执行 |
| 模型不可用 | 节点健康检查失败 | 降级到 Mock/规则 |
| 超时 | 超过 timeout 限制 | 降级或返回超时错误 |
| 输入验证失败 | 格式错误、参数超出范围 | 立即拒绝 |
| 内部错误 | 服务端错误 | 记录错误，返回内部错误 |
| 外部供应商错误 | 第三方 API 返回错误 | 如果允许外部，返回错误；否则降级 |

#### 2.6 审计元数据

**记录字段**（不记录输入/输出内容）：
| 字段 | 说明 |
|------|------|
| `request_id` | 请求 ID |
| `model` | 模型名 |
| `prompt_tokens` | Prompt Token 数 |
| `completion_tokens` | 完成 Token 数 |
| `latency_ms` | 延迟（毫秒） |
| `provider` | 提供商（local/external/mock/rule） |
| `status` | 状态（completed/failed/timeout） |
| `input_hash` | 输入哈希（验证完整性） |
| `output_hash` | 输出哈希（验证完整性） |

**保留策略**：
- 审计日志保留 90 天（ADR-005）
- 不记录原始 Prompt 和响应

#### 2.7 Health API 隐私约束

**约束规则**：
- ❌ 不返回密钥或 Token
- ❌ 不返回内部错误详情
- ❌ 不返回用户数据
- ❌ 不返回历史调用记录

**响应内容**：
- 模型状态（ready/unavailable/error）
- 延迟（latency_ms）
- 最后检查时间（last_checked）

### 3. 端点定义

#### 3.1 POST /internal/v1/model/chat

**端点编号**：EP-MODEL-058

**请求头**：
```
Authorization: Bearer <internal_service_token>
X-Service-Name: agent-service
```

**隐私校验规则**：
- `data_classification = P4` → 禁止路由到外部模型，必须本地或 Mock
- `data_classification = P3` → 禁止路由到外部模型，必须本地加密
- `retention = none` → 不存储输入/输出
- `consent_scope` 必须与用户授权一致

**请求体**：
```json
{
  "privacy_context": {
    "purpose": "meal_planning",
    "data_classification": "P4",
    "retention": "none",
    "consent_scope": "scene_instance:uuid",
    "allowed_outputs": ["STRUCTURED"],
    "user_id": "uuid",
    "scene_instance_id": "uuid"
  },
  "messages": [
    {
      "role": "user",
      "content": "..."
    }
  ],
  "model": "local-llama-7b",
  "temperature": 0.7,
  "max_tokens": 500,
  "response_format": {
    "type": "json_schema",
    "schema": {...}
  }
}
```

**响应**：
```json
{
  "request_id": "uuid",
  "model": "local-llama-7b",
  "status": "completed",
  "response": {
    "type": "STRUCTURED",
    "content": {...}
  },
  "metadata": {
    "prompt_tokens": 150,
    "completion_tokens": 80,
    "latency_ms": 1250,
    "provider": "local"
  }
}
```

**错误码**：
- `PRIVACY_CONTEXT_MISSING`
- `PRIVACY_CONTEXT_INVALID`
- `PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED`
- `MODEL_UNAVAILABLE`
- `MODEL_TIMEOUT`
- `MODEL_ROUTING_FAILED`
- `INVALID_INPUT`
- `INTERNAL_ERROR`
- `EXTERNAL_PROVIDER_ERROR`

#### 3.2 POST /internal/v1/model/embedding

**端点编号**：EP-MODEL-059

**请求头**：同 chat 端点

**隐私上下文**：同 chat 端点，但 `allowed_outputs` 必须包含 `["EMBEDDING"]`

**请求体**：
```json
{
  "privacy_context": {
    "purpose": "memory_retrieval",
    "data_classification": "P2",
    "retention": "permanent",
    "consent_scope": "memory:uuid",
    "allowed_outputs": ["EMBEDDING"],
    "user_id": "uuid"
  },
  "text": "用户的原始记忆文本...",
  "model": "local-embedding-model",
  "dimension": 768
}
```

**响应**：
```json
{
  "request_id": "uuid",
  "model": "local-embedding-model",
  "status": "completed",
  "embedding": [0.0123, -0.0456, ...],
  "dimension": 768,
  "metadata": {
    "input_tokens": 25,
    "latency_ms": 250,
    "provider": "local"
  }
}
```

**隐私约束**：
- ❌ 不记录原始文本（仅记录哈希）
- ✅ embedding 向量不可逆
- ❌ 不暴露 embedding 给用户

**错误码**：同 chat 端点

#### 3.3 GET /internal/v1/model/health

**端点编号**：EP-MODEL-060

**请求头**：
```
Authorization: Bearer <internal_service_token>
```

**响应**：
```json
{
  "status": "healthy",
  "models": [
    {
      "name": "local-llama-7b",
      "status": "ready",
      "latency_ms": 10,
      "last_checked": "2026-07-14T12:34:56Z"
    },
    {
      "name": "local-embedding-model",
      "status": "ready",
      "latency_ms": 5,
      "last_checked": "2026-07-14T12:34:56Z"
    }
  ],
  "timestamp": "2026-07-14T12:34:56Z"
}
```

**健康状态**：
- `healthy`：所有模型正常
- `degraded`：部分模型不可用
- `unhealthy`：所有模型不可用

**隐私约束**：
- ❌ 不返回密钥或 Token
- ❌ 不返回内部错误详情
- ❌ 不返回用户数据
- ❌ 不返回历史调用记录

**错误码**：
- `INTERNAL_ERROR`
- `SERVICE_UNAVAILABLE`

### 4. API_CONTRACT.md 修改记录

#### 4.1 插入位置

在 API_CONTRACT.md 中，于 Admin 章节（原 2.8）之前插入新的 Model Gateway 章节（2.8），Admin 章节改为 2.9。

**插入位置**：第2814行 "---" 之后，第2816行 "#### GET /api/v1/admin/nodes" 之前

**实际插入**：
- 从第2815行开始插入完整的 Model Gateway 章节
- 包含 3 个端点定义
- Admin 章节自动后移为 2.9

#### 4.2 添加的端点编号

- EP-MODEL-058：POST /internal/v1/model/chat
- EP-MODEL-059：POST /internal/v1/model/embedding
- EP-MODEL-060：GET /internal/v1/model/health

#### 4.3 章节结构

```markdown
### 2.8 Model Gateway（内部）

> **访问控制**：内部接口，仅服务间调用，不对外部用户开放
> **权限**：内部服务（Agent Service、Scene Service）通过服务间认证调用

**路由策略**（见 ADR-004）：
...

#### POST /internal/v1/model/chat
**端点编号**：EP-MODEL-058
...

#### POST /internal/v1/model/embedding
**端点编号**：EP-MODEL-059
...

#### GET /internal/v1/model/health
**端点编号**：EP-MODEL-060
...
```

### 5. P0_P1_REMEDIATION_PLAN.md 更新记录

#### 5.1 返工说明更新（第90-97行）

在"返工说明"部分添加：
```markdown
- ✅ R1-12 已完成补全，任务日志位于 `development-logs/in-progress/`，新增 3 个端点（EP-MODEL-058～060）
```

#### 5.2 任务状态更新（第107行）

将 R1-12 状态从 `[ ]` 改为 `[x]`：
```markdown
| [x] | R1-12 | 补全 Model Gateway | chat、embedding、health | `privacy_context`、超时、结构化输出和降级规则明确 |
```

#### 5.3 具体操作更新（第107行）

扩展"具体操作"字段：
```markdown
| [x] | R1-12 | 补全 Model Gateway | 新增 2.8 章节，3 个内部端点（EP-MODEL-058～060），定义隐私上下文结构、超时规则、降级策略、失败关闭行为和审计元数据 | `privacy_context` 包含 purpose/data_classification/retention/consent_scope/allowed_outputs；超时 30s 可配置；降级策略不绕过隐私；审计仅记录 call_id、model、tokens、latency、status、hash |
```

### 6. 验证检查

#### 6.1 端点编号唯一性检查

```bash
grep -E "EP-MODEL-[0-9]{3}" docs/api/API_CONTRACT.md | sort | uniq -c
```

**结果**：每个端点编号只出现一次 ✅

#### 6.2 章节编号连续性检查

- 2.7 Scene API ✅
- 2.8 Model Gateway ✅（新增）
- 2.9 Admin ✅（原 2.8 改为 2.9）

#### 6.3 隐私约束完整性检查

✅ 所有 3 个端点都包含隐私约束说明
✅ privacy_context 字段定义完整
✅ 降级策略明确（不降级公开）
✅ 审计元数据定义（不记录内容）
✅ Health API 隐私约束明确

#### 6.4 与权威文档一致性检查

✅ 与 ADR-004 路由策略一致
✅ 与 DATA_FLOW.md 信任边界一致
✅ 与 THREAT_MODEL.md T-04 缓解措施一致
✅ 与 PRIVACY_BASELINE.md 数据分类一致

#### 6.5 完成标准验证

✅ `privacy_context` 结构明确（7 个字段）
✅ 超时规则明确（30s 默认，最大 300s）
✅ 结构化输出支持明确（JSON Schema）
✅ 降级规则明确（Mock/规则，不公开）
✅ 失败关闭行为明确（隐私失败立即拒绝）

## 验收结果

### 验收检查清单

- [x] 所有 3 个内部端点（chat、embedding、health）已定义
- [x] privacy_context 结构包含所有必需字段（7 个）
- [x] 超时规则明确（默认 30s，最大 300s）
- [x] 结构化输出支持（JSON Schema）已定义
- [x] 降级策略明确（Mock/规则，不降级公开）
- [x] 失败关闭行为明确（隐私失败立即拒绝）
- [x] 审计元数据定义（仅记录 call_id、model、tokens、latency、status、hash）
- [x] 端点编号稳定唯一（EP-MODEL-058～060）
- [x] Health API 隐私约束明确
- [x] 与 ADR-004、DATA_FLOW.md、THREAT_MODEL.md 一致
- [x] P0_P1_REMEDIATION_PLAN.md 已更新

### 文档变更摘要

| 文档 | 变更类型 | 变更位置 | 说明 |
|------|---------|---------|------|
| docs/api/API_CONTRACT.md | 新增章节 | 2.8 Model Gateway | 完整定义 3 个内部端点 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-12 行 | [ ] → [x] |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明更新 | 第90-97行 | 添加 R1-12 完成说明 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 具体操作更新 | R1-12 具体操作列 | 扩展操作描述 |

### 下一步

R1-12 已完成，R1 批次剩余任务：
- R1-13：补全 Admin API
- R1-14～R1-17：统一路径变量、错误码、幂等规则、冻结文档

可继续执行 R1-13 或进入 R2 批次（前提：R1 全部完成）
