# HTTP API 契约

> **版本**：v1.0-frozen
> **冻结日期**：2026-07-14
> **状态**：已审计冻结，后续变更需 ADR
> **维护者**：开发团队

## 1. 基础约定

### 1.1 API 前缀

```
/api/v1
```

### 1.2 响应格式

**成功响应**：
```json
{
  "success": true,
  "data": {},
  "request_id": "req_xxx"
}
```

**失败响应**：
```json
{
  "success": false,
  "error": {
    "code": "MODULE_REASON",
    "message": "人类可读的错误信息",
    "details": {}
  },
  "request_id": "req_xxx"
}
```

### 1.3 通用请求规则

#### 1.3.1 分页

**请求参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:------:|--------|------|
| `page` | int | 否 | 1 | 页码（从 1 开始） |
| `page_size` | int | 否 | 20 | 每页数量 |

**限制**：
- `page_size` 最大值为 100（List 端点）或 20（Admin 端点）
- `page` 必须 ≥ 1
- `page` 超过总页数时返回空列表（`items: []`），而非 404

**响应**：
```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 100
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `items` | array | 当前页数据列表 |
| `page` | int | 当前页码 |
| `page_size` | int | 每页数量 |
| `total` | int | 总记录数 |

**错误码**：
- `INVALID_PAGINATION` - `page` 或 `page_size` 超出范围（`page < 1` 或 `page_size > max`）

**分页一致性**：
- ✅ 所有 List 端点使用相同字段名（`page`、`page_size`、`total`）
- ✅ 不使用 `offset`/`limit` 或 `cursor` 等其他分页方式（MVP 阶段）
- ❌ 不使用 `next_cursor` 或 `prev_cursor`（P2 阶段评估游标分页）

#### 1.3.2 排序

**请求参数**：
```
?sort=created_at&order=desc
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:------:|--------|------|
| `sort` | string | 否 | 端点定义 | 排序字段（如 `created_at`、`updated_at`、`name`） |
| `order` | string | 否 | desc | 排序方向：`asc` 或 `desc` |

**允许排序字段**：
- 每个 List 端点在文档中明确列出允许的 `sort` 字段
- 不允许排序的字段返回 `INVALID_SORT_FIELD` 错误（MVP 阶段简化为忽略非法字段，使用默认排序）

**默认排序**：
- 大多数端点默认按 `created_at desc`（最新优先）
- 目录树端点按 `name asc`（字母顺序）

#### 1.3.3 过滤

**请求参数**：
```
?status=active&type=DORM&q=搜索词
```

**过滤规则**：
- 精确匹配：`?status=active`、`?type=DORM`
- 范围匹配：`?start_time=2026-07-01&end_time=2026-07-31`
- 包含匹配：`?q=关键词`（搜索场景）
- 布尔过滤：`?include_private=false`

**过滤一致性**：
- ✅ 所有 List 端点的过滤参数使用相同语义（`status`、`type`、`q`）
- ✅ 时间范围使用 `start_time`/`end_time`（统一字段名）
- ✅ 布尔参数使用 `include_*` 前缀（如 `include_private`、`include_deleted`）

**错误码**：
- `INVALID_FILTER` - 过滤参数值无效（如 `status=INVALID_VALUE`）
- `DIRECTORY_QUERY_TOO_SHORT` - 搜索词过短（最少 2 字符）

#### 1.3.4 时间格式

**统一格式**：ISO 8601（RFC 3339）

**请求**：
```
?start_time=2026-07-14T10:00:00Z
?start_time=2026-07-14T10:00:00+08:00
?start_time=2026-07-14
```

**响应**：
```json
{
  "created_at": "2026-07-14T10:30:00Z",
  "updated_at": "2026-07-14T12:00:00+08:00",
  "expires_at": "2026-07-21T10:30:00Z"
}
```

**规则**：
- ✅ 所有时间字段使用 UTC（后缀 `Z`）或带时区偏移（`+08:00`）
- ✅ 日期-only 格式（`2026-07-14`）仅用于 `date` 字段（如场景公共上下文）
- ✅ 时间戳精度：秒级（`2026-07-14T10:30:00Z`），不使用毫秒
- ❌ 不使用 Unix 时间戳（`1721565000`）
- ❌ 不使用自定义格式（`2026/07/14 10:30:00`）

#### 1.3.5 ID 格式

**统一格式**：UUID v4（小写，带连字符）

**示例**：
```
uuid: "550e8400-e29b-41d4-a716-446655440000"
```

**规则**：
- ✅ 所有 ID 字段使用 UUID v4 格式
- ✅ ID 字段名统一为 `*_id`（如 `user_id`、`organization_id`、`scene_instance_id`）
- ✅ 响应中的 ID 字段使用与请求相同的名称
- ❌ 不使用自增整数 ID（`1`、`2`、`3`）
- ❌ 不使用短 ID（`abc123`）
- ❌ 不使用大写下划线 ID（`USER_ID`）——仅错误码使用

#### 1.3.6 空值规则

**统一规则**：

| 场景 | 请求 | 响应 |
|------|------|------|
| 可选字段未提供 | 省略字段（不发送 `null`） | 返回 `null` |
| 可选字段明确设置为空 | 发送 `null` | 返回 `null` |
| 必填字段为空 | 返回 `INVALID_INPUT`（400） | - |
| 数组为空 | 发送 `[]` | 返回 `[]` |
| 对象为空 | 发送 `{}` | 返回 `{}` |

**示例**：
```json
// 请求：省略可选字段
{
  "scene_key": "meal_planning",
  "participant_user_ids": ["uuid1", "uuid2"]
}

// 响应：未提供的字段返回 null
{
  "conversation_id": null,
  "public_context": {}
}

// 请求：明确设置为 null
{
  "conversation_id": null,
  "public_context": null
}
```

**规则**：
- ✅ 请求中省略可选字段 = 不修改该字段（PATCH）或使用默认值（POST）
- ✅ 响应中 `null` 表示该字段存在但值为空
- ✅ 响应中省略字段表示该字段不适用于当前上下文（仅列表响应）
- ❌ 不使用空字符串 `""` 代替 `null`（除 `display_name` 等明确允许的字段）

#### 1.3.7 布尔值格式

**统一规则**：
- ✅ 使用 JSON `true`/`false`
- ✅ 字段名使用肯定形式（`enabled`、`visible`、`send_invitation`）
- ❌ 不使用 `"Y"`/`"N"`、`"1"`/`"0"`、`"on"`/`"off"`

#### 1.3.8 枚举值格式

**统一规则**：
- ✅ 枚举值使用大写蛇形命名（`PUBLIC`、`INTERNAL`、`PRIVATE`、`STUDENT`、`DORM`）
- ✅ 枚举值在文档中明确列出可选值
- ✅ 无效枚举值返回 `INVALID_INPUT`（400）

**示例**：
```json
{
  "privacy_level": "INTERNAL",  // ✅ 正确
  "type": "DORM",               // ✅ 正确
  "status": "active"            // ❌ 错误（应为 ACTIVE）
}
```

### 1.4 幂等规则

#### 1.4.1 幂等性概述

幂等性保证：使用相同 `Idempotency-Key` 的多次请求，服务端只执行一次，返回相同结果。

**适用场景**：
- 网络超时后客户端重试
- 前端重复提交保护
- 第三方回调重试

#### 1.4.2 必须支持幂等性的端点

以下端点**必须**支持 `Idempotency-Key`：

| 端点 | 方法 | 幂等原因 |
|------|------|---------|
| POST /api/v1/auth/register | POST | 防止重复注册 |
| POST /api/v1/organizations | POST | 防止重复创建组织 |
| POST /api/v1/organizations/{organization_id}/members | POST | 防止重复添加成员 |
| POST /api/v1/organizations/{organization_id}/join | POST | 防止重复加入 |
| POST /api/v1/conversations | POST | 防止重复创建会话 |
| POST /api/v1/conversations/{conversation_id}/participants | POST | 防止重复添加参与者 |
| POST /api/v1/scene-instances | POST | 防止重复创建场景 |
| POST /api/v1/scene-instances/{scene_instance_id}/participants | POST | 防止重复添加参与者 |
| POST /api/v1/scene-instances/{scene_instance_id}/private-submission | POST | 防止重复提交偏好 |
| POST /api/v1/scene-instances/{scene_instance_id}/consent | POST | 防止重复授权 |
| POST /api/v1/scene-instances/{scene_instance_id}/vote | POST | 防止重复投票 |
| POST /api/v1/scene-instances/{scene_instance_id}/confirm | POST | 防止重复确认 |
| POST /api/v1/scene-instances/{scene_instance_id}/cancel | POST | 防止重复取消 |
| POST /api/v1/scene-instances/{scene_instance_id}/start | POST | 防止重复启动 |
| POST /api/v1/memories | POST | 防止重复创建记忆 |
| POST /api/v1/admin/nodes | POST | 防止重复创建节点 |
| POST /api/v1/admin/models | POST | 防止重复创建模型 |
| POST /api/v1/admin/deployments | POST | 防止重复创建部署 |

以下端点**可选**支持 `Idempotency-Key`（MVP 阶段建议支持）：

| 端点 | 方法 | 说明 |
|------|------|------|
| POST /api/v1/messages | POST | 防止重复发送消息（MVP 建议支持） |
| POST /api/v1/memories/export | POST | 防止重复导出（MVP 建议支持） |
| POST /api/v1/agents/me/chat | POST | 防止重复对话（MVP 建议支持） |

以下端点**不适用**幂等性：

| 端点 | 方法 | 原因 |
|------|------|------|
| PATCH /api/v1/users/{user_id} | PATCH | 更新操作，每次执行结果不同 |
| PATCH /api/v1/organizations/{organization_id} | PATCH | 更新操作，每次执行结果不同 |
| PATCH /api/v1/agents/me | PATCH | 更新操作，每次执行结果不同 |
| PATCH /api/v1/memories/{memory_id} | PATCH | 更新操作，每次执行结果不同 |
| PATCH /api/v1/admin/nodes/{node_id} | PATCH | 更新操作，使用 If-Match 乐观锁 |
| DELETE /api/v1/organizations/{organization_id} | DELETE | 删除操作，第二次删除返回 404 |
| DELETE /api/v1/messages/{message_id} | DELETE | 删除操作，第二次删除返回 404 |
| DELETE /api/v1/admin/nodes/{node_id} | DELETE | 删除操作，第二次删除返回 404 |

#### 1.4.3 Idempotency-Key 格式

**请求头**：
```
Idempotency-Key: <uuid>
```

**规则**：
- ✅ 格式：UUID v4（小写，带连字符）
- ✅ 长度：36 字符（`550e8400-e29b-41d4-a716-446655440000`）
- ✅ 客户端生成，服务端不生成
- ✅ 客户端应缓存已使用的 Key，避免复用不同请求的 Key
- ❌ 不使用空字符串或默认值

**生成建议**：
```javascript
// 推荐：使用 UUID v4
crypto.randomUUID()

// 备选：使用时间戳 + 随机数
`${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
```

#### 1.4.4 作用域

**幂等记录唯一键**：

```
composite_key = actor_id + HTTP_method + request_path + request_body_hash + Idempotency-Key
```

**三条硬规则**：

| 场景 | 处理方式 | 响应 |
|------|---------|------|
| 相同 actor + method + path + body_hash + key | 返回首次缓存结果 | 200/201（与首次相同） |
| 相同 actor + method + path + key，但 body_hash 不同 | 视为冲突 | 409 `IDEMPOTENCY_CONFLICT` |
| 不同 actor 使用相同 key | 视为新请求（不复用他人记录） | 正常执行 |

**说明**：
- ✅ `actor_id`：发起请求的用户或服务账号 ID，确保不同用户不互相干扰
- ✅ `request_path`：完整路径（含路径变量，如 `/api/v1/organizations/{organization_id}/members`）
- ✅ `request_body_hash`：请求体 JSON 的 SHA-256 哈希（忽略字段顺序），确保参数变更可检测
- ✅ `Idempotency-Key`：客户端提供的 UUID v4
- ✅ 同一 actor 对同一端点发送相同 body + 相同 key → 幂等（返回缓存结果）
- ✅ 同一 actor 对同一端点发送不同 body + 相同 key → 冲突（返回 409）
- ❌ 不同 actor 即使使用相同 key → 也视为独立请求（不共享幂等记录）
- ❌ 不以 key 单独作为唯一键（必须结合 actor + path + body_hash）

#### 1.4.5 过期时间

**默认过期时间**：24 小时

**规则**：
- ✅ `Idempotency-Key` 在创建后 24 小时内有效
- ✅ 超过 24 小时的 Key 被视为新请求（返回 201/200，重新执行）
- ✅ Key 在使用后保留 24 小时（用于重复请求返回缓存结果）
- ✅ 24 小时后自动清理

**清理策略**：
- 后台任务每小时清理过期的 Key
- 内存存储（MVP）：服务重启后 Key 丢失，但业务逻辑保证安全
- 数据库存储（P2）：Key 持久化，支持跨服务实例

#### 1.4.6 重复请求响应

**首次请求**：
1. 服务端接收请求，检查 `Idempotency-Key` 是否存在
2. 不存在：执行请求，存储结果，返回 201/200
3. 存在且未完成：返回 409 `IDEMPOTENCY_CONFLICT`（请求正在进行中）
4. 存在且已完成：返回缓存的结果（相同状态码和响应体）

**重复请求响应格式**：
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "created"
  },
  "request_id": "req_xxx",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
}
```

**规则**：
- ✅ 重复请求返回与首次请求**完全相同**的响应体（包括 `request_id`）
- ✅ 重复请求不触发事件发布（如 `UserRegistered`）
- ✅ 重复请求不产生新的审计日志（仅记录首次请求）
- ❌ 不返回 `"duplicate": true` 标志（客户端不应感知差异）

#### 1.4.7 冲突处理

**冲突场景**：

| 场景 | 处理方式 | 错误码 |
|------|---------|--------|
| 相同 Key，相同参数，请求正在进行中 | 返回 409，提示稍后重试 | `IDEMPOTENCY_CONFLICT` |
| 相同 Key，不同参数 | 返回 409，Key 已被使用 | `IDEMPOTENCY_CONFLICT` |
| 相同 Key，超过 24 小时 | 视为新请求，重新执行 | - |
| 未提供 Key（必须支持的端点） | 返回 400，要求提供 Key | `IDEMPOTENCY_KEY_REQUIRED` |

**冲突响应示例**：
```json
{
  "success": false,
  "error": {
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "请求正在进行中，请稍后重试",
    "details": {
      "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2026-07-14T10:30:00Z"
    },
    "request_id": "req_xxx",
    "retryable": true
  }
}
```

**重试策略**：
- 客户端收到 `IDEMPOTENCY_CONFLICT` 后，等待 1 秒后重试
- 最多重试 3 次
- 超过 3 次后返回错误给用户

#### 1.4.8 幂等性与业务冲突的关系

**业务冲突错误码**（如 `CONVERSATION_PARTICIPANT_ALREADY_EXISTS`）与幂等性冲突的区别：

| 场景 | 错误码 | 说明 |
|------|--------|------|
| 首次请求，参与者已存在 | `CONVERSATION_PARTICIPANT_ALREADY_EXISTS` | 业务逻辑冲突 |
| 重复请求（相同 Key），参与者已存在 | 返回缓存的成功响应 | 幂等性保证 |
| 首次请求，未提供 Key | `IDEMPOTENCY_KEY_REQUIRED` | 缺少幂等键 |

**规则**：
- ✅ 幂等性优先于业务冲突检查
- ✅ 如果请求有 `Idempotency-Key`，服务端先检查 Key 是否存在
- ✅ Key 存在且已完成：直接返回缓存结果，不检查业务冲突
- ✅ Key 不存在：执行业务逻辑，存储结果

### 1.5 鉴权

#### 1.5.1 Web 浏览器端（主认证方式）

**方案**：JWT + HttpOnly Secure SameSite Cookie

- Access Token 和 Refresh Token 均存储在 HttpOnly Secure SameSite Cookie 中
- 浏览器自动携带 Cookie，前端代码无法读取（防 XSS）
- 前端不得将 access_token 存入 `localStorage`、`sessionStorage` 或任何可读存储

**请求头**（浏览器端）：

```
Cookie: access_token=<jwt>; refresh_token=<jwt>
```

**登录/注册成功后**，服务端通过 `Set-Cookie` 响应头发放 Cookie。

#### 1.5.2 非浏览器内部调用（辅助认证方式）

**方案**：Bearer Token（仅限内部服务）

- `Authorization: Bearer <internal_service_token>`
- 仅用于服务间调用（如 Agent Service → Model Gateway）
- 不得用于普通 Web 用户认证
- Token 通过服务发现或密钥管理系统分发

**适用端点**：
- `POST /internal/v1/model/chat`
- `POST /internal/v1/model/embedding`
- `GET /internal/v1/model/health`

**管理后台**：
- `Authorization: Bearer <admin_token>`
- 仅限管理后台调用
- Token 通过管理员登录流程获取

#### 1.5.3 认证流程

```
登录 → 验证凭据 → 颁发 Access + Refresh Token
→ Set-Cookie: access_token（HttpOnly, Secure, SameSite=Lax）
→ Set-Cookie: refresh_token（HttpOnly, Secure, SameSite=Lax）
→ 后续请求自动携带 Cookie
→ 服务端验证 Cookie 中的 access_token
→ 过期后使用 refresh_token 轮换
→ 刷新过期后跳转登录
```

#### 1.5.4 参考

- ADR-003：采用 JWT + HttpOnly Cookie 方案
- R1-19：CSRF 防护方案（Cookie 写请求需 CSRF Token）
- R1-20：修正登录响应（不再返回 access_token/refresh_token 到响应体）

#### 1.5.5 Cookie 属性详细定义

**access_token Cookie**：

| 属性 | 值 | 说明 |
|------|-----|------|
| `HttpOnly` | true | 禁止 JavaScript 访问（防 XSS 窃取） |
| `Secure` | true | 仅 HTTPS 传输（生产环境强制） |
| `SameSite` | Lax | 跨站请求不携带 Cookie（防止 CSRF）；同站导航（如点击链接）携带 |
| `Path` | `/api/v1` | 仅对 `/api/v1/*` 路径发送 |
| `Max-Age` | 3600 | 有效期 1 小时 |
| `Domain` | 配置项 | 根据部署环境设置（如 `.campus-agent.example.edu`） |

**refresh_token Cookie**：

| 属性 | 值 | 说明 |
|------|-----|------|
| `HttpOnly` | true | 禁止 JavaScript 访问 |
| `Secure` | true | 仅 HTTPS 传输 |
| `SameSite` | Lax | 同 access_token |
| `Path` | `/api/v1/auth` | 仅对 `/api/v1/auth/*` 路径发送（限制暴露面） |
| `Max-Age` | 604800 | 有效期 7 天 |
| `Domain` | 配置项 | 同 access_token |

**SameSite=Lax 选择理由**：
- 浏览器从外部链接点击进入站点时（如从学校官网点击 CampusAgent 链接），`access_token` Cookie 会被发送，用户保持登录状态
- 跨站 POST 请求（如恶意网站的 `<form>` 提交）不携带 Cookie，防止 CSRF
- 如果需要更严格的安全策略，可改为 `SameSite=Strict`（但会影响从外部链接进入时的登录状态保持）

**开发环境例外**：
- 开发环境（`APP_ENV=development`）允许 `Secure=false`（HTTP 本地开发）
- 生产环境必须 `Secure=true`（强制 HTTPS）

**Cookie 清理**：
- 注销时：`Max-Age=0`，立即过期
- 刷新失败时：保留旧 access_token 直到过期（不主动清除）

#### 1.5.6 CSRF 防护方案

> 本节依据 ADR-003 和 [R1-18 浏览器认证统一方案](development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md) 定义 CSRF 防护机制。

**背景**：
- 浏览器端主认证方式为 HttpOnly Cookie（Section 1.5.1）
- Cookie 在浏览器同站请求中自动携带（`SameSite=Lax`）
- **已认证的**浏览器写操作（POST/PATCH/PUT/DELETE）需要额外 CSRF 防护层
- 未认证端点（login、register）不持有 csrf_token，豁免 CSRF 校验

##### 1.5.6.1 CSRF Token 来源

**Double-Submit Cookie 模式**：

| 组件 | 名称 | HttpOnly | 说明 |
|------|------|:--------:|------|
| CSRF Token Cookie | `csrf_token` | **false** | 非 HttpOnly，允许 JavaScript 读取 |
| 请求头 | `X-CSRF-Token` | - | 客户端将 Cookie 值原样放入请求头 |

**流程**：
1. 用户登录成功后，服务端设置 `csrf_token` Cookie（非 HttpOnly）
2. 前端读取 `csrf_token` Cookie 值（通过 `document.cookie` 或辅助函数）
3. 每次浏览器发送写请求（POST/PATCH/PUT/DELETE）时，在 `X-CSRF-Token` 请求头中携带 `csrf_token` 的值
4. 服务端校验：`X-CSRF-Token` 请求头值 = `csrf_token` Cookie 值
5. 校验失败：返回 HTTP 403 + 对应错误码

**前端伪代码**：

```javascript
// 读取 CSRF Token
function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/)
  return match ? match[1] : null
}

// 发起写请求
async function postData(url, data) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': getCsrfToken(),
    },
    credentials: 'include',
    body: JSON.stringify(data),
  })
  return response
}
```

**后端校验伪代码**：

```python
def validate_csrf(request):
    # 跳过非浏览器请求（已通过 Bearer 认证）
    if request.auth and request.auth.type == "bearer":
        return True

    # 跳过未认证端点（login/register），此时客户端尚无 csrf_token Cookie
    if request.path in ("/api/v1/auth/login", "/api/v1/auth/register"):
        return True

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")

    if not csrf_cookie or not csrf_header:
        raise CSRF_TOKEN_MISSING()

    if csrf_cookie != csrf_header:
        raise CSRF_TOKEN_MISMATCH()

    # Token 有效期检查（可选增强，不进入 MVP）
    # if is_csrf_token_expired(csrf_cookie):
    #     raise CSRF_TOKEN_EXPIRED()

    return True
```

##### 1.5.6.2 强制 CSRF 校验的请求

以下请求**必须**包含有效的 `X-CSRF-Token` 请求头：

| HTTP 方法 | 范围 | 说明 |
|-----------|------|------|
| `POST` | Cookie 已认证的浏览器端 POST | 创建资源、执行操作（login/register 除外） |
| `PATCH` | Cookie 已认证的浏览器端 PATCH | 更新资源 |
| `PUT` | Cookie 已认证的浏览器端 PUT | 替换资源（MVP 未使用，预留） |
| `DELETE` | Cookie 已认证的浏览器端 DELETE | 删除资源 |

**判断规则**：
- 请求通过 Cookie 认证（非 Bearer）且非 login/register 端点 → 必须校验 CSRF
- 请求通过 Bearer 认证（内部服务）→ 跳过 CSRF 校验
- 请求为 GET/HEAD/OPTIONS → 跳过 CSRF 校验（只读操作）
- 请求为未认证端点（`POST /api/v1/auth/login`、`POST /api/v1/auth/register`）→ 跳过 CSRF 校验（此时客户端尚无 csrf_token Cookie）

**CSRF Bootstrap 流程**：
1. 用户访问站点（未认证）
2. 用户提交登录/注册表单（无需 CSRF Token，因为尚未持有 csrf_token Cookie）
3. 服务端验证凭据后，通过 `Set-Cookie` 响应头发放 `access_token`、`refresh_token`、`csrf_token`
4. 前端从响应中获取 `csrf_token` Cookie（非 HttpOnly，可读取）
5. 后续所有写请求携带 `X-CSRF-Token` 请求头

##### 1.5.6.3 CSRF 豁免请求

以下请求**豁免** CSRF 校验：

| 请求类型 | 豁免原因 |
|----------|---------|
| `GET`、`HEAD`、`OPTIONS` | 只读操作，不改变服务端状态 |
| `POST /api/v1/auth/login` | 未认证登录请求，客户端尚无 csrf_token Cookie |
| `POST /api/v1/auth/register` | 未认证注册请求，客户端尚无 csrf_token Cookie |
| Bearer Token 认证的请求 | 内部服务间调用（`internal_service_token`）及管理后台（`admin_token`），不通过 Cookie 认证 |
| WebSocket 握手（GET /ws/v1） | WebSocket 使用一次性 ticket，非 Cookie 认证 |
| 静态资源请求（`/static/*`、`/favicon.ico`） | 不涉及 API 认证 |

**CSRF Bootstrap 流程说明**：
- login/register 是 CSRF 防护的 bootstrap 端点
- 登录/注册成功后，服务端通过 `Set-Cookie` 发放 `csrf_token`
- 前端从 Cookie 中读取 `csrf_token`，用于后续写请求的 `X-CSRF-Token` 请求头
- 此流程不要求 login/register 本身携带 CSRF Token（Chicken-and-Egg 问题）

**WebSocket 握手特别说明**：
- 当前：`GET /ws/v1?ticket=<one_time_ticket>`（R1-22 将改为 Cookie）
- WebSocket 握手通过 ticket 认证，不使用 Cookie
- SameSite=Lax 已阻止跨站 WebSocket 连接携带 Cookie
- 豁免 CSRF 校验，但保留 ticket 过期检查（待 R1-23 实现）

##### 1.5.6.4 CSRF 校验失败响应

当 CSRF 校验失败时，返回 HTTP 403 和以下错误码之一：

| 场景 | HTTP 状态码 | 错误码 | message |
|------|:----------:|--------|---------|
| 缺少 `X-CSRF-Token` 请求头（写请求） | 403 | `CSRF_TOKEN_MISSING` | 缺少 CSRF Token，请刷新页面后重试 |
| `X-CSRF-Token` 与 `csrf_token` Cookie 值不匹配 | 403 | `CSRF_TOKEN_MISMATCH` | CSRF Token 不匹配，请刷新页面后重试 |
| `csrf_token` Cookie 已过期（可选增强，P2 实现） | 403 | `CSRF_TOKEN_EXPIRED` | CSRF Token 已过期，请重新登录 |

**响应格式**：

```json
{
  "error": {
    "code": "CSRF_TOKEN_MISSING",
    "message": "缺少 CSRF Token，请刷新页面后重试",
    "details": {},
    "request_id": "abc-123-def",
    "retryable": false
  }
}
```

**前端处理**：
- `CSRF_TOKEN_MISSING` / `CSRF_TOKEN_MISMATCH`：页面刷新（Token 已失效）
- `CSRF_TOKEN_EXPIRED`：跳转到登录页（重新登录刷新 Token）

##### 1.5.6.5 CSRF Token 生命周期

| 事件 | CSRF Token 行为 |
|------|----------------|
| 用户注册（POST /api/v1/auth/register） | 生成新的 `csrf_token` Cookie（注册成功后自动登录） |
| 用户登录（POST /api/v1/auth/login） | 生成新的 `csrf_token` Cookie |
| Token 刷新（POST /api/v1/auth/refresh） | 保持 `csrf_token` 不变（或选择刷新） |
| 用户注销（POST /api/v1/auth/logout） | 清除 `csrf_token` Cookie（Max-Age=0） |
| Token 过期（access_token 过期） | `csrf_token` 保留但失效（前端应跳转登录） |

**CSRF Bootstrap 流程**：
- login/register 是未认证端点，不持有 csrf_token Cookie
- 登录/注册成功后，服务端通过 `Set-Cookie` 一次性发放 `access_token`、`refresh_token`、`csrf_token`
- 前端从 Cookie 中读取 `csrf_token`（非 HttpOnly），用于后续写请求的 `X-CSRF-Token` 请求头
- 此流程解决了 Chicken-and-Egg 问题：首次请求无需 CSRF，后续请求需要 CSRF

**开发环境**：
- 开发环境允许 `Secure=false`（HTTP）
- CSRF 防护在开发环境同样生效（不豁免）
- `csrf_token` 有效期在开发环境可适当缩短（如 1 小时），方便测试

##### 1.5.6.6 参考

- ADR-003：认证方式决策
- [R1-18 浏览器认证统一方案](development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md)
- [R1-22 WebSocket 鉴权修正](docs/project/P0_P1_REMEDIATION_PLAN.md)（WebSocket Cookie 迁移）

### 1.6 错误码体系

#### 1.6.1 统一错误响应结构

所有错误响应使用统一结构：

```json
{
  "success": false,
  "error": {
    "code": "MODULE_REASON",
    "message": "人类可读的错误信息",
    "details": {},
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | string | 稳定错误码，格式 `MODULE_REASON`，客户端据此分支 |
| `message` | string | 人类可读的错误描述，用于前端展示和调试 |
| `details` | object | 附加信息（如过期时间、允许的值列表、冲突字段等），可为空对象 `{}` |
| `request_id` | string | 请求追踪 ID，用于日志关联和客服排查 |
| `retryable` | bool | 是否可重试：`true` 表示客户端可安全重试（如超时、限流），`false` 表示重试无意义（如参数错误、权限拒绝） |

**隐私约束**：
- ❌ 错误响应**不得**泄露其他用户的数据
- ❌ 错误响应**不得**泄露系统内部结构（数据库列名、文件路径、堆栈跟踪）
- ❌ 认证失败时**不得**区分"用户不存在"和"密码错误"（防止账号枚举）
- ✅ 错误码本身可暴露（客户端需要据此分支），但 `details` 必须脱敏
- ✅ 隐私失败（`privacy_violation`）必须有独立错误码，不得混入 `validation_error`

#### 1.6.2 错误分类与 HTTP 状态码映射

| 分类 | 前缀 | HTTP 状态码 | 说明 |
|------|------|:----------:|------|
| **authentication** | `AUTH_*` | 401 | 未认证或凭证无效 |
| **authorization** | `*_PERMISSION_DENIED`、`*_NOT_PARTICIPANT`、`*_CONSENT_REQUIRED`、`*_CONSENT_EXPIRED`、`*_PERMISSION_EXPIRED` | 403 | 已认证但无权限 |
| **privacy_violation** | `PRIVACY_*`、`*_CONTENT_ENCRYPTED`、`*_SUBMISSION_ENCRYPTION_FAILED` | 403 | 隐私保护阻止操作 |
| **validation_error** | `*_INVALID_*`、`*_TOO_SHORT`、`*_TOO_LARGE`、`*_MISSING` | 400 | 请求格式或参数错误 |
| **not_found** | `*_NOT_FOUND` | 404 | 资源不存在 |
| **conflict** | `*_ALREADY_EXISTS`、`*_ALREADY_*`、`*_IN_USE`、`*_CANNOT_LEAVE`、`*_LIMIT_REACHED`、`*_CAPACITY_EXCEEDED`、`PRECONDITION_FAILED` | 409 | 资源状态冲突 |
| **state_transition_error** | `*_INVALID_STATE`、`*_INVALID_STAGE`、`*_PENDING_*`、`*_NOT_READY` | 422 | 当前状态不允许该操作 |
| **idempotency_conflict** | `IDEMPOTENCY_CONFLICT`（跨模块通用码，不分模块前缀）、`IDEMPOTENCY_KEY_REQUIRED` | 409/400 | Idempotency-Key 冲突或缺失（跨所有模块，不分前缀） |
| **csrf** | `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH`、`CSRF_TOKEN_EXPIRED` | 403 | CSRF Token 缺失、不匹配或过期 |
| **rate_limit** | `*_RATE_LIMITED` | 429 | 请求频率超限 |
| **model_gateway_error** | `MODEL_*`、`PRIVACY_CONTEXT_*` | 502/503 | 模型网关错误 |
| **internal_error** | `INTERNAL_ERROR` | 500 | 服务端未预期错误 |

#### 1.6.3 错误码总表

以下为全量错误码清单，按分类排列。

**认证（AUTH）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `AUTH_INVALID_TOKEN` | 401 | 访问令牌无效或已过期 | false | Auth |
| `AUTH_REFRESH_TOKEN_REVOKED` | 401 | Refresh Token 已被撤销（包括重放检测触发撤销） | false | Auth |
| `AUTH_REFRESH_TOKEN_EXPIRED` | 401 | Refresh Token 已过期 | false | Auth |
| `AUTH_ACCOUNT_DISABLED` | 401 | 账号已被禁用 | false | Auth |
| `AUTH_EMAIL_NOT_VERIFIED` | 401 | 邮箱未验证 | false | Auth |
| `AUTH_WEAK_PASSWORD` | 400 | 密码强度不足 | false | Auth |
| `AUTH_INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 | false | Auth |
| `USER_ALREADY_EXISTS` | 409 | 邮箱或学号已被注册 | false | Auth / User |

**CSRF**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `CSRF_TOKEN_MISSING` | 403 | 缺少 CSRF Token | false | 通用 |
| `CSRF_TOKEN_MISMATCH` | 403 | CSRF Token 不匹配 | false | 通用 |
| `CSRF_TOKEN_EXPIRED` | 403 | CSRF Token 已过期 | false | 通用 |

**授权（Authorization）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `USER_NOT_FOUND` | 404 | 用户不存在 | false | User |
| `USER_PERMISSION_DENIED` | 403 | 无权限操作此用户 | false | User |
| `ORG_PERMISSION_DENIED` | 403 | 无权限操作此组织 | false | Organization |
| `ORG_NOT_FOUND` | 404 | 组织不存在 | false | Organization |
| `ORG_MEMBER_ALREADY_EXISTS` | 409 | 用户已是组织成员 | false | Organization |
| `ORG_LAST_OWNER_CANNOT_LEAVE` | 409 | 最后一个所有者不能退出组织 | false | Organization |
| `ORG_INVALID_JOIN_POLICY` | 400 | 当前加入策略不允许 | false | Organization |
| `ORG_CAPACITY_EXCEEDED` | 409 | 组织成员数已达上限 | false | Organization |
| `CONVERSATION_NOT_FOUND` | 404 | 会话不存在 | false | Conversation |
| `CONVERSATION_PERMISSION_DENIED` | 403 | 无权限操作此会话 | false | Conversation |
| `CONVERSATION_NOT_PARTICIPANT` | 403 | 非会话参与者 | false | Conversation |
| `CONVERSATION_PARTICIPANT_NOT_FOUND` | 404 | 参与者不存在 | false | Conversation |
| `CONVERSATION_PARTICIPANT_ALREADY_EXISTS` | 409 | 参与者已存在 | false | Conversation |
| `CONVERSATION_LAST_OWNER_CANNOT_LEAVE` | 409 | 最后一个所有者不能退出 | false | Conversation |
| `CONVERSATION_AGENT_NOT_FOUND` | 404 | 智能体不存在 | false | Conversation |
| `CONVERSATION_USER_NOT_FOUND` | 404 | 用户不存在 | false | Conversation |
| `CONVERSATION_INVALID_PRIVACY_LEVEL` | 400 | 无效的隐私级别 | false | Conversation |
| `MESSAGE_NOT_FOUND` | 404 | 消息不存在 | false | Conversation |
| `MESSAGE_PERMISSION_DENIED` | 403 | 无权限操作此消息 | false | Conversation |
| `AGENT_NOT_FOUND` | 404 | 智能体不存在 | false | Agent |
| `AGENT_PERMISSION_DENIED` | 403 | 无权限操作此智能体 | false | Agent |
| `AGENT_PERMISSION_EXPIRED` | 403 | 智能体授权已过期 | false | Agent |
| `AGENT_INVALID_AUTONOMY_LEVEL` | 403 | 授权等级不足，无法执行此操作 | false | Agent |
| `AGENT_CHAT_DISABLED` | 403 | Agent 聊天功能已禁用 | false | Agent |
| `AGENT_SCENE_NOT_FOUND` | 404 | 关联场景不存在 | false | Agent |
| `AGENT_RUN_INVALID_STATUS` | 400 | 无效的状态过滤值 | false | Agent |
| `MEMORY_NOT_FOUND` | 404 | 记忆不存在 | false | Memory |
| `MEMORY_PERMISSION_DENIED` | 403 | 无权限操作此记忆 | false | Memory |
| `MEMORY_ACCESS_DENIED` | 403 | 无权限查看访问记录 | false | Memory |
| `MEMORY_ACCESS_INVALID_FILTER` | 400 | 无效的过滤参数 | false | Memory |
| `MEMORY_IN_USE` | 409 | 记忆正在被场景使用，需先结束场景 | false | Memory |
| `SCENE_NOT_FOUND` | 404 | 场景定义不存在 | false | Scene |
| `SCENE_INSTANCE_NOT_FOUND` | 404 | 场景实例不存在 | false | Scene |
| `SCENE_INSTANCE_PERMISSION_DENIED` | 403 | 无权限操作此场景实例 | false | Scene |
| `SCENE_INSTANCE_NOT_PARTICIPANT` | 403 | 非场景参与者 | false | Scene |
| `SCENE_INSTANCE_PARTICIPANT_NOT_FOUND` | 404 | 场景参与者不存在 | false | Scene |
| `ADMIN_PERMISSION_DENIED` | 403 | 管理员权限不足 | false | Admin |
| `NODE_NOT_FOUND` | 404 | 边缘节点不存在 | false | Admin |
| `MODEL_NOT_FOUND` | 404 | 模型配置不存在 | false | Admin |

**隐私违规（Privacy Violation）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `PRIVACY_CONTEXT_MISSING` | 403 | 缺少隐私上下文（privacy_context），请求被拒绝 | false | Model Gateway |
| `PRIVACY_CONTEXT_INVALID` | 403 | 隐私上下文字段无效或数据分类不符 | false | Model Gateway |
| `PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED` | 403 | 敏感数据（P3/P4）禁止路由到外部模型 | false | Model Gateway |
| `PRIVACY_CONSENT_REVOKED` | 403 | 隐私授权已被撤销，操作被拒绝 | false | Scene / Agent |
| `MEMORY_CONTENT_ENCRYPTED` | 403 | 记忆内容已加密，需要特殊权限才能访问 | false | Memory |
| `SCENE_INSTANCE_SUBMISSION_ENCRYPTION_FAILED` | 500 | 私有偏好加密失败，为保护隐私拒绝执行 | false | Scene |

**参数验证（Validation Error）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `INVALID_INPUT` | 400 | 请求参数格式错误或超出范围 | false | 通用 |
| `INVALID_PAGINATION` | 400 | 分页参数无效 | false | Admin / Memory |
| `INVALID_TIME_RANGE` | 400 | 时间范围无效 | false | Admin |
| `INVALID_ENDPOINT` | 400 | 端点格式无效 | false | Admin |
| `INVALID_CAPABILITIES` | 400 | 能力列表无效 | false | Admin |
| `INVALID_MODEL_CONFIG` | 400 | 模型配置无效 | false | Admin |
| `MESSAGE_INVALID_SENDER_TYPE` | 400 | 无效的发送者类型过滤值 | false | Conversation |
| `DIRECTORY_QUERY_TOO_SHORT` | 400 | 搜索词过短（最少 2 字符） | false | Directory |
| `DIRECTORY_INVALID_TYPE` | 400 | 无效的搜索类型 | false | Directory |
| `DIRECTORY_TREE_TOO_DEEP` | 400 | 组织树深度超过限制（最多 10 层） | false | Directory |
| `DIRECTORY_ORG_NOT_FOUND` | 404 | 组织不存在或无权访问 | false | Directory |
| `SCENE_LIST_INVALID_TYPE` | 400 | 无效的场景类型过滤值 | false | Scene |
| `SCENE_INSTANCE_CREATE_INVALID_SCENE_KEY` | 400 | 无效的场景标识符 | false | Scene |
| `SCENE_INSTANCE_CREATE_NO_PARTICIPANTS` | 400 | 至少需要 1 名参与者 | false | Scene |
| `SCENE_INSTANCE_CREATE_CONVERSATION_NOT_FOUND` | 404 | 关联会话不存在 | false | Scene |
| `MEMORY_INVALID_FIELD` | 400 | 试图更新不可变字段 | false | Memory |
| `MEMORY_EXPORT_INVALID_FORMAT` | 400 | 不支持的导出格式 | false | Memory |
| `MEMORY_EXPORT_TOO_LARGE` | 413 | 导出数据过大（超过 10MB） | false | Memory |

**状态冲突（State Transition Error）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `SCENE_INVALID_STAGE` | 422 | 当前场景阶段不允许此操作 | false | Scene |
| `SCENE_INSTANCE_INVALID_STATE` | 422 | 当前状态不允许此操作 | false | Scene |
| `SCENE_INSTANCE_PENDING_SUBMISSIONS` | 422 | 还有参与者未提交偏好，需强制启动 | false | Scene |
| `SCENE_CANDIDATES_NOT_READY` | 422 | 候选方案尚未生成 | false | Scene |

**资源冲突（Conflict）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `PRECONDITION_FAILED` | 409 | If-Match/ETag 不匹配，资源已被修改 | true | Admin |
| `SCENE_VOTE_ALREADY_VOTED` | 409 | 已投票过（使用 Idempotency-Key 可安全重试） | false | Scene |
| `SCENE_INSTANCE_SUBMISSION_ALREADY_EXISTS` | 409 | 已提交过偏好 | false | Scene |
| `SCENE_INSTANCE_CONSENT_ALREADY_GRANTED` | 409 | 已授权过 | false | Scene |
| `SCENE_INSTANCE_CONSENT_EXPIRED` | 403 | 授权已过期，需重新授权 | false | Scene |
| `SCENE_INSTANCE_PARTICIPANT_ALREADY_EXISTS` | 409 | 参与者已存在 | false | Scene |
| `SCENE_INSTANCE_PARTICIPANT_LIMIT_REACHED` | 409 | 参与者数量已达上限 | false | Scene |
| `SCENE_CONFIRM_INVALID_CANDIDATE` | 400 | 无效的候选方案 ID | false | Scene |
| `SCENE_VOTE_INVALID_CANDIDATE` | 400 | 无效的候选方案 ID | false | Scene |
| `SCENE_CONFIRM_MEMORY_WRITE_FAILED` | 500 | 长期记忆写入失败 | false | Scene |
| `MESSAGE_CANNOT_RECALL` | 403 | 超过撤回时限（15 分钟） | false | Conversation |
| `MESSAGE_HARD_DELETE_DENIED` | 403 | 无权限执行硬删除 | false | Conversation |
| `MESSAGE_HARD_DELETE_PRIVATE_SESSION` | 403 | 私密会话消息不支持硬删除 | false | Conversation |
| `MESSAGE_HARD_DELETE_AGENT_DOMAIN` | 403 | Agent 私域消息不支持硬删除 | false | Conversation |
| `MESSAGE_HARD_DELETE_SCENE_PRIVATE` | 403 | Scene 私有提交不支持硬删除 | false | Conversation |
| `MEMORY_CONSENT_REQUIRED` | 403 | 更新敏感分类需要重新授权 | false | Memory |
| `MEMORY_EXPORT_CONFIRMATION_REQUIRED` | 400 | 导出敏感记忆需要用户二次确认 | false | Memory |
| `MEMORY_EXPORT_RATE_LIMITED` | 429 | 导出频率超限（每小时 3 次） | false | Memory |
| `NODE_ALREADY_EXISTS` | 409 | 节点已存在（Idempotency-Key 冲突） | false | Admin |
| `NODE_IN_USE` | 409 | 节点正在处理请求，无法删除 | false | Admin |
| `NODE_OFFLINE` | 503 | 节点离线 | false | Admin |
| `MODEL_ALREADY_EXISTS` | 409 | 模型已存在（Idempotency-Key 冲突） | false | Admin |
| `DEPLOYMENT_ALREADY_EXISTS` | 409 | 部署已存在（Idempotency-Key 冲突） | false | Admin |

**模型网关（Model Gateway）**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `MODEL_UNAVAILABLE` | 503 | 模型服务不可用 | true | Model Gateway / Agent |
| `MODEL_TIMEOUT` | 504 | 模型调用超时 | true | Model Gateway |
| `MODEL_ROUTING_FAILED` | 502 | 模型路由失败 | false | Model Gateway |
| `EXTERNAL_PROVIDER_ERROR` | 502 | 外部模型供应商返回错误 | true | Model Gateway |
| `AGENT_MODEL_UNAVAILABLE` | 503 | Agent 模型服务不可用 | true | Agent |

**内部错误**

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `INTERNAL_ERROR` | 500 | 服务端内部错误 | false | 通用 |
| `SERVICE_UNAVAILABLE` | 503 | 服务暂不可用 | true | Admin / Model Gateway |
| `HEALTH_CHECK_FAILED` | 503 | 节点健康检查失败 | true | Admin |

#### 1.6.4 隐私失败显式化规则

根据威胁模型和隐私基线，以下规则强制实施：

1. **隐私失败必须使用独立错误码**：不得使用 `validation_error` 或通用 `INTERNAL_ERROR` 描述隐私失败
2. **可识别的隐私错误码**：
   - `PRIVACY_CONTEXT_MISSING` - Model Gateway 缺少隐私上下文
   - `PRIVACY_CONTEXT_INVALID` - 隐私上下文字段无效
   - `PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED` - 敏感数据禁止外发
   - `PRIVACY_CONSENT_REVOKED` - 授权被撤销
   - `MEMORY_CONTENT_ENCRYPTED` - 记忆内容加密不可访问
   - `SCENE_INSTANCE_SUBMISSION_ENCRYPTION_FAILED` - 加密失败拒绝执行
3. **权限失败 ≠ 隐私失败**：
   - `*_PERMISSION_DENIED` 属于 `authorization`（403），表示"你没有权限"
   - `PRIVACY_*` 属于 `privacy_violation`（403），表示"系统阻止你访问以保护他人隐私"
4. **前端处理差异**：
   - `authorization`：显示"无权访问"
   - `privacy_violation`：显示"此操作受隐私保护限制"，不得提示如何绕过

#### 1.6.5 错误码命名规范

- 格式：`MODULE_REASON`（大写下划线）
- `MODULE`：2-8 字符模块缩写（`AUTH`、`CONVERSATION`、`SCENE_INSTANCE`、`MEMORY`、`MODEL`、`ADMIN`、`DIRECTORY`、`AGENT`、`ORG`）
- `REASON`：描述失败原因，使用动词过去分词或名词短语
- 同一失败原因在不同模块使用各自前缀，不跨模块复用
- **例外**：幂等性错误码 `IDEMPOTENCY_CONFLICT`、`IDEMPOTENCY_KEY_REQUIRED` 为跨模块通用码，不分模块前缀（所有模块共用同一错误码）

#### 1.6.6 端点错误码清单

**CSRF 校验规则（适用于所有 Cookie 已认证的浏览器写请求）**：

| 请求类型 | CSRF 校验 | 错误码 |
|----------|:---------:|--------|
| Cookie 已认证的浏览器端 POST/PATCH/PUT/DELETE | ✅ 必须 | `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| 浏览器端 GET/HEAD/OPTIONS | ❌ 豁免 | 无 |
| 未认证端点（login/register） | ❌ 豁免 | 无 |
| 内部服务（Bearer Token） | ❌ 豁免 | 无 |
| WebSocket 握手 | ❌ 豁免 | 无 |

**端点错误码规范**：
- 写端点（POST/PATCH/PUT/DELETE）必须标注 `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH`
- `CSRF_TOKEN_EXPIRED` 为可选增强（P2 实现），MVP 阶段不进入端点错误码清单
- 豁免端点（GET/HEAD/OPTIONS、login/register、内部端点）不标注 CSRF 错误码

每个端点必须在文档中列出可能返回的错误码。以下为 R1-08～R1-13 端点的错误码关联：

**Auth（2.1）**

| 端点 | 错误码 |
|------|--------|
| POST /api/v1/auth/register | `AUTH_WEAK_PASSWORD`、`USER_ALREADY_EXISTS` |
| POST /api/v1/auth/login | `AUTH_INVALID_CREDENTIALS` |
| POST /api/v1/auth/refresh | `AUTH_REFRESH_TOKEN_REVOKED`、`AUTH_REFRESH_TOKEN_EXPIRED`、`AUTH_INVALID_TOKEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/auth/logout | `AUTH_INVALID_TOKEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/auth/me | `AUTH_INVALID_TOKEN` |

**User（2.2）**

| 端点 | 错误码 |
|------|--------|
| GET /api/v1/users/{user_id} | `USER_NOT_FOUND` |
| PATCH /api/v1/users/{user_id} | `USER_NOT_FOUND`、`USER_PERMISSION_DENIED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/users/{user_id}/organizations | `USER_NOT_FOUND` |
| GET /api/v1/users/{user_id}/agent | `USER_NOT_FOUND`、`AGENT_NOT_FOUND` |

**Organization（2.3）**

| 端点 | 错误码 |
|------|--------|
| POST /api/v1/organizations | `ORG_INVALID_JOIN_POLICY`、`ORG_CAPACITY_EXCEEDED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/organizations | （无业务错误） |
| GET /api/v1/organizations/{organization_id} | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED` |
| PATCH /api/v1/organizations/{organization_id} | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| DELETE /api/v1/organizations/{organization_id} | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`ORG_LAST_OWNER_CANNOT_LEAVE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/organizations/{organization_id}/members | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`USER_NOT_FOUND`、`ORG_MEMBER_ALREADY_EXISTS`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/organizations/{organization_id}/members | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED` |
| PATCH /api/v1/organizations/{organization_id}/members/{user_id} | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`USER_NOT_FOUND`、`ORG_LAST_OWNER_CANNOT_LEAVE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| DELETE /api/v1/organizations/{organization_id}/members/{user_id} | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`USER_NOT_FOUND`、`ORG_LAST_OWNER_CANNOT_LEAVE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/organizations/{organization_id}/join | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`ORG_MEMBER_ALREADY_EXISTS`、`ORG_INVALID_JOIN_POLICY`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/organizations/{organization_id}/leave | `ORG_NOT_FOUND`、`ORG_PERMISSION_DENIED`、`ORG_LAST_OWNER_CANNOT_LEAVE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

**Directory（2.4）**

| 端点 | 错误码 |
|------|--------|
| GET /api/v1/directory/search | `DIRECTORY_QUERY_TOO_SHORT`、`DIRECTORY_INVALID_TYPE` |
| GET /api/v1/directory/tree | `DIRECTORY_ORG_NOT_FOUND`、`DIRECTORY_TREE_TOO_DEEP` |
| GET /api/v1/directory/recommended | 无（占位接口始终成功） |

**Conversation（2.5）**

| 端点 | 错误码 |
|------|--------|
| POST /api/v1/conversations | `CONVERSATION_INVALID_PRIVACY_LEVEL`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/conversations | （无业务错误） |
| GET /api/v1/conversations/{conversation_id} | `CONVERSATION_NOT_FOUND`、`CONVERSATION_NOT_PARTICIPANT` |
| PATCH /api/v1/conversations/{conversation_id} | `CONVERSATION_NOT_FOUND`、`CONVERSATION_PERMISSION_DENIED`、`CONVERSATION_INVALID_PRIVACY_LEVEL`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/conversations/{conversation_id}/participants | `CONVERSATION_NOT_FOUND`、`CONVERSATION_PERMISSION_DENIED`、`CONVERSATION_PARTICIPANT_ALREADY_EXISTS`、`CONVERSATION_AGENT_NOT_FOUND`、`CONVERSATION_USER_NOT_FOUND`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| DELETE /api/v1/conversations/{conversation_id}/participants/{participant_id} | `CONVERSATION_NOT_FOUND`、`CONVERSATION_PARTICIPANT_NOT_FOUND`、`CONVERSATION_PERMISSION_DENIED`、`CONVERSATION_LAST_OWNER_CANNOT_LEAVE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/conversations/{conversation_id}/messages | `CONVERSATION_NOT_FOUND`、`CONVERSATION_NOT_PARTICIPANT`、`MESSAGE_INVALID_SENDER_TYPE` |
| POST /api/v1/conversations/{conversation_id}/messages | `CONVERSATION_NOT_FOUND`、`CONVERSATION_NOT_PARTICIPANT`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| DELETE /api/v1/messages/{message_id} | `MESSAGE_NOT_FOUND`、`MESSAGE_PERMISSION_DENIED`、`MESSAGE_CANNOT_RECALL`、`MESSAGE_HARD_DELETE_DENIED`、`MESSAGE_HARD_DELETE_PRIVATE_SESSION`、`MESSAGE_HARD_DELETE_AGENT_DOMAIN`、`MESSAGE_HARD_DELETE_SCENE_PRIVATE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

**Agent（2.6）**

| 端点 | 错误码 |
|------|--------|
| GET /api/v1/agents/me | `AGENT_NOT_FOUND`、`AGENT_PERMISSION_DENIED` |
| PATCH /api/v1/agents/me | `AGENT_NOT_FOUND`、`AGENT_PERMISSION_DENIED`、`AGENT_INVALID_AUTONOMY_LEVEL` |
| POST /api/v1/agents/me/chat | `AGENT_NOT_FOUND`、`AGENT_PERMISSION_DENIED`、`AGENT_INVALID_AUTONOMY_LEVEL`、`AGENT_CHAT_DISABLED`、`AGENT_MODEL_UNAVAILABLE` |
| GET /api/v1/agents/me/permissions | `AGENT_NOT_FOUND`、`AGENT_PERMISSION_DENIED` |
| PATCH /api/v1/agents/me/permissions | `AGENT_NOT_FOUND`、`AGENT_PERMISSION_DENIED`、`AGENT_INVALID_AUTONOMY_LEVEL`、`AGENT_SCENE_NOT_FOUND`、`AGENT_PERMISSION_EXPIRED` |
| GET /api/v1/agents/me/runs | `AGENT_NOT_FOUND`、`AGENT_PERMISSION_DENIED`、`AGENT_RUN_INVALID_STATUS` |

**Memory（2.7）**

| 端点 | 错误码 |
|------|--------|
| GET /api/v1/memories | `MEMORY_ACCESS_INVALID_FILTER` |
| POST /api/v1/memories | `MEMORY_CONSENT_REQUIRED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/memories/{memory_id} | `MEMORY_NOT_FOUND`、`MEMORY_PERMISSION_DENIED`、`MEMORY_CONTENT_ENCRYPTED` |
| PATCH /api/v1/memories/{memory_id} | `MEMORY_NOT_FOUND`、`MEMORY_PERMISSION_DENIED`、`MEMORY_INVALID_FIELD`、`MEMORY_CONSENT_REQUIRED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| DELETE /api/v1/memories/{memory_id} | `MEMORY_NOT_FOUND`、`MEMORY_PERMISSION_DENIED`、`MEMORY_IN_USE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/memories/access-log | `MEMORY_ACCESS_DENIED`、`MEMORY_ACCESS_INVALID_FILTER` |
| POST /api/v1/memories/export | `MEMORY_NOT_FOUND`、`MEMORY_PERMISSION_DENIED`、`MEMORY_EXPORT_INVALID_FORMAT`、`MEMORY_EXPORT_CONFIRMATION_REQUIRED`、`MEMORY_EXPORT_TOO_LARGE`、`MEMORY_EXPORT_RATE_LIMITED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

**Scene（2.8）**

| 端点 | 错误码 |
|------|--------|
| GET /api/v1/scenes | `SCENE_LIST_INVALID_TYPE` |
| GET /api/v1/scenes/{scene_key} | `SCENE_NOT_FOUND` |
| POST /api/v1/scene-instances | `SCENE_INSTANCE_CREATE_INVALID_SCENE_KEY`、`SCENE_INSTANCE_CREATE_NO_PARTICIPANTS`、`SCENE_INSTANCE_CREATE_CONVERSATION_NOT_FOUND`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/scene-instances/{scene_instance_id} | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_PERMISSION_DENIED` |
| POST /api/v1/scene-instances/{scene_instance_id}/participants | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_PERMISSION_DENIED`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_INSTANCE_PARTICIPANT_ALREADY_EXISTS`、`SCENE_INSTANCE_PARTICIPANT_LIMIT_REACHED`、`CONVERSATION_USER_NOT_FOUND`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/scene-instances/{scene_instance_id}/consent | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_NOT_PARTICIPANT`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_INSTANCE_CONSENT_ALREADY_GRANTED`、`SCENE_INSTANCE_CONSENT_EXPIRED`、`PRIVACY_CONSENT_REVOKED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/scene-instances/{scene_instance_id}/private-submission | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_NOT_PARTICIPANT`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_INSTANCE_SUBMISSION_ALREADY_EXISTS`、`SCENE_INSTANCE_SUBMISSION_ENCRYPTION_FAILED`、`PRIVACY_CONSENT_REVOKED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/scene-instances/{scene_instance_id}/start | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_PERMISSION_DENIED`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_INSTANCE_PENDING_SUBMISSIONS`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| GET /api/v1/scene-instances/{scene_instance_id}/candidates | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_NOT_PARTICIPANT`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_CANDIDATES_NOT_READY` |
| POST /api/v1/scene-instances/{scene_instance_id}/vote | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_NOT_PARTICIPANT`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_CANDIDATES_NOT_READY`、`SCENE_VOTE_INVALID_CANDIDATE`、`SCENE_VOTE_ALREADY_VOTED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/scene-instances/{scene_instance_id}/confirm | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_PERMISSION_DENIED`、`SCENE_INSTANCE_INVALID_STATE`、`SCENE_CANDIDATES_NOT_READY`、`SCENE_CONFIRM_INVALID_CANDIDATE`、`SCENE_CONFIRM_MEMORY_WRITE_FAILED`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/scene-instances/{scene_instance_id}/cancel | `SCENE_INSTANCE_NOT_FOUND`、`SCENE_INSTANCE_PERMISSION_DENIED`、`SCENE_INSTANCE_INVALID_STATE`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

**Model Gateway（2.9）**

| 端点 | 错误码 |
|------|--------|
| POST /internal/v1/model/chat | `PRIVACY_CONTEXT_MISSING`、`PRIVACY_CONTEXT_INVALID`、`PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED`、`MODEL_UNAVAILABLE`、`MODEL_TIMEOUT`、`MODEL_ROUTING_FAILED`、`INVALID_INPUT`、`INTERNAL_ERROR`、`EXTERNAL_PROVIDER_ERROR` |
| POST /internal/v1/model/embedding | 同 POST /internal/v1/model/chat |
| GET /internal/v1/model/health | `INTERNAL_ERROR`、`SERVICE_UNAVAILABLE` |

**Admin（2.10）**

| 端点 | 错误码 |
|------|--------|
| POST /api/v1/admin/nodes | `ADMIN_PERMISSION_DENIED`、`NODE_ALREADY_EXISTS`、`INVALID_ENDPOINT`、`INVALID_CAPABILITIES` |
| GET /api/v1/admin/nodes | `ADMIN_PERMISSION_DENIED`、`INVALID_PAGINATION` |
| GET /api/v1/admin/nodes/{node_id} | `ADMIN_PERMISSION_DENIED`、`NODE_NOT_FOUND` |
| PATCH /api/v1/admin/nodes/{node_id} | `ADMIN_PERMISSION_DENIED`、`NODE_NOT_FOUND`、`PRECONDITION_FAILED` |
| DELETE /api/v1/admin/nodes/{node_id} | `ADMIN_PERMISSION_DENIED`、`NODE_NOT_FOUND`、`NODE_IN_USE` |
| POST /api/v1/admin/nodes/{node_id}/health-check | `ADMIN_PERMISSION_DENIED`、`NODE_NOT_FOUND`、`HEALTH_CHECK_FAILED`、`NODE_OFFLINE` |
| GET /api/v1/admin/nodes/{node_id}/metrics | `ADMIN_PERMISSION_DENIED`、`NODE_NOT_FOUND`、`INVALID_TIME_RANGE` |
| POST /api/v1/admin/models | `ADMIN_PERMISSION_DENIED`、`MODEL_ALREADY_EXISTS`、`INVALID_MODEL_CONFIG` |
| GET /api/v1/admin/models | `ADMIN_PERMISSION_DENIED`、`INVALID_PAGINATION` |
| POST /api/v1/admin/deployments | `ADMIN_PERMISSION_DENIED`、`MODEL_NOT_FOUND`、`NODE_NOT_FOUND`、`DEPLOYMENT_ALREADY_EXISTS` |
| GET /api/v1/admin/deployments | `ADMIN_PERMISSION_DENIED`、`INVALID_PAGINATION` |

---

### 1.7 统一响应模型

#### 1.7.1 响应结构总览

所有 API 响应使用统一结构：

```json
{
  "success": true,
  "data": {},
  "request_id": "req_xxx"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 请求是否成功（`true` 或 `false`） |
| `data` | object/array/null | 响应数据（成功时）或 `null`（失败时，失败详情在 `error` 字段） |
| `request_id` | string | 请求追踪 ID（UUID v4） |

**失败响应**（见 1.6.1）：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "MODULE_REASON",
    "message": "人类可读的错误信息",
    "details": {},
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

#### 1.7.2 列表响应

**适用端点**：所有 GET List 端点（如 `GET /api/v1/conversations`、`GET /api/v1/organizations`）

**结构**：
```json
{
  "success": true,
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 100
  },
  "request_id": "req_xxx"
}
```

**规则**：
- ✅ `items` 始终为数组（空列表表示无数据）
- ✅ `page`、`page_size`、`total` 始终存在
- ✅ 空列表时 `total` 为 0
- ❌ 不使用 `null` 代替空数组

#### 1.7.3 详情响应

**适用端点**：所有 GET Detail 端点（如 `GET /api/v1/users/{user_id}`、`GET /api/v1/scene-instances/{id}`）

**结构**：
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "...",
    "created_at": "2026-07-14T10:30:00Z"
  },
  "request_id": "req_xxx"
}
```

**规则**：
- ✅ `data` 为单个对象
- ✅ 资源不存在时返回 404（`*_NOT_FOUND`）
- ❌ 不使用 `null` 表示资源不存在（使用 HTTP 状态码）

#### 1.7.4 创建响应

**适用端点**：所有 POST 创建端点（如 `POST /api/v1/organizations`、`POST /api/v1/scene-instances`）

**结构**：
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "...",
    "created_at": "2026-07-14T10:30:00Z"
  },
  "request_id": "req_xxx"
}
```

**HTTP 状态码**：`201 Created`

**规则**：
- ✅ `data` 包含新创建资源的完整字段
- ✅ `id` 字段必返（客户端需要知道新资源 ID）
- ✅ `created_at` 字段必返
- ✅ 如果支持幂等性，响应中包含 `idempotency_key` 字段
- ✅ `Location` 头指向新资源 URL（`/api/v1/organizations/{id}`）

**幂等响应**：与首次创建返回完全相同的内容（包括 `request_id`）

#### 1.7.5 更新响应

**适用端点**：所有 PATCH/PUT 端点（如 `PATCH /api/v1/users/{user_id}`、`PATCH /api/v1/organizations/{id}`）

**结构**：
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "...",
    "updated_at": "2026-07-14T10:30:00Z"
  },
  "request_id": "req_xxx"
}
```

**HTTP 状态码**：`200 OK`

**规则**：
- ✅ `data` 包含更新后的完整资源
- ✅ `updated_at` 字段必返
- ✅ 未修改的字段也返回（完整资源）
- ✅ 如果请求了不存在的字段，返回 `MEMORY_INVALID_FIELD`（400）

#### 1.7.6 异步任务响应

**适用端点**：触发异步处理的端点（如 `POST /api/v1/scene-instances/{id}/start`、`POST /api/v1/scene-instances/{id}/private-submission`）

**结构**：
```json
{
  "success": true,
  "data": {
    "instance_id": "uuid",
    "status": "PROCESSING",
    "started_at": "2026-07-14T10:45:00Z",
    "estimated_completion": "2026-07-14T11:15:00Z"
  },
  "request_id": "req_xxx"
}
```

**HTTP 状态码**：`202 Accepted`

**规则**：
- ✅ `status` 字段必返（当前处理状态）
- ✅ `started_at` 字段必返
- ✅ `estimated_completion` 可选（如果可预估）
- ✅ 客户端应轮询 `GET /api/v1/scene-instances/{id}` 获取最新状态
- ✅ 状态变更通过 WebSocket 推送（P0-10）

**状态值**：
- `PENDING` - 排队中
- `PROCESSING` - 处理中
- `COMPLETED` - 完成
- `FAILED` - 失败（`failure_reason` 字段说明原因）

#### 1.7.7 删除响应

**适用端点**：所有 DELETE 端点（如 `DELETE /api/v1/organizations/{id}`、`DELETE /api/v1/messages/{id}`）

**结构**：
```json
{
  "success": true,
  "data": null,
  "request_id": "req_xxx"
}
```

**HTTP 状态码**：`204 No Content`

**规则**：
- ✅ 204 响应体为空（无 `data` 字段）
- ✅ 删除成功后客户端应从缓存中移除该资源
- ✅ 软删除的资源仍可通过 GET 查询（`deleted_at` 不为 null）
- ❌ 不使用 200 OK + 空对象表示删除成功

#### 1.7.8 空值处理规则

**统一规则**：

| 场景 | 响应行为 |
|------|---------|
| 资源存在，字段值为空 | 返回 `null` |
| 资源存在，字段不存在 | 省略该字段 |
| 数组为空 | 返回 `[]` |
| 对象为空 | 返回 `{}` |
| 404 资源不存在 | 返回错误响应（`data: null`） |

**示例**：
```json
// 正常响应（某些字段为 null）
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "张三",
    "avatar_url": null,
    "bio": null,
    "created_at": "2026-07-14T10:30:00Z"
  },
  "request_id": "req_xxx"
}

// 404 响应
{
  "success": false,
  "data": null,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "用户不存在",
    "details": {},
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

---

### 1.8 请求校验规则

#### 1.8.1 校验时机

**校验层级**：
1. **路由层**：路径格式、HTTP 方法、Content-Type
2. **认证层**：Token 有效性、账号状态
3. **参数层**：查询参数、路径参数、请求体
4. **业务层**：状态冲突、权限检查、业务规则

**校验失败响应**：
- 路由/参数校验失败 → `400 Bad Request` + `INVALID_INPUT`
- 认证失败 → `401 Unauthorized` + `AUTH_INVALID_TOKEN`
- 权限失败 → `403 Forbidden` + `*_PERMISSION_DENIED`
- 资源不存在 → `404 Not Found` + `*_NOT_FOUND`

#### 1.8.2 字段校验规则

**字符串**：
- 最小长度：`minLength`（如 `display_name` 最少 2 字符）
- 最大长度：`maxLength`（如 `display_name` 最多 50 字符）
- 格式：`pattern`（如 `email` 使用 RFC 5322 格式）
- 空值：允许 `null` 或空字符串（取决于字段定义）

**数字**：
- 最小值：`minimum`（如 `budget_max` ≥ 0）
- 最大值：`maximum`（如 `budget_max` ≤ 1000000）
- 精度：整数或浮点数（文档中明确指定）

**数组**：
- 最小长度：`minItems`（如 `participant_user_ids` 最少 1 个）
- 最大长度：`maxItems`（如 `participant_user_ids` 最多 50 个）
- 唯一性：`uniqueItems`（如 `user_ids` 不允许重复）

**对象**：
- 必填字段：`required` 数组列出
- 额外字段：拒绝（`additionalProperties: false`）

#### 1.8.3 校验错误响应

**结构**：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "请求参数验证失败",
    "details": {
      "field": "email",
      "reason": "格式无效",
      "constraint": "email"
    },
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

**批量校验错误**（可选，MVP 阶段返回第一个错误）：
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_INPUT",
    "message": "多个字段验证失败",
    "details": {
      "errors": [
        {"field": "email", "reason": "格式无效"},
        {"field": "display_name", "reason": "长度超过 50 字符"}
      ]
    },
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

**MVP 阶段规则**：
- ✅ 返回第一个校验错误（简化）
- ✅ `details.field` 指向出错字段
- ✅ `details.reason` 说明失败原因
- ❌ 不返回完整字段列表（P2 阶段支持批量错误）

#### 1.8.4 错误码映射

**R1-15 错误码在 R1-16 校验中的使用**：

| 校验场景 | 错误码 | HTTP |
|---------|--------|------|
| 必填字段缺失 | `INVALID_INPUT` | 400 |
| 字段类型错误 | `INVALID_INPUT` | 400 |
| 字段值超出范围 | `INVALID_INPUT` | 400 |
| 字符串长度超限 | `INVALID_INPUT` | 400 |
| 数组长度超限 | `INVALID_INPUT` | 400 |
| 枚举值无效 | `INVALID_INPUT` | 400 |
| 格式不匹配（email、UUID） | `INVALID_INPUT` | 400 |
| 分页参数无效 | `INVALID_PAGINATION` | 400 |
| 时间格式无效 | `INVALID_INPUT` | 400 |
| 缺少 Idempotency-Key | `IDEMPOTENCY_KEY_REQUIRED` | 400 |

**R1-15 错误码在业务逻辑中的使用**：
- 见 Section 1.6.6 端点错误码清单

#### 1.8.5 内容类型

**请求**：
- `POST`/`PATCH`/`PUT`：`Content-Type: application/json`
- 请求体必须为合法 JSON
- 非法 JSON → `400 Bad Request` + `INVALID_INPUT`

**响应**：
- 所有响应：`Content-Type: application/json; charset=utf-8`
- 不使用其他内容类型（MVP 阶段）

## 2. API 端点清单

### 2.1 Auth（认证）

#### POST /api/v1/auth/register

**描述**：注册新用户

**权限**：公开

**请求体**：
```json
{
  "email": "student@example.edu",
  "password": "******",
  "display_name": "张三",
  "student_no": "20260001",
  "organization_ids": ["class_uuid", "dorm_uuid"]
}
```

**响应**：201 Created

**响应头**：
```
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1; Max-Age=3600
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800
Set-Cookie: csrf_token=<random>; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

**说明**：
- 邮箱和学号必须唯一
- 支持幂等性（见 1.4）
- 发布 `UserRegistered` 事件
- Token 通过 `Set-Cookie` 响应头发放，注册成功后自动登录
- `csrf_token` Cookie 用于 CSRF 防护（非 HttpOnly，前端可读取）
- 注册成功后前端可读取 `csrf_token` Cookie，并用于后续写请求的 `X-CSRF-Token` 请求头

**错误码**：
- `AUTH_WEAK_PASSWORD` - 密码强度不足
- `USER_ALREADY_EXISTS` - 邮箱或学号已被注册

---

#### POST /api/v1/auth/login

**描述**：用户登录

**权限**：公开

**认证方式**：无（公开端点）

**请求体**：
```json
{
  "email": "student@example.edu",
  "password": "******"
}
```

**响应**：200 OK

**响应体**：
```json
{
  "id": "uuid",
  "email": "student@example.edu",
  "display_name": "张三",
  "global_role": "STUDENT"
}
```

**响应头**：
```
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1; Max-Age=3600
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800
Set-Cookie: csrf_token=<random>; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

**说明**：
- Token 通过 `Set-Cookie` 响应头发放，不返回在响应体中
- `access_token`：有效期 1 小时，`Path=/api/v1`，用于 API 认证
- `refresh_token`：有效期 7 天，`Path=/api/v1/auth`，仅用于刷新令牌
- `csrf_token`：有效期 7 天，`Path=/`，用于 CSRF 防护（非 HttpOnly，前端可读取）
- 前端不得读取 `access_token`/`refresh_token` Cookie（`HttpOnly` 禁止 JavaScript 访问）
- 浏览器自动在后续请求中携带 Cookie
- 前端需读取 `csrf_token` Cookie 值，并在写请求中通过 `X-CSRF-Token` 请求头携带

**安全**：
- 密码错误次数限制
- 不泄露账号是否存在
- 统一响应时间

**错误码**：
- `AUTH_INVALID_CREDENTIALS` - 邮箱或密码错误（统一响应，不区分具体原因，防止账号枚举）

---

#### POST /api/v1/auth/refresh

**描述**：刷新访问令牌（Refresh Token 轮换）

**权限**：已认证（通过 refresh_token Cookie）

**认证方式**：Cookie（`refresh_token`）

**请求体**：无（refresh_token 从 Cookie 中读取）

**响应**：200 OK

**响应体**：
```json
{
  "id": "uuid",
  "email": "student@example.edu",
  "display_name": "张三",
  "global_role": "STUDENT",
  "session_version": 3
}
```

**响应头**：
```
Set-Cookie: access_token=<new_jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1; Max-Age=3600
Set-Cookie: refresh_token=<new_jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800
```

**说明**：
- `refresh_token` 从 `Cookie` 中读取（不在请求体中传递）
- **Refresh Token 轮换**：每次刷新成功时，颁发新的 `refresh_token`，旧 `refresh_token` 立即失效（加入黑名单）
- `access_token` 和 `refresh_token` 都通过 `Set-Cookie` 响应头发放
- `session_version` 表示当前会话版本号，每次刷新递增（用于前端检测会话状态变化）
- 如果 `refresh_token` 无效、已撤销、已过期或被检测为重放攻击，返回对应错误码
- **重放检测**：如果检测到同一 `refresh_token` 被使用两次（重放），立即撤销整个 token family（所有关联的 refresh_token），标记 session compromised
- 前端需要检测 `session_version` 变化，如果版本号突然变化，提示用户重新登录（安全警告）

**Token Family 机制**：
- 每次登录/刷新时生成新的 token family ID
- `refresh_token` 包含 family ID
- 重放检测：同一 family ID 的 refresh_token 只能使用一次
- 检测到重放时：撤销整个 family（所有关联的 refresh_token），标记 session compromised

**错误码**：
- `AUTH_REFRESH_TOKEN_REVOKED` - Refresh Token 已被撤销（包括重放检测触发撤销）
- `AUTH_REFRESH_TOKEN_EXPIRED` - Refresh Token 已过期
- `AUTH_INVALID_TOKEN` - 未找到 refresh_token（Cookie 缺失）
- `CSRF_TOKEN_MISSING` - 缺少 CSRF Token
- `CSRF_TOKEN_MISMATCH` - CSRF Token 不匹配

---

#### POST /api/v1/auth/logout

**描述**：注销（清除认证 Cookie 并撤销 session）

**权限**：已认证

**认证方式**：Cookie（`access_token`）

**请求体**：无

**响应**：204 No Content

**响应头**：
```
Set-Cookie: access_token=; HttpOnly; Secure; SameSite=Lax; Path=/api/v1; Max-Age=0
Set-Cookie: refresh_token=; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=0
Set-Cookie: csrf_token=; Secure; SameSite=Lax; Path=/; Max-Age=0
```

**说明**：
- 服务端撤销当前 refresh_token（加入黑名单）
- 服务端撤销整个 token family（所有关联的 refresh_token）
- 通过 `Set-Cookie` 清除浏览器中的 access_token、refresh_token 和 csrf_token
- `Max-Age=0` 表示立即过期
- 前端应同时清除客户端状态（如 Vuex/Pinia store）

**错误码**：
- `AUTH_INVALID_TOKEN` - 未认证或令牌无效
- `CSRF_TOKEN_MISSING` - 缺少 CSRF Token
- `CSRF_TOKEN_MISMATCH` - CSRF Token 不匹配

---

#### GET /api/v1/auth/me

**描述**：获取当前用户信息

**权限**：已认证

**认证方式**：Cookie（`access_token`）

**请求头**：
```
Cookie: access_token=<jwt>
```

**响应**：200 OK
```json
{
  "id": "uuid",
  "email": "...",
  "display_name": "...",
  "global_role": "STUDENT",
  "agent": { ... }
}
```

**说明**：
- 认证信息从 `Cookie` 中读取（不在 `Authorization` 头中传递）
- 前端通过此接口验证登录状态

**错误码**：
- `AUTH_INVALID_TOKEN` - 未认证或令牌无效

---

### 2.2 User（用户）

#### GET /api/v1/users/{user_id}

**描述**：获取用户详情

**权限**：公开信息

**响应**：200 OK
```json
{
  "id": "uuid",
  "display_name": "...",
  "avatar_url": "...",
  "profile_visibility": "PUBLIC"
}
```

**隐私**：
- 不返回私有信息
- 可见性控制生效

**错误码**：
- `USER_NOT_FOUND` - 用户不存在或已注销

---

#### PATCH /api/v1/users/{user_id}

**描述**：更新用户资料

**权限**：本人或管理员

**请求体**：
```json
{
  "display_name": "...",
  "bio": "..."
}
```

**响应**：200 OK

**错误码**：
- `USER_NOT_FOUND` - 用户不存在
- `USER_PERMISSION_DENIED` - 无权限修改（非本人或管理员）

---

#### GET /api/v1/users/{user_id}/organizations

**描述**：获取用户组织列表

**权限**：本人或管理员

**响应**：200 OK

**错误码**：
- `USER_NOT_FOUND` - 用户不存在

---

#### GET /api/v1/users/{user_id}/agent

**描述**：获取用户智能体

**权限**：本人或管理员

**响应**：200 OK

**错误码**：
- `USER_NOT_FOUND` - 用户不存在
- `AGENT_NOT_FOUND` - 用户尚未创建智能体

---

### 2.3 Organization（组织）

#### POST /api/v1/organizations

**描述**：创建组织

**权限**：已认证

**请求体**：
```json
{
  "name": "8栋302宿舍",
  "type": "DORM",
  "description": "...",
  "visibility": "PRIVATE",
  "join_policy": "INVITE_ONLY"
}
```

**响应**：201 Created

**错误码**：
- `ORG_INVALID_JOIN_POLICY` - 无效的加入策略
- `ORG_CAPACITY_EXCEEDED` - 组织成员数已达上限

---

#### GET /api/v1/organizations

**描述**：获取组织列表

**权限**：已认证

**查询参数**：
```
?type=DORM&page=1&page_size=20
```

**响应**：200 OK

---

#### GET /api/v1/organizations/{organization_id}

**描述**：获取组织详情

**权限**：成员或可见性允许

**响应**：200 OK

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权查看此组织

---

#### PATCH /api/v1/organizations/{organization_id}

**描述**：更新组织

**权限**：OWNER 或 ADMIN

**请求体**：部分更新

**响应**：200 OK

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权修改此组织

---

#### DELETE /api/v1/organizations/{organization_id}

**描述**：删除组织

**权限**：OWNER

**响应**：204 No Content

**说明**：软删除或归档

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权删除此组织
- `ORG_LAST_OWNER_CANNOT_LEAVE` - 最后一个所有者不能删除组织

---

#### POST /api/v1/organizations/{organization_id}/members

**描述**：添加成员

**权限**：OWNER 或 ADMIN

**请求体**：
```json
{
  "user_id": "uuid",
  "role": "MEMBER"
}
```

**响应**：201 Created

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权添加成员
- `USER_NOT_FOUND` - 用户不存在
- `ORG_MEMBER_ALREADY_EXISTS` - 用户已是组织成员

---

#### GET /api/v1/organizations/{organization_id}/members

**描述**：获取成员列表

**权限**：成员

**响应**：200 OK

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权查看成员列表

---

#### PATCH /api/v1/organizations/{organization_id}/members/{user_id}

**描述**：更新成员角色

**权限**：OWNER 或 ADMIN

**请求体**：
```json
{
  "role": "ADMIN"
}
```

**响应**：200 OK

**保护**：最后一个 OWNER 不能降级

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权修改成员角色
- `USER_NOT_FOUND` - 目标用户不存在
- `ORG_LAST_OWNER_CANNOT_LEAVE` - 最后一个所有者不能降级

---

#### DELETE /api/v1/organizations/{organization_id}/members/{user_id}

**描述**：移除成员

**权限**：OWNER 或 ADMIN

**响应**：204 No Content

**保护**：最后一个 OWNER 不能移除

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权移除成员
- `USER_NOT_FOUND` - 目标用户不存在
- `ORG_LAST_OWNER_CANNOT_LEAVE` - 最后一个所有者不能移除

---

#### POST /api/v1/organizations/{organization_id}/join

**描述**：加入组织

**权限**：已认证

**响应**：201 Created

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 当前加入策略不允许
- `ORG_MEMBER_ALREADY_EXISTS` - 已是组织成员
- `ORG_INVALID_JOIN_POLICY` - 当前加入策略不允许加入

---

#### POST /api/v1/organizations/{organization_id}/leave

**描述**：退出组织

**权限**：成员

**响应**：204 No Content

**保护**：最后一个 OWNER 不能退出

**错误码**：
- `ORG_NOT_FOUND` - 组织不存在
- `ORG_PERMISSION_DENIED` - 无权退出此组织
- `ORG_LAST_OWNER_CANNOT_LEAVE` - 最后一个所有者不能退出

---

### 2.4 Directory（目录）

#### GET /api/v1/directory/search

**描述**：搜索用户和组织，基于可见性策略过滤结果

**权限**：已认证

**请求参数**：
```
?q={query}&type={user|org|all}&page=1&page_size=20
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 搜索关键词（用户名、组织名、学号） |
| `type` | string | 否 | 搜索类型：`user`、`org`、`all`（默认 `all`） |
| `page` | int | 否 | 页码（默认 1） |
| `page_size` | int | 否 | 每页数量（默认 20，最大 100） |

**响应**：200 OK
```json
{
  "items": [
    {
      "type": "user",
      "id": "uuid",
      "display_name": "...",
      "avatar_url": "...",
      "bio": "...",
      "student_no": "20260001",
      "organization_count": 2
    },
    {
      "type": "organization",
      "id": "uuid",
      "name": "...",
      "type": "CLASS",
      "description": "...",
      "member_count": 45
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 150
}
```

**隐私投影**：
- 用户：仅返回 `PUBLIC` 或 `INTERNAL` 可见性资料
- 组织：仅返回 `PUBLIC` 或 `INTERNAL` 可见性组织
- 不返回私有信息（email、phone、密码哈希等）
- 搜索关键词不记录到审计日志

**错误码**：
- `DIRECTORY_QUERY_TOO_SHORT` - 搜索词过短（最少 2 字符）
- `DIRECTORY_INVALID_TYPE` - 无效的搜索类型

**可见性规则**：
- `PUBLIC` - 所有人可见
- `INTERNAL` - 仅已认证用户可见
- `PRIVATE` - 不在搜索结果中显示

---

#### GET /api/v1/directory/tree

**描述**：获取组织树形结构，支持按类型过滤

**权限**：已认证

**请求参数**：
```
?root_id={organization_id}&type={SCHOOL|COLLEGE|CLASS|DORM|CLUB|COURSE}&include_private=false
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `root_id` | uuid | 否 | 根组织ID（默认返回顶层结构） |
| `type` | string | 否 | 过滤组织类型（默认全部） |
| `include_private` | bool | 否 | 是否包含私有组织（默认 false） |

**响应**：200 OK
```json
{
  "id": "uuid",
  "name": "计算机学院",
  "type": "COLLEGE",
  "parent_id": null,
  "member_count": 120,
  "children": [
    {
      "id": "uuid",
      "name": "软件工程1班",
      "type": "CLASS",
      "parent_id": "uuid",
      "member_count": 45,
      "children": []
    }
  ]
}
```

**隐私投影**：
- 仅返回 `PUBLIC` 和 `INTERNAL` 组织
- 私有组织需要显式权限才能访问
- 树深度限制：最多 10 层

**错误码**：
- `DIRECTORY_ORG_NOT_FOUND` - 根组织不存在
- `DIRECTORY_TREE_TOO_DEEP` - 树深度超过限制

---

#### GET /api/v1/directory/recommended

**描述**：获取推荐的组织和用户（**占位接口，MVP 暂不实现**）

**权限**：已认证

**请求参数**：无

**响应**：200 OK（占位）
```json
{
  "users": [],
  "organizations": []
}
```

**状态**：MVP 阶段仅返回空数组，P2 阶段实现推荐算法

**隐私投影**：同 `/directory/search`

**错误码**：无（占位接口始终成功）

---

#### POST /api/v1/conversations

**描述**：创建会话

**权限**：已认证

**请求体**：
```json
{
  "type": "GROUP",
  "title": "8栋302宿舍",
  "participant_user_ids": ["uuid1", "uuid2"],
  "attach_group_agent": true
}
```

**响应**：201 Created

---

#### GET /api/v1/conversations

**描述**：获取会话列表

**权限**：已认证

**响应**：200 OK

---

#### GET /api/v1/conversations/{conversation_id}

**描述**：获取会话详情

**权限**：参与者

**响应**：200 OK

---

#### POST /api/v1/conversations/{conversation_id}/messages

**描述**：发送消息

**权限**：参与者

**请求体**：
```json
{
  "message_type": "TEXT",
  "content": "...",
  "reply_to_id": null
}
```

**响应**：201 Created

**隐私**：私有偏好不能通过此接口发送

---

#### PATCH /api/v1/conversations/{conversation_id}

**端点编号**：EP-CONV-024
**描述**：更新会话信息（标题、头像、隐私级别等）

**权限**：会话所有者或管理员

**请求体**：
```json
{
  "title": "新标题",
  "avatar_url": "https://...",
  "privacy_level": "INTERNAL"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 会话标题 |
| `avatar_url` | string | 否 | 头像URL |
| `privacy_level` | string | 否 | 隐私级别：`PUBLIC`/`INTERNAL`/`PRIVATE` |

**响应**：200 OK

```json
{
  "id": "uuid",
  "type": "GROUP",
  "title": "新标题",
  "privacy_level": "INTERNAL",
  "updated_at": "2026-07-14T10:30:00Z"
}
```

**隐私约束**：
- 会话隐私级别变更不影响历史消息可见性
- 私有偏好字段不能通过此接口修改

**错误码**：
- `CONVERSATION_NOT_FOUND` - 会话不存在
- `CONVERSATION_PERMISSION_DENIED` - 无权限修改
- `CONVERSATION_INVALID_PRIVACY_LEVEL` - 无效的隐私级别

---

#### POST /api/v1/conversations/{conversation_id}/participants

**端点编号**：EP-CONV-025
**描述**：向会话添加参与者（用户或智能体）

**权限**：会话所有者或管理员

**请求体**：
```json
{
  "participant_type": "USER",
  "user_id": "uuid",
  "role": "MEMBER"
}
```

或

```json
{
  "participant_type": "AGENT",
  "agent_id": "uuid",
  "role": "MEMBER"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `participant_type` | string | 是 | 参与者类型：`USER` 或 `AGENT` |
| `user_id` | uuid | 条件必填 | 用户ID（participant_type=USER 时必填） |
| `agent_id` | uuid | 条件必填 | 智能体ID（participant_type=AGENT 时必填） |
| `role` | string | 否 | 角色：`OWNER`/`ADMIN`/`MEMBER`（默认 `MEMBER`） |

**响应**：201 Created

```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "participant_type": "USER",
  "user_id": "uuid",
  "role": "MEMBER",
  "joined_at": "2026-07-14T10:30:00Z"
}
```

**边界说明**：
- **Conversation Member**：通过此接口添加，获得会话内权限
- **Organization Member**：组织成员身份独立，不自动获得会话权限
- **Agent Participant**：智能体参与者，有独立的 `agent_id`
- 三者权限互不继承，需分别授权

**错误码**：
- `CONVERSATION_NOT_FOUND` - 会话不存在
- `CONVERSATION_PERMISSION_DENIED` - 无权限添加参与者
- `CONVERSATION_PARTICIPANT_ALREADY_EXISTS` - 参与者已存在
- `CONVERSATION_AGENT_NOT_FOUND` - 智能体不存在
- `CONVERSATION_USER_NOT_FOUND` - 用户不存在

---

#### DELETE /api/v1/conversations/{conversation_id}/participants/{participant_id}

**端点编号**：EP-CONV-026
**描述**：从会话移除参与者

**权限**：
- 会话所有者或管理员可移除任何参与者
- 参与者本人可主动退出（调用者即被移除者）

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `conversation_id` | uuid | 会话ID |
| `participant_id` | uuid | 参与者ID |

**响应**：204 No Content

**隐私约束**：
- 移除后，该参与者无法再访问会话历史消息
- 历史消息保留在系统中，但对该参与者不可见
- 不删除消息内容，仅撤销访问权限

**错误码**：
- `CONVERSATION_NOT_FOUND` - 会话不存在
- `CONVERSATION_PARTICIPANT_NOT_FOUND` - 参与者不存在
- `CONVERSATION_PERMISSION_DENIED` - 无权限移除
- `CONVERSATION_LAST_OWNER_CANNOT_LEAVE` - 最后一个所有者不能退出

---

#### GET /api/v1/conversations/{conversation_id}/messages

**端点编号**：EP-CONV-027
**描述**：获取会话消息列表，支持分页和按发送者过滤

**权限**：会话参与者

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `conversation_id` | uuid | 会话ID |

**请求参数**：
```
?page=1&page_size=50&sender_type={USER|AGENT|SYSTEM}&sender_id={uuid}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码（默认 1） |
| `page_size` | int | 否 | 每页数量（默认 50，最大 200） |
| `sender_type` | string | 否 | 发送者类型过滤 |
| `sender_id` | uuid | 否 | 发送者ID过滤 |

**响应**：200 OK

```json
{
  "items": [
    {
      "id": "uuid",
      "conversation_id": "uuid",
      "sender_type": "USER",
      "sender_user_id": "uuid",
      "sender_agent_id": null,
      "message_type": "TEXT",
      "content": "...",
      "structured_payload": null,
      "visibility": "VISIBLE",
      "reply_to_id": null,
      "created_at": "2026-07-14T10:30:00Z",
      "deleted_at": null
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 150
}
```

**消息可见范围**：
- ✅ **会话参与者可见**：当前会话的所有参与者可看到 `visibility="VISIBLE"` 的消息
- ✅ **组织成员可见**：仅当该组织成员同时也是会话参与者时才可见
- ❌ **非参与者不可见**：即使在同一组织，非参与者无法查看
- ❌ **Agent 私域**：Agent 发送的私有消息不进入群聊可见区
- ❌ **私有偏好**：严格禁止通过消息接口保存，需使用 Scene API

**隐私投影**：
- `deleted_at` 不为 null 的消息不返回（软删除）
- `visibility="HIDDEN"` 的消息不返回
- 仅返回当前会话内的消息，不泄露其他会话

**错误码**：
- `CONVERSATION_NOT_FOUND` - 会话不存在
- `CONVERSATION_NOT_PARTICIPANT` - 非参与者无法查看消息
- `MESSAGE_INVALID_SENDER_TYPE` - 无效的发送者类型过滤

---

#### DELETE /api/v1/messages/{message_id}

**端点编号**：EP-CONV-028
**描述**：删除消息（软删除或撤回）

**权限**：
- 消息发送者可删除自己的消息
- 会话所有者或管理员可删除任何消息

**隐私约束**：
- 硬删除（hard_delete）**仅适用于公共会话消息**
- 管理员**不得读取消息内容**，只能通过接口删除
- 不得作用于以下私域消息：
  - Agent 私域消息（`sender_type=AGENT` 且 `visibility=PRIVATE`）
  - Memory 私域关联消息
  - Scene 私有提交（`scene_private_submission`）
- 删除私域消息需通过对应的专属接口（Memory DELETE、Scene 清理）

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `message_id` | uuid | 消息ID |

**请求体**（可选）：
```json
{
  "reason": "发送错误",
  "hard_delete": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reason` | string | 否 | 删除原因（审计用） |
| `hard_delete` | bool | 否 | 是否硬删除（默认 false，仅管理员可设为 true） |

**响应**：204 No Content

**删除行为**：
- **软删除**（默认）：设置 `deleted_at` 时间戳，消息对发送者和管理员可见"已删除"
- **硬删除**（仅管理员，仅公共会话）：物理删除记录，不可恢复
  - ✅ 可作用于：`privacy_level=PUBLIC` 的会话消息
  - ❌ 不可作用于：`privacy_level=PRIVATE` 的会话消息
  - ❌ 不可作用于：Agent 私域消息
  - ❌ 不可作用于：Scene 私有提交
- **撤回限制**：发送后 15 分钟内可撤回（由发送者调用）

**隐私约束**：
- 删除操作记录审计日志（包含 reason，但不包含消息内容）
- 即使软删除，消息内容仍在数据库中，需额外权限才能查看
- 硬删除不可逆，需谨慎操作
- 管理员执行硬删除时，仅标记删除状态，不返回消息内容

**错误码**：
- `MESSAGE_NOT_FOUND` - 消息不存在
- `MESSAGE_PERMISSION_DENIED` - 无权限删除
- `MESSAGE_CANNOT_RECALL` - 超过撤回时限（15 分钟）
- `MESSAGE_HARD_DELETE_DENIED` - 无权限硬删除
- `MESSAGE_HARD_DELETE_PRIVATE_SESSION` - 私密会话消息不支持硬删除
- `MESSAGE_HARD_DELETE_AGENT_DOMAIN` - Agent 私域消息不支持硬删除
- `MESSAGE_HARD_DELETE_SCENE_PRIVATE` - Scene 私有提交不支持硬删除

---

### 2.5 Agent（智能体）

#### GET /api/v1/agents/me

**端点编号**：EP-AGENT-033
**描述**：获取我的智能体

**权限**：本人

**响应**：200 OK

---

#### PATCH /api/v1/agents/me

**端点编号**：EP-AGENT-034
**描述**：更新智能体配置

**权限**：本人

**请求体**：
```json
{
  "name": "...",
  "autonomy_level": "L1"
}
```

**响应**：200 OK

---

#### POST /api/v1/agents/me/chat

**端点编号**：EP-AGENT-035
**描述**：与我的智能体对话

**权限**：本人

**授权等级要求**：
- **L0**：❌ 禁止使用此接口
- **L1**：✅ 允许，仅返回建议
- **L2**：✅ 允许，可提交结构化偏好
- **L3**：✅ 允许（MVP 不开放）
- **L4**：✅ 允许（MVP 不开放）

**Agent 所有权**：
- Agent 属于用户本人，不属于平台或管理员
- 管理员无法通过此接口读取或操作他人 Agent 的对话
- 请求必须包含当前用户的 `agent_id`，不得跨用户访问

**请求体**：
```json
{
  "message": "帮我规划这周的聚餐",
  "message_type": "TEXT",
  "context": {
    "scene_key": "meal_planning",
    "conversation_id": "uuid"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | string | 是 | 用户消息内容 |
| `message_type` | string | 否 | 消息类型：`TEXT`/`IMAGE`（默认 `TEXT`） |
| `context` | object | 否 | 上下文信息（场景、会话等） |
| `context.scene_key` | string | 否 | 场景标识符 |
| `context.conversation_id` | uuid | 否 | 关联会话ID |

**响应**：200 OK

```json
{
  "run_id": "uuid",
  "agent_id": "uuid",
  "autonomy_level": "L1",
  "response": {
    "type": "TEXT",
    "content": "根据你的饮食偏好，我推荐以下餐厅..."
  },
  "run_summary": {
    "status": "completed",
    "duration_ms": 1250,
    "tools_used": 0
  },
  "privacy_level": "P1"
}
```

**说明**：
- ✅ `run_summary`：返回脱敏后的执行摘要（仅状态、时长、工具使用数）
- ❌ `trace`：不返回模型名、Token 用量、推理过程、延迟等敏感信息
- ❌ 完整 trace 仅记录在审计日志，不暴露给用户

**元数据保存与暴露规则**：
| 字段 | 可保存 | 可暴露给用户 | 可暴露给管理员 | 说明 |
|------|--------|------------|--------------|------|
| 用户消息内容 | ✅ | ✅ | ❌ | 用户对话内容 |
| Agent 回复内容 | ✅ | ✅ | ❌ | Agent 响应内容 |
| Model 调用 ID | ✅ | ❌ | ❌ | 仅审计日志 |
| 逻辑模型名称 | ✅ | ❌ | ❌ | 仅审计日志 |
| Token 用量 | ✅ | ❌ | ❌ | 仅审计日志 |
| 延迟 | ✅ | ❌ | ❌ | 仅审计日志 |
| 状态 | ✅ | ❌ | ❌ | 仅审计日志 |
| **执行摘要（run_summary）** | ✅ | ✅（脱敏） | ❌ | 仅状态、时长、工具数 |
| **完整 Prompt** | ✅（加密） | ❌ | ❌ | 加密存储，不暴露 |
| **完整模型响应** | ✅（加密） | ❌ | ❌ | 加密存储，不暴露 |
| **推理过程（reasoning）** | ✅（加密） | ❌ | ❌ | 加密存储，不暴露 |
| **Tool Call 详情** | ✅（加密） | ❌ | ❌ | 加密存储，不暴露 |

**隐私约束**：
- ❌ 私有偏好不能通过此接口发送（必须使用 Scene API）
- ❌ 响应中不暴露模型名、Token 用量、推理过程、延迟等敏感信息
- ✅ 仅返回脱敏后的 `run_summary`（状态、时长、工具使用数）
- ✅ 完整 trace 记录在审计日志，不返回给用户
- ✅ Agent Run 元数据保留 30 天（PRIVACY_BASELINE.md）
- ❌ 管理员无法读取用户与 Agent 的对话内容
- ❌ 模型厂商无法获取用户原始消息

**与 Model Gateway API 职责边界**：
- 此接口处理用户对话上下文、权限检查和响应格式化
- `/internal/v1/model/chat` 仅处理模型调用（内部接口）
- Agent Service 调用 Model Gateway，但用户不直接调用

**错误码**：
- `AGENT_NOT_FOUND` - Agent 不存在
- `AGENT_PERMISSION_DENIED` - 无权限使用此 Agent
- `AGENT_INVALID_AUTONOMY_LEVEL` - 授权等级不足
- `AGENT_MODEL_UNAVAILABLE` - 模型服务不可用
- `AGENT_CHAT_DISABLED` - Agent 聊天功能已禁用

---

#### GET /api/v1/agents/me/permissions

**端点编号**：EP-AGENT-036
**描述**：查询我的智能体的授权设置和限制

**权限**：本人

**响应**：200 OK

```json
{
  "agent_id": "uuid",
  "autonomy_level": "L1",
  "permissions": [
    {
      "scene_key": "meal_planning",
      "autonomy_level": "L2",
      "allowed_memory_categories": ["FOOD_PREFERENCE", "BUDGET"],
      "allowed_actions": ["submit_preference", "rate_candidate"],
      "expires_at": "2026-07-21T00:00:00+09:00",
      "granted_at": "2026-07-14T10:30:00Z",
      "granted_by": "user"
    },
    {
      "scene_key": "class_discussion",
      "autonomy_level": "L1",
      "allowed_memory_categories": [],
      "allowed_actions": ["answer_question"],
      "expires_at": null,
      "granted_at": "2026-07-10T08:00:00Z",
      "granted_by": "user"
    }
  ],
  "global_constraints": {
    "max_autonomy_level": "L2",
    "require_user_confirmation": ["final_vote", "payment", "registration"],
    "cannot_access": ["P3_data", "private_submissions"]
  }
}
```

**权限字段说明**：

| 字段 | 说明 |
|------|------|
| `autonomy_level` | 当前全局授权等级（L0-L4） |
| `scene_key` | 场景标识符 |
| `autonomy_level` | 该场景的授权等级 |
| `allowed_memory_categories` | 可访问的记忆分类 |
| `allowed_actions` | 可执行的动作列表 |
| `expires_at` | 授权过期时间（null 表示永不过期） |
| `granted_at` | 授权授予时间 |
| `granted_by` | 授权来源：`user`/`system`/`organization` |
| `max_autonomy_level` | 全局最高授权等级 |
| `require_user_confirmation` | 必须用户确认的动作列表 |
| `cannot_access` | 禁止访问的资源列表 |

**隐私约束**：
- 仅返回当前用户的 Agent 权限
- 不返回其他用户的权限信息
- 场景范围（`scene_key`）不暴露给非授权方

**错误码**：
- `AGENT_NOT_FOUND` - Agent 不存在
- `AGENT_PERMISSION_DENIED` - 无权限查看权限信息

---

#### PATCH /api/v1/agents/me/permissions

**端点编号**：EP-AGENT-037
**描述**：修改我的智能体的授权设置

**权限**：本人

**授权等级限制**：
- **L1** 用户只能授予 L1 或更低
- **L2** 用户可以授予 L2，需明确场景授权
- **L3/L4** 不允许通过 API 授权（MVP 不开放）

**请求体**：
```json
{
  "action": "grant",
  "scene_key": "meal_planning",
  "autonomy_level": "L2",
  "allowed_memory_categories": ["FOOD_PREFERENCE"],
  "allowed_actions": ["submit_preference", "rate_candidate"],
  "expires_at": "2026-07-21T00:00:00+09:00"
}
```

或（撤销授权）：

```json
{
  "action": "revoke",
  "scene_key": "meal_planning"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | 是 | 操作：`grant`/`revoke`/`update` |
| `scene_key` | string | 是 | 场景标识符 |
| `autonomy_level` | string | 条件 | 授权等级（grant/update 时必填） |
| `allowed_memory_categories` | array | 否 | 可访问的记忆分类 |
| `allowed_actions` | array | 否 | 可执行的动作列表 |
| `expires_at` | timestamp | 否 | 授权过期时间 |

**响应**：200 OK

```json
{
  "success": true,
  "permission": {
    "scene_key": "meal_planning",
    "autonomy_level": "L2",
    "expires_at": "2026-07-21T00:00:00+09:00"
  }
}
```

**撤销后行为**：
- 新请求立即失效
- 已进行中的操作不影响（不影响 in-flight 请求）
- 场景结束后删除相关授权记录
- 审计日志记录撤销原因

**过期时间规则**：
- `expires_at` 为 null 表示永不过期
- 过期后自动降级到 L1
- 过期前可续期

**场景范围**：
- 授权按场景（`scene_key`）独立管理
- 不同场景的授权等级互不影响
- 场景结束立即删除临时授权

**错误码**：
- `AGENT_NOT_FOUND` - Agent 不存在
- `AGENT_PERMISSION_DENIED` - 无权限修改
- `AGENT_INVALID_AUTONOMY_LEVEL` - 无效的授权等级
- `AGENT_SCENE_NOT_FOUND` - 场景不存在
- `AGENT_PERMISSION_EXPIRED` - 授权已过期

---

#### GET /api/v1/agents/me/runs

**端点编号**：EP-AGENT-038
**描述**：查询我的智能体的执行历史

**权限**：本人

**Agent 所有权**：
- 仅返回当前用户的 Agent 执行历史
- 管理员无法读取用户 Agent 的运行详情
- 按用户隔离，不跨用户查询

**请求参数**：
```
?page=1&page_size=20&status={RUNNING|COMPLETED|FAILED|CANCELLED}&started_after={timestamp}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | int | 否 | 页码（默认 1） |
| `page_size` | int | 否 | 每页数量（默认 20，最大 100） |
| `status` | string | 否 | 状态过滤 |
| `started_after` | timestamp | 否 | 开始时间过滤 |

**响应**：200 OK

```json
{
  "items": [
    {
      "run_id": "uuid",
      "agent_id": "uuid",
      "status": "COMPLETED",
      "started_at": "2026-07-14T10:30:00Z",
      "completed_at": "2026-07-14T10:30:02Z",
      "scene_key": "meal_planning",
      "actions_taken": [
        "submit_preference",
        "rate_candidate"
      ],
      "result_summary": {
        "candidates_evaluated": 5,
        "final_ranking": 3
      },
      "run_summary": {
        "status": "completed",
        "duration_ms": 1250,
        "tools_used": 0
      },
      "failure_reason": null
    },
    {
      "run_id": "uuid",
      "agent_id": "uuid",
      "status": "FAILED",
      "started_at": "2026-07-14T10:30:00Z",
      "completed_at": "2026-07-14T10:30:01Z",
      "scene_key": null,
      "actions_taken": [],
      "result_summary": null,
      "run_summary": {
        "status": "failed",
        "duration_ms": 1000,
        "tools_used": 0
      },
      "failure_reason": "PRIVACY_CONSENT_REVOKED"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 15
}
```

**隐私约束**：
- ❌ **不返回模型名**（model）
- ❌ **不返回 token 用量**（prompt/completion tokens）
- ❌ **不返回延迟**（latency_ms）
- ❌ **不返回推理过程**（reasoning_summary）
- ❌ **不返回完整 trace**
- ✅ **仅返回脱敏后的 run_summary**：状态、时长、工具使用数
- ✅ **完整 trace 仅进入受控审计日志**，用户和管理员默认不可见
- ✅ **审计日志保留 30 天**（PRIVACY_BASELINE.md）

**运行状态**：
| 状态 | 说明 |
|------|------|
| `RUNNING` | 正在执行 |
| `COMPLETED` | 成功完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |

**失败原因**：
| 失败原因 | 说明 |
|---------|------|
| `PRIVACY_CONSENT_REVOKED` | 隐私授权被撤销（隐私失败关闭） |
| `MODEL_UNAVAILABLE` | 模型服务不可用 |
| `TIMEOUT` | 执行超时 |
| `INVALID_INPUT` | 输入无效 |
| `INTERNAL_ERROR` | 内部错误 |
| `USER_CANCELLED` | 用户主动取消 |

**隐私失败关闭规则**：
- ✅ **PRIVACY_CONSENT_REVOKED**：授权被撤销时，立即停止执行
- ✅ **场景结束后删除**：临时数据（trace、中间结果）立即删除
- ✅ **失败记录**：仅保留失败原因和时间戳，不保留敏感内容
- ❌ **不记录完整 Prompt/响应**：即使失败也不记录
- ✅ **Agent Run 元数据保留**：30 天（PRIVACY_BASELINE.md）

**元数据暴露规则**：
- ✅ **暴露给用户**：状态、时间戳、场景、动作列表、结果摘要
- ❌ **不暴露**：完整 trace、完整 Prompt、完整模型响应
- ❌ **管理员不可见**：用户 Agent 的运行详情对管理员不可见

**与 Memory API 职责边界**：
- **Agent Runs**：记录 Agent 的执行历史（动作、状态、结果）
- **Memory API**：管理用户的记忆项（FOOD_PREFERENCE、BUDGET 等）
- Agent 执行后产生的记忆通过 Memory Service 写入
- 两者通过 `agent_id` 和 `memory_id` 关联

**与 Model Gateway API 职责边界**：
- **Agent Service**：管理 Agent 生命周期、权限、执行逻辑
- **Model Gateway**：纯模型调用路由（内部接口）
- Agent 通过 Model Gateway 调用模型，但不暴露 Model Gateway 细节给用户

**错误码**：
- `AGENT_NOT_FOUND` - Agent 不存在
- `AGENT_PERMISSION_DENIED` - 无权限查看执行历史
- `AGENT_RUN_INVALID_STATUS` - 无效的状态过滤值

---

### 2.6 Memory（记忆）

**范围说明**：当前 Memory API 版本不包含 `share`/`revoke` 端点。记忆的授权访问通过以下方式实现：
- ✅ **Agent permissions API**：通过 `POST /api/v1/agents/me/permissions` 控制 Agent 对特定记忆分类的访问权限
- ✅ **Scene consent API**：通过 `POST /api/v1/scene-instances/{scene_instance_id}/consent` 控制场景对记忆的临时授权
- ⚠️ **P1 阶段评估**：将在 P1 阶段评估是否需要独立的记忆共享接口

#### GET /api/v1/memories

**端点编号**：EP-MEM-039
**描述**：获取记忆列表

**权限**：本人

**查询参数**：
```
?category=FOOD_PREFERENCE&page=1&page_size=20
```

**响应**：200 OK

---

#### POST /api/v1/memories

**端点编号**：EP-MEM-040
**描述**：创建记忆

**权限**：本人

**响应**：201 Created

---

#### DELETE /api/v1/memories/{memory_id}

**端点编号**：EP-MEM-043
**描述**：删除记忆

**权限**：所有者

**响应**：204 No Content

**删除影响**：
- 删除后，Agent 无法再访问此记忆
- 已关联的场景实例不受影响（场景结果保留）
- 会话历史不受影响
- 软删除：设置 `deleted_at`，可恢复
- 硬删除：物理删除，不可恢复（需额外权限）

**错误码**：
- `MEMORY_NOT_FOUND` - 记忆不存在
- `MEMORY_PERMISSION_DENIED` - 无权限删除
- `MEMORY_IN_USE` - 记忆正在被场景使用（需先结束场景）

---

#### GET /api/v1/memories/{memory_id}

**端点编号**：EP-MEM-041
**描述**：获取记忆详情

**权限**：所有者

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `memory_id` | uuid | 记忆ID |

**响应**：200 OK

```json
{
  "id": "uuid",
  "owner_user_id": "uuid",
  "agent_id": null,
  "category": "FOOD_PREFERENCE",
  "sensitivity_level": "P2",
  "visibility": "PRIVATE",
  "source": "user_input",
  "confidence": 0.95,
  "expires_at": null,
  "created_at": "2026-07-14T10:30:00Z",
  "updated_at": "2026-07-14T10:30:00Z",
  "deleted_at": null,
  "purpose": "聚餐偏好收集",
  "consent_id": "uuid",
  "retention_policy": "permanent"
}
```

**记忆字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uuid | 记忆ID |
| `owner_user_id` | uuid | 所有者用户ID |
| `agent_id` | uuid | 关联智能体ID（可选） |
| `category` | string | 记忆分类（FOOD_PREFERENCE/BUDGET/...） |
| `sensitivity_level` | string | 敏感级别（P1/P2/P3） |
| `visibility` | string | 可见性（PUBLIC/INTERNAL/PRIVATE） |
| `source` | string | 来源（user_input/agent_extracted/scene_result） |
| `confidence` | float | 置信度（0.0-1.0） |
| `expires_at` | timestamp | 过期时间（null 表示永不过期） |
| `purpose` | string | 创建目的 |
| `consent_id` | uuid | 关联授权记录ID |
| `retention_policy` | string | 保留策略（permanent/ttl/scene_end） |

**记忆类型区分**：

| 类型 | 说明 | 保留策略 | 示例 |
|------|------|---------|------|
| **短期临时记忆** | 场景期间使用，场景结束后删除 | `scene_end` | 私有提交、偏好胶囊、私有评价 |
| **长期记忆** | 用户主动保存，长期保留 | `permanent` 或 `ttl` | 饮食偏好、预算、个人习惯 |

**隐私约束**：
- ❌ 不返回加密内容（`content_encrypted`）
- ✅ 返回元数据（分类、可见性、置信度等）
- ❌ 其他用户无法读取
- ❌ 管理员无法读取记忆内容
- ✅ 审计日志记录访问

**错误码**：
- `MEMORY_NOT_FOUND` - 记忆不存在
- `MEMORY_PERMISSION_DENIED` - 无权限查看
- `MEMORY_CONTENT_ENCRYPTED` - 内容已加密，需特殊权限

---

#### PATCH /api/v1/memories/{memory_id}

**端点编号**：EP-MEM-042
**描述**：更新记忆元数据

**权限**：所有者

**可更新字段**：
- `category` - 记忆分类
- `visibility` - 可见性
- `confidence` - 置信度
- `expires_at` - 过期时间
- `purpose` - 创建目的

**不可更新字段**：
- ❌ `owner_user_id` - 所有者不可变更
- ❌ `content_encrypted` - 内容需通过重新创建更新
- ❌ `created_at` - 创建时间不可变更

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `memory_id` | uuid | 记忆ID |

**请求体**：
```json
{
  "visibility": "INTERNAL",
  "confidence": 0.85,
  "expires_at": "2027-07-14T10:30:00Z"
}
```

**响应**：200 OK

```json
{
  "id": "uuid",
  "visibility": "INTERNAL",
  "confidence": 0.85,
  "expires_at": "2027-07-14T10:30:00Z",
  "updated_at": "2026-07-14T10:30:00Z"
}
```

**更新影响**：
- ✅ **Agent**：更新后，Agent 下次执行时将使用新元数据
- ✅ **Scene**：已关联的场景实例不受影响（历史数据保留）
- ✅ **Conversation**：会话历史不受影响
- ⚠️ **Consent**：如果 `category` 变更，需重新获取授权

**隐私约束**：
- 更新操作记录审计日志
- 不记录更新前后的具体内容
- 仅记录字段变更和时间戳

**错误码**：
- `MEMORY_NOT_FOUND` - 记忆不存在
- `MEMORY_PERMISSION_DENIED` - 无权限更新
- `MEMORY_INVALID_FIELD` - 试图更新不可变字段
- `MEMORY_CONSENT_REQUIRED` - 更新敏感分类需要重新授权

---

#### GET /api/v1/memories/access-log

**端点编号**：EP-MEM-044
**描述**：查询记忆的访问记录

**权限**：所有者

**访问日志记录内容**：

| 字段 | 说明 | 示例 |
|------|------|------|
| `access_id` | 访问ID | `uuid` |
| `memory_id` | 记忆ID | `uuid` |
| `accessor_type` | 访问者类型 | `USER`/`AGENT`/`SYSTEM` |
| `accessor_id` | 访问者ID | `uuid` |
| `accessor_name` | 访问者名称 | `张三`/`我的智能体` |
| `purpose` | 访问目的 | `meal_planning`/`scene_execution` |
| `action` | 操作类型 | `read`/`update`/`delete`/`export` |
| `result` | 结果 | `success`/`denied`/`error` |
| `failure_reason` | 失败原因（可选） | `MEMORY_PERMISSION_DENIED` |
| `ip_address` | IP 地址（脱敏） | `192.168.xxx.xxx` |
| `user_agent` | User-Agent（可选） | `Mozilla/5.0...` |
| `timestamp` | 时间戳 | `2026-07-14T10:30:00Z` |

**请求参数**：
```
?memory_id={uuid}&page=1&page_size=20&action={read|update|delete|export}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `memory_id` | uuid | 否 | 记忆ID（默认返回所有） |
| `action` | string | 否 | 操作类型过滤 |
| `page` | int | 否 | 页码（默认 1） |
| `page_size` | int | 否 | 每页数量（默认 20，最大 100） |

**响应**：200 OK

```json
{
  "items": [
    {
      "access_id": "uuid",
      "memory_id": "uuid",
      "accessor_type": "AGENT",
      "accessor_id": "uuid",
      "accessor_name": "我的智能体",
      "purpose": "meal_planning",
      "action": "read",
      "result": "success",
      "failure_reason": null,
      "ip_address": "192.168.xxx.xxx",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2026-07-14T10:30:00Z"
    },
    {
      "access_id": "uuid",
      "memory_id": "uuid",
      "accessor_type": "USER",
      "accessor_id": "uuid",
      "accessor_name": "张三",
      "purpose": "manual_review",
      "action": "read",
      "result": "denied",
      "failure_reason": "MEMORY_PERMISSION_DENIED",
      "ip_address": "192.168.xxx.xxx",
      "user_agent": null,
      "timestamp": "2026-07-14T10:25:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 15
}
```

**访问记录规则**：
- ✅ **所有访问都记录**：成功、失败、拒绝都记录
- ✅ **访问者**：记录类型和ID（用户/智能体/系统）
- ✅ **访问目的**：记录场景或操作目的
- ✅ **时间和结果**：记录时间戳和操作结果
- ✅ **失败原因**：拒绝时记录原因
- ✅ **IP 脱敏**：仅记录前3段（如 `192.168.xxx.xxx`）
- ❌ **不记录记忆内容**：仅记录访问元数据

**隐私约束**：
- 仅返回当前用户的所有记忆访问记录
- 不返回其他用户的访问记录
- 保留 90 天后自动清理（ADR-005）

**错误码**：
- `MEMORY_ACCESS_INVALID_FILTER` - 无效的过滤参数
- `MEMORY_ACCESS_DENIED` - 无权限查看访问记录

---

#### POST /api/v1/memories/export

**端点编号**：EP-MEM-045
**描述**：导出记忆数据

**权限**：所有者

**导出范围**：
- ✅ **包含**：当前用户的所有记忆元数据
- ✅ **包含**：记忆分类、可见性、置信度、创建时间
- ❌ **不包含**：加密内容（`content_encrypted`）
- ❌ **不包含**：其他用户的数据
- ❌ **不包含**：私有提交（PrivateSceneSubmission）
- ❌ **不包含**：场景临时数据

**脱敏规则**：
| 字段 | 脱敏规则 |
|------|---------|
| `content_encrypted` | ❌ 不导出（需单独请求解密） |
| `consent_id` | ✅ 导出（哈希处理） |
| `purpose` | ✅ 导出（去除敏感词） |
| `source` | ✅ 导出 |
| `visibility` | ✅ 导出 |

**用户确认要求**：
1. ✅ **导出前二次确认**：返回导出摘要，用户需明确确认
2. ✅ **导出范围说明**：明确告知将导出哪些数据
3. ✅ **审计日志**：记录导出操作（时间、IP、导出数量）
4. ✅ **导出文件水印**：包含用户ID和时间戳

**请求体**：
```json
{
  "categories": ["FOOD_PREFERENCE", "BUDGET"],
  "include_deleted": false,
  "format": "json",
  "confirm": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `categories` | array | 否 | 导出分类（默认全部） |
| `include_deleted` | bool | 否 | 是否包含已删除（默认 false） |
| `format` | string | 否 | 格式：`json`/`csv`（默认 `json`） |
| `confirm` | bool | 是 | 用户确认（必须为 true） |

**响应**：200 OK（下载文件）

```json
{
  "export_id": "uuid",
  "download_url": "https://...",
  "expires_at": "2026-07-14T12:30:00Z",
  "total_count": 150,
  "categories": ["FOOD_PREFERENCE", "BUDGET"],
  "generated_at": "2026-07-14T10:30:00Z"
}
```

**导出文件格式**（JSON）：
```json
{
  "export_metadata": {
    "user_id": "uuid",
    "generated_at": "2026-07-14T10:30:00Z",
    "total_count": 150,
    "categories": ["FOOD_PREFERENCE", "BUDGET"]
  },
  "memories": [
    {
      "id": "uuid",
      "category": "FOOD_PREFERENCE",
      "sensitivity_level": "P2",
      "visibility": "PRIVATE",
      "source": "user_input",
      "confidence": 0.95,
      "created_at": "2026-07-14T10:30:00Z",
      "updated_at": "2026-07-14T10:30:00Z"
    }
  ]
}
```

**隐私约束**：
- ❌ 不导出加密内容
- ❌ 不导出其他用户的数据
- ❌ 不导出私有提交
- ✅ 审计日志记录导出操作
- ✅ 导出文件 1 小时后自动删除

**与跨模块影响**：
- **Agent**：导出不影响 Agent 运行
- **Scene**：导出不影响场景结果
- **Conversation**：导出不影响会话历史

**错误码**：
- `MEMORY_EXPORT_INVALID_FORMAT` - 不支持的格式
- `MEMORY_EXPORT_CONFIRMATION_REQUIRED` - 需要用户确认
- `MEMORY_EXPORT_TOO_LARGE` - 导出数据过大（超过 10MB）
- `MEMORY_EXPORT_RATE_LIMITED` - 导出频率限制（每小时 3 次）

---

### 2.7 Scene（场景）

**状态机**：[SCENE_STATE_MACHINE.md](../architecture/SCENE_STATE_MACHINE.md) 定义完整状态流转

**关键概念边界**：

| 概念 | 定义 | 说明 |
|------|------|------|
| **Scene Definition（场景定义）** | 场景模板 | 如 `meal_planning`，定义场景类型和配置 |
| **Scene Instance（场景实例）** | 具体场景执行 | 由创建者发起，有独立状态流转 |
| **Scene Participant（场景参与者）** | 参与者 | 可以是用户或智能体，必须授权后才能提交 |
| **Private Preference（私有偏好）** | 用户私有提交 | 通过 `private-submission` 提交，不进入消息表 |
| **Preference Capsule（偏好胶囊）** | 偏好聚合 | 系统生成的去标识化偏好集合 |
| **Candidate（候选方案）** | 候选结果 | 基于偏好胶囊生成的方案列表 |
| **Vote（投票）** | 用户投票 | 参与者在候选方案上的选择 |
| **Final Decision（最终决定）** | 最终确认 | 群主或创建者确认的最终结果 |

**隐私原则**：
- ❌ **私有偏好不进入 Conversation**：不通过消息接口保存，不进入群聊
- ❌ **私有偏好不暴露给 Admin**：管理员页面无私有内容入口
- ❌ **私有偏好不跨场景泄露**：胶囊去标识化，无法追溯到个人
- ✅ **临时数据自动清理**：场景结束后 P4 数据立即清理
- ✅ **长期记忆二次确认**：写入前必须用户显式确认
- ✅ **隐私失败时关闭执行**：不降级公开处理

**状态-API 映射**：

| 状态 | 允许调用的 API | 发起者 |
|------|--------------|--------|
| `DRAFT` | POST /api/v1/scene-instances（创建）、POST /api/v1/scene-instances/{scene_instance_id}/participants | 创建者 |
| `WAITING_FOR_PARTICIPANTS` | POST /api/v1/scene-instances/{scene_instance_id}/participants、POST /api/v1/scene-instances/{scene_instance_id}/consent | 创建者/参与者 |
| `WAITING_FOR_CONSENT` | POST /api/v1/scene-instances/{scene_instance_id}/consent | 参与者 |
| `WAITING_FOR_PRIVATE_INPUT` | POST /api/v1/scene-instances/{scene_instance_id}/private-submission、POST /api/v1/scene-instances/{scene_instance_id}/start | 参与者/创建者 |
| `PROCESSING` | GET /api/v1/scene-instances/{scene_instance_id}（查看状态） | 所有参与者 |
| `CANDIDATES_READY` | POST /api/v1/scene-instances/{scene_instance_id}/start（开始投票）、GET /api/v1/scene-instances/{scene_instance_id}/candidates | 创建者/参与者 |
| `VOTING` | POST /api/v1/scene-instances/{scene_instance_id}/vote、GET /api/v1/scene-instances/{scene_instance_id}/candidates | 参与者 |
| `CONFIRMING` | POST /api/v1/scene-instances/{scene_instance_id}/confirm、GET /api/v1/scene-instances/{scene_instance_id}/candidates | 群主/创建者 |
| `COMPLETED` | GET /api/v1/scene-instances/{scene_instance_id}（查看结果） | 所有参与者 |
| `CANCELLED` | GET /api/v1/scene-instances/{scene_instance_id}（查看状态） | 所有参与者 |
| `FAILED` | GET /api/v1/scene-instances/{scene_instance_id}（查看错误） | 所有参与者 |
| `EXPIRED` | GET /api/v1/scene-instances/{scene_instance_id}（查看状态） | 所有参与者 |

**场景结束后的临时数据清理**：

| 数据类型 | 清理时机 | 清理策略 | 保留内容 |
|---------|---------|---------|---------|
| **私有偏好** | COMPLETED/CANCELLED/FAILED/EXPIRED 后立即 | 物理删除 | 无 |
| **偏好胶囊** | COMPLETED/CANCELLED/FAILED/EXPIRED 后立即 | 物理删除 | 无 |
| **候选方案** | COMPLETED/CANCELLED/FAILED/EXPIRED 后立即 | 物理删除 | 仅保留选中结果（脱敏） |
| **投票记录** | COMPLETED/CANCELLED/FAILED/EXPIRED 后立即 | 物理删除 | 无 |
| **审计日志** | 永久 | 不清理 | 完整保留（结构化元数据） |
| **最终结果** | 永久 | 不清理 | 选中候选、确认时间、参与者 |

**长期记忆写入二次确认**：
- 在 `CONFIRMING` 阶段，创建者确认时可以选择 `write_to_long_term_memory`
- 如果为 `true`，系统调用 `POST /api/v1/memories` 写入记忆
- 写入内容：脱敏后的场景结果（如"选择了海底捞作为聚餐地点"）
- ❌ 不写入：私有偏好、投票详情、个人理由

---

#### GET /api/v1/scenes

**端点编号**：EP-SCENE-046
**描述**：获取场景定义列表

**权限**：已认证

**说明**：
- 返回系统支持的所有场景定义
- 包含 MVP 场景和"即将上线"场景
- "即将上线"场景标记为 `is_coming_soon=true`

**请求参数**：
```
?type=mvp&page=1&page_size=20
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 否 | 场景类型：`mvp`/`coming_soon`/`all`（默认 `all`） |
| `page` | int | 否 | 页码（默认 1） |
| `page_size` | int | 否 | 每页数量（默认 20，最大 100） |

**响应**：200 OK

```json
{
  "items": [
    {
      "scene_key": "meal_planning",
      "name": "宿舍聚餐协商",
      "description": "四名学生在不暴露私有偏好的前提下完成聚餐决策",
      "icon": "🍽️",
      "status": "available",
      "is_coming_soon": false,
      "min_participants": 2,
      "max_participants": 10,
      "estimated_duration_minutes": 30
    },
    {
      "scene_key": "class_discussion",
      "name": "课堂讨论",
      "description": "学生围绕课程主题进行结构化讨论",
      "icon": "📚",
      "status": "coming_soon",
      "is_coming_soon": true,
      "min_participants": 3,
      "max_participants": 50,
      "estimated_duration_minutes": 60
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 5
}
```

**错误码**：
- `SCENE_LIST_INVALID_TYPE` - 无效的场景类型过滤

---

#### GET /api/v1/scenes/{scene_key}

**端点编号**：EP-SCENE-047
**描述**：获取场景定义详情

**权限**：已认证

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_key` | string | 场景标识符（如 `meal_planning`） |

**响应**：200 OK

```json
{
  "scene_key": "meal_planning",
  "name": "宿舍聚餐协商",
  "description": "四名学生在不暴露私有偏好的前提下完成聚餐决策",
  "icon": "🍽️",
  "status": "available",
  "is_coming_soon": false,
  "config": {
    "min_participants": 2,
    "max_participants": 10,
    "estimated_duration_minutes": 30,
    "required_consent_level": "L2",
    "allow_private_submission": true,
    "supports_voting": true,
    "supports_long_term_memory": true
  },
  "participant_roles": [
    {
      "role": "creator",
      "label": "发起人",
      "permissions": ["publish", "cancel", "confirm"]
    },
    {
      "role": "participant",
      "label": "参与者",
      "permissions": ["consent", "submit", "vote"]
    }
  ],
  "workflow": [
    {
      "step": 1,
      "state": "WAITING_FOR_PARTICIPANTS",
      "label": "邀请参与者",
      "actor": "creator"
    },
    {
      "step": 2,
      "state": "WAITING_FOR_CONSENT",
      "label": "授权确认",
      "actor": "participant"
    },
    {
      "step": 3,
      "state": "WAITING_FOR_PRIVATE_INPUT",
      "label": "提交偏好",
      "actor": "participant"
    },
    {
      "step": 4,
      "state": "PROCESSING",
      "label": "生成候选",
      "actor": "system"
    },
    {
      "step": 5,
      "state": "VOTING",
      "label": "投票",
      "actor": "participant"
    },
    {
      "step": 6,
      "state": "CONFIRMING",
      "label": "确认结果",
      "actor": "creator"
    },
    {
      "step": 7,
      "state": "COMPLETED",
      "label": "完成",
      "actor": "system"
    }
  ]
}
```

**说明**：
- 场景定义只返回元数据，不返回任何用户私有数据
- `required_consent_level` 指示所需的最低授权等级（L1/L2/L3/L4）
- `allow_private_submission` 指示是否支持私有偏好提交

**错误码**：
- `SCENE_NOT_FOUND` - 场景定义不存在

---

#### POST /api/v1/scene-instances

**端点编号**：EP-SCENE-048
**描述**：创建场景实例

**权限**：已认证

**状态机起点**：`DRAFT`

**请求体**：
```json
{
  "scene_key": "meal_planning",
  "conversation_id": "uuid",
  "participant_user_ids": ["uuid1", "uuid2"],
  "public_context": {
    "date": "2026-07-18",
    "city": "广州"
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `scene_key` | string | 是 | 场景标识符（如 `meal_planning`） |
| `conversation_id` | uuid | 否 | 关联会话ID（可选） |
| `participant_user_ids` | array | 是 | 参与者用户ID列表 |
| `public_context` | object | 否 | 公共上下文（如日期、地点） |

**响应**：201 Created

```json
{
  "instance_id": "uuid",
  "scene_key": "meal_planning",
  "status": "DRAFT",
  "creator_user_id": "uuid",
  "participants": [
    {
      "user_id": "uuid",
      "role": "creator",
      "status": "invited"
    },
    {
      "user_id": "uuid",
      "role": "participant",
      "status": "invited"
    }
  ],
  "public_context": {
    "date": "2026-07-18",
    "city": "广州"
  },
  "created_at": "2026-07-14T10:30:00Z",
  "expires_at": "2026-07-21T10:30:00Z"
}
```

**创建后状态流转**：
- 初始状态：`DRAFT`
- 发起人调用 `POST /api/v1/scene-instances/{scene_instance_id}/participants` → `WAITING_FOR_PARTICIPANTS`
- 或发起人直接邀请参与者 → `WAITING_FOR_PARTICIPANTS`

**隐私约束**：
- 不创建任何私有偏好数据
- 只返回元数据（状态、参与者列表、上下文）

**错误码**：
- `SCENE_INSTANCE_CREATE_INVALID_SCENE_KEY` - 无效的场景标识符
- `SCENE_INSTANCE_CREATE_NO_PARTICIPANTS` - 至少需要 1 名参与者
- `SCENE_INSTANCE_CREATE_CONVERSATION_NOT_FOUND` - 关联会话不存在

---

#### GET /api/v1/scene-instances/{scene_instance_id}

**端点编号**：EP-SCENE-049
**描述**：获取场景实例详情

**权限**：
- 创建者：可查看完整信息
- 参与者：可查看基本信息（不含私有偏好）
- 其他用户：不可见

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**响应**：200 OK

```json
{
  "instance_id": "uuid",
  "scene_key": "meal_planning",
  "status": "VOTING",
  "creator_user_id": "uuid",
  "conversation_id": "uuid",
  "participants": [
    {
      "user_id": "uuid",
      "role": "creator",
      "consent_granted": true,
      "consent_level": "L2",
      "submission_status": "submitted",
      "submitted_at": "2026-07-14T10:35:00Z"
    },
    {
      "user_id": "uuid",
      "role": "participant",
      "consent_granted": true,
      "consent_level": "L2",
      "submission_status": "submitted",
      "submitted_at": "2026-07-14T10:36:00Z"
    }
  ],
  "public_context": {
    "date": "2026-07-18",
    "city": "广州"
  },
  "current_step": {
    "state": "VOTING",
    "label": "投票中",
    "started_at": "2026-07-14T10:40:00Z",
    "expires_at": "2026-07-15T10:40:00Z"
  },
  "candidates_count": 3,
  "votes_count": 2,
  "created_at": "2026-07-14T10:30:00Z",
  "updated_at": "2026-07-14T10:45:00Z"
}
```

**隐私约束**：
- ❌ 不返回私有偏好内容（`preferences` 字段）
- ❌ 不返回偏好胶囊（`capsule` 字段）
- ✅ 返回参与者提交状态（`submission_status`）和提交时间
- ✅ 返回投票计数（`votes_count`），但不返回谁投了什么
- ✅ 管理员只能查看结构化元数据

**可见性规则**：
| 字段 | 创建者 | 参与者 | 管理员 |
|------|--------|--------|--------|
| 场景状态 | ✅ | ✅ | ✅ |
| 参与者列表 | ✅ | ✅（他人） | ✅（无私有数据） |
| 提交状态 | ✅ | ✅（他人脱敏） | ❌ |
| 私有偏好 | ✅（自己） | ❌ | ❌ |
| 候选方案 | ✅ | ✅ | ❌ |
| 投票详情 | ✅ | ❌ | ❌ |

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_PERMISSION_DENIED` - 无权限查看

---

#### POST /api/v1/scene-instances/{scene_instance_id}/participants

**端点编号**：EP-SCENE-050
**描述**：向场景添加参与者

**权限**：创建者

**允许状态**：`DRAFT`、`WAITING_FOR_PARTICIPANTS`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**：
```json
{
  "user_ids": ["uuid1", "uuid2"],
  "send_invitation": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_ids` | array | 是 | 要添加的用户ID列表 |
| `send_invitation` | bool | 否 | 是否发送邀请通知（默认 true） |

**响应**：200 OK

```json
{
  "added": [
    {
      "user_id": "uuid",
      "role": "participant",
      "status": "invited",
      "invited_at": "2026-07-14T10:30:00Z"
    }
  ],
  "already_exists": [],
  "failed": []
}
```

**状态流转**：
- 添加参与者后，状态保持不变（`DRAFT` 或 `WAITING_FOR_PARTICIPANTS`）
- 当所有参与者都确认参与后，自动流转到 `WAITING_FOR_CONSENT`

**隐私约束**：
- 只返回参与者 ID 和状态，不返回任何私有数据

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_PERMISSION_DENIED` - 仅创建者可添加参与者
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态不允许添加参与者
- `SCENE_INSTANCE_PARTICIPANT_ALREADY_EXISTS` - 参与者已存在
- `SCENE_INSTANCE_PARTICIPANT_LIMIT_REACHED` - 参与者数量已达上限

---

#### POST /api/v1/scene-instances/{scene_instance_id}/private-submission

**端点编号**：EP-SCENE-051
**描述**：提交私有偏好 ⭐ 核心隐私接口

**权限**：参与者本人

**允许状态**：`WAITING_FOR_PRIVATE_INPUT`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**：
```json
{
  "preferences": {
    "budget_max": 100,
    "cuisines": ["日料", "粤菜"],
    "excluded_ingredients": ["香菜"],
    "distance_limit_km": 3,
    "notes": "希望安静一点"
  },
  "save_to_long_term_memory": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `preferences` | object | 是 | 私有偏好对象（场景特定结构） |
| `save_to_long_term_memory` | bool | 否 | 是否保存到长期记忆（默认 false） |

**响应**：202 Accepted

```json
{
  "submission_status": "ACCEPTED",
  "capsule_generated": true,
  "expires_at": "2026-07-14T00:00:00+09:00"
}
```

**状态流转**：
- 提交后，参与者状态更新为 `submitted`
- 当所有参与者都提交后，自动流转到 `PROCESSING`
- 如果超时未提交，自动流转到 `PROCESSING`（标记为 timeout）

**偏好胶囊生成**：
- ✅ 系统生成去标识化的偏好胶囊（preference capsule）
- ❌ 胶囊无法追溯到个人
- ✅ 胶囊用于生成候选方案，不进入消息表

**隐私控制**：
- ✅ **只接受自己的提交**：不能代他人提交
- ✅ **响应不回显原文**：不返回 `preferences` 内容
- ✅ **不进入消息表**：不在 Conversation 中保存
- ✅ **加密存储**：偏好数据加密存储，P4 临时数据
- ✅ **场景结束后清理**：临时数据立即清理
- ❌ **私有偏好不暴露给 Admin**：管理员无法查看
- ❌ **私有偏好不暴露给 Conversation**：不进入群聊

**与 Memory API 交互**：
- 如果 `save_to_long_term_memory=true`，调用 `POST /api/v1/memories`
- 保存为 `retention_policy=permanent` 或 `ttl`
- 保存前需用户显式确认

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_NOT_PARTICIPANT` - 非参与者无法提交
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态不允许提交
- `SCENE_INSTANCE_SUBMISSION_ALREADY_EXISTS` - 已提交过偏好
- `SCENE_INSTANCE_SUBMISSION_ENCRYPTION_FAILED` - 加密失败，拒绝执行

---

#### POST /api/v1/scene-instances/{scene_instance_id}/consent

**端点编号**：EP-SCENE-052
**描述**：授权场景（L2 授权）

**权限**：参与者本人

**允许状态**：`WAITING_FOR_CONSENT`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**：
```json
{
  "granted": true,
  "autonomy_level": "L2",
  "expires_at": "2026-07-14T00:00:00+09:00"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `granted` | bool | 是 | 是否授权（true=授权，false=拒绝） |
| `autonomy_level` | string | 否 | 授权等级（L1/L2/L3/L4，默认 L1） |
| `expires_at` | timestamp | 否 | 授权过期时间（null=永不过期） |

**响应**：200 OK

```json
{
  "consent_id": "uuid",
  "granted": true,
  "autonomy_level": "L2",
  "expires_at": "2026-07-21T00:00:00+09:00",
  "granted_at": "2026-07-14T10:30:00Z"
}
```

**状态流转**：
- 授权后，参与者状态更新为 `consented`
- 当所有参与者都授权后，自动流转到 `WAITING_FOR_PRIVATE_INPUT`
- 如果有参与者拒绝，场景进入 `CANCELLED` 状态

**授权等级说明**：
- **L1**：默认，仅查看
- **L2**：允许提交私有偏好、投票（MVP 最大授权）
- **L3/L4**：MVP 不开放

**隐私约束**：
- 授权记录加密存储
- 过期后自动降级到 L1
- 撤销授权立即生效（`PRIVACY_CONSENT_REVOKED`）

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_NOT_PARTICIPANT` - 非参与者无法授权
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态不允许授权
- `SCENE_INSTANCE_CONSENT_ALREADY_GRANTED` - 已授权过
- `SCENE_INSTANCE_CONSENT_EXPIRED` - 授权已过期

---
```json
{
  "granted": true,
  "autonomy_level": "L2",
  "expires_at": "2026-07-14T00:00:00+09:00"
}
```

**响应**：200 OK

---

#### POST /api/v1/scene-instances/{scene_instance_id}/start

**端点编号**：EP-SCENE-053
**描述**：开始处理（触发处理流程）

**权限**：创建者

**允许状态**：`WAITING_FOR_PRIVATE_INPUT`

**触发条件**：
- 所有参与者已提交偏好，或
- 达到超时时间（48 小时）

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**：无

**响应**：202 Accepted

```json
{
  "instance_id": "uuid",
  "status": "PROCESSING",
  "started_at": "2026-07-14T10:45:00Z",
  "estimated_completion": "2026-07-14T11:15:00Z"
}
```

**状态流转**：
- 调用后，状态从 `WAITING_FOR_PRIVATE_INPUT` → `PROCESSING`
- 系统开始处理私有偏好，生成候选方案
- 处理完成后，自动流转到 `CANDIDATES_READY`

**处理流程**：
1. 读取所有参与者的私有偏好（加密数据）
2. 生成去标识化的偏好胶囊
3. 调用模型或规则引擎生成候选方案
4. 保存候选方案到数据库
5. 状态更新为 `CANDIDATES_READY`

**隐私约束**：
- 处理过程中不暴露任何私有偏好
- 只返回状态和时间戳

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_PERMISSION_DENIED` - 仅创建者可启动
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态不允许启动
- `SCENE_INSTANCE_PENDING_SUBMISSIONS` - 还有参与者未提交（需强制启动）

---

#### GET /api/v1/scene-instances/{scene_instance_id}/candidates

**端点编号**：EP-SCENE-054
**描述**：获取候选方案列表

**权限**：参与者

**允许状态**：`CANDIDATES_READY`、`VOTING`、`CONFIRMING`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**响应**：200 OK

```json
{
  "candidates": [
    {
      "candidate_id": "uuid",
      "name": "海底捞（大学城店）",
      "description": "满足所有硬性限制，距离最近",
      "match_score": 0.95,
      "criteria_met": [
        "预算范围内",
        "符合所有饮食限制",
        "距离在 3km 内"
      ],
      "public_details": {
        "cuisine": "火锅",
        "avg_price_per_person": 85,
        "distance_km": 1.2,
        "address": "大学城大街 123 号",
        "dietary_restrictions_supported": ["不吃香菜", "清真"]
      },
      "aggregated_preferences_summary": {
        "budget_range": "60-100元",
        "preferred_cuisines": ["火锅", "粤菜"],
        "common_restrictions": ["不吃香菜"]
      }
    }
  ],
  "total": 3,
  "generated_at": "2026-07-14T10:50:00Z"
}
```

**候选方案生成**：
- ✅ 基于去标识化的偏好胶囊生成
- ✅ 不包含任何可追溯到个人的信息
- ✅ 满足所有硬性限制（硬约束）
- ✅ 提供聚合的偏好摘要（无个人标识）

**隐私约束**：
- ❌ 不返回私有偏好内容
- ❌ 不返回偏好胶囊
- ✅ 只返回聚合摘要（`aggregated_preferences_summary`）
- ✅ 候选方案详情去标识化

**可见性规则**：
| 字段 | 创建者 | 参与者 | 管理员 |
|------|--------|--------|--------|
| 候选列表 | ✅ | ✅ | ❌ |
| 候选详情 | ✅ | ✅ | ❌ |
| 聚合偏好摘要 | ✅ | ✅ | ❌ |
| 私有偏好 | ❌ | ❌ | ❌ |

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_NOT_PARTICIPANT` - 非参与者无法查看
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态无可用候选
- `SCENE_CANDIDATES_NOT_READY` - 候选方案尚未生成

---

#### POST /api/v1/scene-instances/{scene_instance_id}/vote

**端点编号**：EP-SCENE-055
**描述**：投票

**权限**：参与者

**允许状态**：`VOTING`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**：
```json
{
  "candidate_id": "uuid"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `candidate_id` | uuid | 是 | 候选方案ID |

**响应**：200 OK

```json
{
  "vote_id": "uuid",
  "candidate_id": "uuid",
  "voted_at": "2026-07-14T10:55:00Z",
  "total_votes": 3
}
```

**状态流转**：
- 投票后，参与者状态更新为 `voted`
- 当所有参与者都投票或超时后，自动流转到 `CONFIRMING`

**幂等性**：
- 使用 `Idempotency-Key` 支持重复投票
- 重复投票返回上次投票结果，不重复计数

**隐私约束**：
- ✅ 投票内容加密存储
- ❌ 不返回其他参与者的投票详情
- ✅ 只返回总票数（`total_votes`）

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_NOT_PARTICIPANT` - 非参与者无法投票
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态不允许投票
- `SCENE_VOTE_INVALID_CANDIDATE` - 无效的候选方案ID
- `SCENE_VOTE_ALREADY_VOTED` - 已投票过（除非使用幂等键）

---

#### POST /api/v1/scene-instances/{scene_instance_id}/confirm

**端点编号**：EP-SCENE-056
**描述**：确认最终结果

**权限**：群主或创建者

**允许状态**：`CONFIRMING`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**：
```json
{
  "selected_candidate_id": "uuid",
  "write_to_long_term_memory": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `selected_candidate_id` | uuid | 是 | 选中的候选方案ID |
| `write_to_long_term_memory` | bool | 否 | 是否写入长期记忆（需用户显式确认） |

**响应**：200 OK

```json
{
  "instance_id": "uuid",
  "status": "COMPLETED",
  "selected_candidate": {
    "candidate_id": "uuid",
    "name": "海底捞（大学城店）"
  },
  "confirmed_at": "2026-07-14T11:00:00Z",
  "memory_written": false
}
```

**状态流转**：
- 确认后，状态从 `CONFIRMING` → `COMPLETED`（终态）
- 触发临时数据清理流程
- 如果 `write_to_long_term_memory=true`，写入长期记忆

**长期记忆二次确认**：
- ✅ 写入前必须用户显式确认（`write_to_long_term_memory` 字段）
- ✅ 写入内容为脱敏后的结果（餐厅名称、理由）
- ❌ 不写入私有偏好、投票详情等敏感信息

**临时数据清理**：
- 场景结束后立即清理 P4 临时数据
- 包括：私有偏好、偏好胶囊、原始提交
- 保留：审计日志、最终结果、公开摘要

**隐私约束**：
- ❌ 确认操作不暴露私有偏好
- ✅ 最终结果去标识化
- ✅ 临时数据清理完成前，`COMPLETED` 状态不可撤销

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_PERMISSION_DENIED` - 仅群主/创建者可确认
- `SCENE_INSTANCE_INVALID_STATE` - 当前状态不允许确认
- `SCENE_CONFIRM_INVALID_CANDIDATE` - 无效的候选方案ID
- `SCENE_CONFIRM_MEMORY_WRITE_FAILED` - 长期记忆写入失败

---

#### POST /api/v1/scene-instances/{scene_instance_id}/cancel

**端点编号**：EP-SCENE-057
**描述**：取消场景

**权限**：群主或创建者

**允许状态**：非终态（`DRAFT`、`WAITING_FOR_PARTICIPANTS`、`WAITING_FOR_CONSENT`、`WAITING_FOR_PRIVATE_INPUT`、`PROCESSING`、`CANDIDATES_READY`、`VOTING`、`CONFIRMING`）

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `scene_instance_id` | uuid | 场景实例ID |

**请求体**（可选）：
```json
{
  "reason": "参与者不足"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `reason` | string | 否 | 取消原因（审计用） |

**响应**：204 No Content

**状态流转**：
- 取消后，状态 → `CANCELLED`（终态）
- 触发临时数据清理流程

**临时数据清理**：
- ✅ 立即清理 P4 临时数据（私有偏好、偏好胶囊、候选方案）
- ✅ 清理投票记录
- ✅ 保留审计日志（包含取消原因和时间戳）
- ✅ 保留最终结果（标记为 cancelled）

**隐私约束**：
- 取消操作不暴露任何私有偏好
- 审计日志记录取消原因，但不记录私有数据

**错误码**：
- `SCENE_INSTANCE_NOT_FOUND` - 场景实例不存在
- `SCENE_INSTANCE_PERMISSION_DENIED` - 仅群主/创建者可取消
- `SCENE_INSTANCE_INVALID_STATE` - 已处于终态，无法取消

---

### 2.8 Model Gateway（内部）

> **访问控制**：内部接口，仅服务间调用，不对外部用户开放
> **权限**：内部服务（Agent Service、Scene Service）通过服务间认证调用

**路由策略**（见 ADR-004）：
```
请求 → Model Gateway → 路由决策
  ├─ 检查隐私上下文（privacy_context）
  ├─ 检查节点健康
  ├─ 检查外部模型是否启用
  └─ 选择路由
    ├─ 本地边缘节点（敏感数据时优先）
    ├─ 外部模型 API（仅授权且启用时）
    ├─ Mock 模型（备用）
    └─ 规则引擎（最终降级）
```

**路由优先级**：
1. **本地边缘节点**（敏感数据时优先）
2. **外部模型 API**（仅授权且启用时）
3. **Mock 模型**（备用）
4. **规则引擎**（最终降级）

**关键原则**：
- ❌ **不能直接接收未经授权的原始私密数据**
- ✅ **所有请求必须携带 `privacy_context`**
- ✅ **敏感数据不路由到外部模型**
- ✅ **隐私失败时关闭执行，不降级公开处理**
- ✅ **降级策略不会绕过隐私限制**

#### POST /internal/v1/model/chat

**端点编号**：EP-MODEL-058
**描述**：调用模型进行对话（内部接口）

**权限**：内部服务（Agent Service、Scene Service）

**请求头**：
```
Authorization: Bearer <internal_service_token>
X-Service-Name: agent-service  # 或 scene-service
```

**privacy_context 字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `purpose` | string | 是 | 调用目的（如 `meal_planning`、`agent_chat`） |
| `data_classification` | string | 是 | 数据分类：`P0`/`P1`/`P2`/`P3`/`P4` |
| `retention` | string | 是 | 保留策略：`session`/`permanent`/`none` |
| `consent_scope` | string | 是 | 授权范围（如 `scene_instance:{id}`） |
| `allowed_outputs` | array | 是 | 允许的输出类型（如 `["TEXT", "STRUCTURED"]`） |
| `user_id` | uuid | 是 | 关联用户 ID |
| `scene_instance_id` | uuid | 否 | 关联场景实例 ID（可选） |

**隐私校验规则**：
- ✅ `data_classification = P4` → 禁止路由到外部模型，必须本地或 Mock
- ✅ `data_classification = P3` → 禁止路由到外部模型，必须本地加密
- ✅ `retention = none` → 不存储输入/输出
- ✅ `consent_scope` 必须与用户授权一致
- ❌ 缺少 `privacy_context` → 拒绝请求（`MISSING_PRIVACY_CONTEXT`）

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
      "role": "system",
      "content": "你是一个餐饮推荐助手。根据用户偏好胶囊生成候选餐厅列表。"
    },
    {
      "role": "user",
      "content": "基于以下去标识化偏好胶囊生成3个候选餐厅：预算中档、粤菜/日料、距离<3km、安静环境。"
    }
  ],
  "preference_capsule": {
    "budget_tier": "medium",
    "cuisine_preferences": ["粤菜", "日料"],
    "excluded_cuisines": [],
    "distance_limit_km": 3,
    "environment_preference": "quiet",
    "capsule_id": "uuid",
    "generated_at": "2026-07-14T10:35:00Z"
  },
  "model": "local-llama-7b",
  "temperature": 0.7,
  "max_tokens": 500,
  "response_format": {
    "type": "json_schema",
    "schema": {
      "type": "object",
      "properties": {
        "candidates": {
          "type": "array",
          "items": {
            "type": "object"
          }
        }
      }
    }
  }
}
```

**响应**：200 OK

```json
{
  "request_id": "uuid",
  "model": "local-llama-7b",
  "status": "completed",
  "response": {
    "type": "STRUCTURED",
    "content": {
      "candidates": [...]
    }
  },
  "metadata": {
    "prompt_tokens": 150,
    "completion_tokens": 80,
    "latency_ms": 1250,
    "provider": "local"
  }
}
```

**元数据记录**（不记录输入/输出内容）：
| 字段 | 说明 |
|------|------|
| `request_id` | 请求 ID |
| `model` | 模型名 |
| `prompt_tokens` | Prompt Token 数 |
| `completion_tokens` | 完成 Token 数 |
| `latency_ms` | 延迟（毫秒） |
| `provider` | 提供商（local/external/mock/rule） |
| `status` | 状态（completed/failed/timeout） |
| `input_hash` | 输入哈希（用于验证完整性） |
| `output_hash` | 输出哈希（用于验证完整性） |

**路由决策**：
- `data_classification = P4` → 仅本地节点或 Mock
- `data_classification = P3` → 仅本地节点（加密）
- `contains_sensitive_data = true` → 禁止外部
- `allow_external = false` → 外部不可用

**超时**：
- 默认超时：30 秒
- 可配置：`timeout` 字段（最大 300 秒）

**失败处理**：

| 失败类型 | 原因 | 处理策略 | 错误码 |
|---------|------|---------|--------|
| **隐私校验失败** | 缺少 privacy_context、数据分类不符 | 立即拒绝，不执行 | `PRIVACY_CONTEXT_MISSING`、`PRIVACY_CONTEXT_INVALID` |
| **模型不可用** | 节点健康检查失败 | 降级到 Mock/规则 | `MODEL_UNAVAILABLE` |
| **超时** | 超过 timeout 限制 | 降级到 Mock/规则（如果允许）或返回超时错误 | `TIMEOUT` |
| **输入验证失败** | 消息格式错误、参数超出范围 | 立即拒绝 | `INVALID_INPUT` |
| **内部错误** | 服务端错误 | 记录错误，返回 `INTERNAL_ERROR` |
| **外部供应商错误** | 第三方 API 返回错误 | 如果允许外部，返回错误；否则降级 | `EXTERNAL_PROVIDER_ERROR` |

**降级策略**：
1. **本地节点失败** → Mock 模型
2. **Mock 失败** → 规则引擎
3. **所有路径失败** → 返回错误，**不降级为公开**
4. **隐私能力不可降级**：只能降级为 Mock/规则，不能绕过隐私检查

**隐私约束**：
- ❌ **不记录原始 Prompt**：仅记录哈希
- ❌ **不记录完整响应**：仅记录哈希
- ❌ **敏感数据不路由到外部**：`data_classification >= P3` 时强制本地
- ❌ **P4 原始私密数据不得直接进入模型消息体**：必须使用去标识化的 preference capsule 或 structured constraints
- ✅ **P4 数据隔离**：原始偏好不进入 `messages.content`，仅通过 `preference_capsule` 传递去标识化摘要
- ✅ **审计元数据**：记录调用 ID、模型名、Token、延迟、状态
- ✅ **90 天保留**：审计日志保留 90 天（ADR-005）

**错误码**：
- `PRIVACY_CONTEXT_MISSING` - 缺少 privacy_context
- `PRIVACY_CONTEXT_INVALID` - privacy_context 字段无效
- `PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED` - 敏感数据禁止路由到外部
- `MODEL_UNAVAILABLE` - 模型服务不可用
- `MODEL_TIMEOUT` - 模型调用超时
- `MODEL_ROUTING_FAILED` - 路由失败
- `INVALID_INPUT` - 输入无效
- `INTERNAL_ERROR` - 内部错误
- `EXTERNAL_PROVIDER_ERROR` - 外部供应商错误

---

#### POST /internal/v1/model/embedding

**端点编号**：EP-MODEL-059
**描述**：生成文本 embedding 向量（内部接口）

**权限**：内部服务（Agent Service、Scene Service）

**请求头**：
```
Authorization: Bearer <internal_service_token>
X-Service-Name: agent-service
```

**privacy_context**：同 POST /internal/v1/model/chat

**请求体**：
```json
{
  "privacy_context": {
    "purpose": "memory_retrieval",
    "data_classification": "P2",
    "retention": "permanent",
    "consent_scope": "memory:uuid",
    "allowed_outputs": ["EMBEDDING"],
    "user_id": "uuid",
    "scene_instance_id": null
  },
  "text": "用户的原始记忆文本...",
  "model": "local-embedding-model",
  "dimension": 768
}
```

**响应**：200 OK

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

**元数据记录**：
| 字段 | 说明 |
|------|------|
| `request_id` | 请求 ID |
| `model` | 模型名 |
| `input_tokens` | 输入 Token 数 |
| `latency_ms` | 延迟（毫秒） |
| `provider` | 提供商 |
| `status` | 状态 |
| `text_hash` | 输入文本哈希 |

**隐私约束**：
- ❌ **不记录原始文本**：仅记录哈希
- ✅ **embedding 向量不可逆**：无法恢复原始文本
- ❌ **不暴露 embedding 给用户**：仅供向量检索使用

**错误码**：同 POST /internal/v1/model/chat

---
#### GET /internal/v1/model/health

**端点编号**：EP-MODEL-060
**描述**：检查模型服务健康状态（内部接口）

**权限**：内部服务

**响应**：200 OK

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

**响应内容**：
| 字段 | 说明 |
|------|------|
| `status` | 健康状态 |
| `models` | 模型列表 |
| `models[].name` | 模型名 |
| `models[].status` | 状态（`ready`/`unavailable`/`error`） |
| `models[].latency_ms` | 延迟 |
| `models[].last_checked` | 最后检查时间 |
| `timestamp` | 响应时间 |

**隐私约束**：
- ❌ **不返回密钥或 Token**：无敏感配置
- ❌ **不返回内部错误详情**：仅状态码
- ❌ **不返回用户数据**：纯健康检查
- ❌ **不返回历史调用记录**：无日志访问

**错误码**：
- `INTERNAL_ERROR` - 内部错误
- `SERVICE_UNAVAILABLE` - 服务不可用

---

### 2.9 Admin（管理）

> **访问控制**：仅管理员可访问
> **权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN（每个端点单独声明）

**隐私原则**：
- ❌ **管理员不能读取用户私有偏好**（P2）
- ❌ **管理员不能读取用户记忆正文**（P2/P3）
- ❌ **管理员不能读取智能体推理过程**（reasoning_summary）
- ❌ **管理员不能读取聊天消息明文**（P1/P2）
- ❌ **管理员不能读取私有提交内容**（P4）
- ❌ **管理员不能读取授权记录详情**（consent 内容）
- ✅ **管理员只能访问结构化元数据**
- ✅ **管理员只能查看脱敏的系统指标**
- ✅ **管理员只能查看结构化审计元数据**（无敏感内容）
- ✅ **心理支持独立域数据对管理员不可见**（P3）

**隐私过滤规则**：
1. 所有 Admin API 响应必须经过隐私过滤层
2. 移除字段：`preferences`、`budget`、`private_submission`、`memory_content`、`reasoning_summary`、`prompt`、`response`
3. 保留字段：`id`、`name`、`status`、`created_at`、`updated_at`、`metadata`（脱敏后）、`metrics`（聚合指标）

#### POST /api/v1/admin/nodes

**端点编号**：EP-ADMIN-061
**描述**：注册新的边缘计算节点

**权限**：SYSTEM_ADMIN（仅系统管理员可创建节点）

**请求头**：
```
Authorization: Bearer <admin_token>
Idempotency-Key: <uuid>  # 见 1.4
```

**请求体**：
```json
{
  "name": "edge-node-01",
  "endpoint": "http://192.168.1.100:8000",
  "capabilities": ["model_inference", "embedding"],
  "models_supported": ["local-llama-7b", "local-embedding-model"],
  "max_concurrent_requests": 50,
  "metadata": {
    "location": "campus-dorm-a",
    "gpu_type": "RTX-4090"
  }
}
```

**响应**：201 Created

```json
{
  "node_id": "uuid",
  "name": "edge-node-01",
  "endpoint": "http://192.168.1.100:8000",
  "status": "registering",
  "capabilities": ["model_inference", "embedding"],
  "created_at": "2026-07-14T12:00:00Z"
}
```

**隐私约束**：
- ✅ 可返回：节点 ID、名称、端点、状态、能力列表、配置元数据
- ❌ 不返回：密钥、Token、内部网络拓扑、用户访问记录

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足（非 SYSTEM_ADMIN）
- `NODE_ALREADY_EXISTS` - 节点已存在（Idempotency-Key 冲突）
- `INVALID_ENDPOINT` - 端点格式无效
- `INVALID_CAPABILITIES` - 能力列表无效

---
#### GET /api/v1/admin/nodes

**端点编号**：EP-ADMIN-062
**描述**：获取所有节点列表

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**请求头**：
```
Authorization: Bearer <admin_token>
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `status` | string | 否 | 过滤状态（`healthy`/`degraded`/`unhealthy`/`offline`） |
| `capability` | string | 否 | 按能力过滤 |
| `page` | int | 否 | 页码（默认 1） |
| `limit` | int | 否 | 每页数量（默认 20，最大 100） |

**响应**：200 OK

```json
{
  "nodes": [
    {
      "node_id": "uuid",
      "name": "edge-node-01",
      "status": "healthy",
      "capabilities": ["model_inference", "embedding"],
      "last_heartbeat": "2026-07-14T12:34:56Z",
      "created_at": "2026-07-14T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

**隐私约束**：
- ✅ 可返回：节点 ID、名称、状态、能力列表、最后心跳时间、创建时间
- ❌ 不返回：端点地址（除非授权）、密钥、内部指标、用户关联数据

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足
- `INVALID_PAGINATION` - 分页参数无效

---
#### GET /api/v1/admin/nodes/{node_id}

**端点编号**：EP-ADMIN-063
**描述**：获取单个节点的详细信息

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**请求头**：
```
Authorization: Bearer <admin_token>
```

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | uuid | 节点 ID |

**响应**：200 OK

```json
{
  "node_id": "uuid",
  "name": "edge-node-01",
  "endpoint": "http://192.168.1.100:8000",
  "status": "healthy",
  "capabilities": ["model_inference", "embedding"],
  "models_supported": ["local-llama-7b", "local-embedding-model"],
  "max_concurrent_requests": 50,
  "current_requests": 12,
  "uptime_seconds": 86400,
  "last_heartbeat": "2026-07-14T12:34:56Z",
  "created_at": "2026-07-14T12:00:00Z",
  "updated_at": "2026-07-14T12:34:56Z",
  "metadata": {
    "location": "campus-dorm-a",
    "gpu_type": "RTX-4090"
  }
}
```

**隐私约束**：
- ✅ 可返回：节点配置、状态、运行指标（聚合）、时间戳
- ❌ 不返回：密钥、Token、请求详情、用户 ID、模型 Prompt/响应

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足
- `NODE_NOT_FOUND` - 节点不存在

---
#### PATCH /api/v1/admin/nodes/{node_id}

**端点编号**：EP-ADMIN-064
**描述**：更新节点配置（如启用/禁用、调整容量）

**权限**：SYSTEM_ADMIN（仅系统管理员可修改节点）

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | uuid | 节点 ID |

**请求头**：
```
Authorization: Bearer <admin_token>
If-Match: <etag>
```

**请求体**：
```json
{
  "status": "maintenance",
  "max_concurrent_requests": 100,
  "metadata": {
    "maintenance_note": "Scheduled maintenance"
  }
}
```

**响应**：200 OK

```json
{
  "node_id": "uuid",
  "name": "edge-node-01",
  "status": "maintenance",
  "max_concurrent_requests": 100,
  "updated_at": "2026-07-14T12:40:00Z"
}
```

**幂等性**：支持 `If-Match` 头（乐观锁），防止并发修改冲突

**隐私约束**：
- ✅ 可修改：节点状态、配置、元数据
- ❌ 不可修改：节点 ID、创建时间、历史日志

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足（非 SYSTEM_ADMIN）
- `NODE_NOT_FOUND` - 节点不存在
- `PRECONDITION_FAILED` - If-Match ETag 不匹配

---
#### DELETE /api/v1/admin/nodes/{node_id}

**端点编号**：EP-ADMIN-065
**描述**：注销节点（标记为已删除，不物理删除）

**权限**：SYSTEM_ADMIN（仅系统管理员可删除节点）

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | uuid | 节点 ID |

**请求头**：
```
Authorization: Bearer <admin_token>
```

**响应**：204 No Content

**状态流转**：
- 删除后，节点状态 → `deleted`
- 节点不再接受新请求
- 已处理的请求不受影响
- 审计日志记录删除操作

**隐私约束**：
- ✅ 可操作：注销节点
- ❌ 审计日志：仅记录操作者、时间、节点 ID，不记录节点配置详情

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足（非 SYSTEM_ADMIN）
- `NODE_NOT_FOUND` - 节点不存在
- `NODE_IN_USE` - 节点正在处理请求，无法删除

---
#### POST /api/v1/admin/nodes/{node_id}/health-check

**端点编号**：EP-ADMIN-066
**描述**：手动触发节点健康检查

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | uuid | 节点 ID |

**请求头**：
```
Authorization: Bearer <admin_token>
```

**请求体**：（空）

**响应**：200 OK

```json
{
  "node_id": "uuid",
  "status": "healthy",
  "checks": {
    "database": "passed",
    "model_gateway": "passed",
    "disk_space": "passed",
    "gpu_available": "passed"
  },
  "latency_ms": 150,
  "checked_at": "2026-07-14T12:34:56Z"
}
```

**健康检查项**：
| 检查项 | 说明 |
|--------|------|
| `database` | 数据库连接 |
| `model_gateway` | 模型网关 |
| `disk_space` | 磁盘空间 |
| `gpu_available` | GPU 可用性 |

**隐私约束**：
- ✅ 可返回：检查状态、检查项状态、延迟、时间戳
- ❌ 不返回：内部错误详情、数据库连接字符串、密钥、用户数据

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足
- `NODE_NOT_FOUND` - 节点不存在
- `HEALTH_CHECK_FAILED` - 健康检查失败（节点无响应）
- `NODE_OFFLINE` - 节点离线

---
#### GET /api/v1/admin/nodes/{node_id}/metrics

**端点编号**：EP-ADMIN-067
**描述**：获取节点的详细运行指标

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | uuid | 节点 ID |

**请求头**：
```
Authorization: Bearer <admin_token>
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_time` | datetime | 否 | 开始时间（默认 1 小时前） |
| `end_time` | datetime | 否 | 结束时间（默认现在） |
| `interval` | string | 否 | 聚合间隔（`1m`/`5m`/`1h`，默认 `5m`） |

**响应**：200 OK

```json
{
  "node_id": "uuid",
  "interval": "5m",
  "metrics": [
    {
      "timestamp": "2026-07-14T12:30:00Z",
      "cpu_usage": 45.2,
      "memory_usage": 67.8,
      "gpu_usage": 82.1,
      "active_requests": 12,
      "request_latency_p50": 250,
      "request_latency_p95": 850,
      "error_rate": 0.02
    }
  ]
}
```

**指标字段**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `cpu_usage` | float | CPU 使用率（%） |
| `memory_usage` | float | 内存使用率（%） |
| `gpu_usage` | float | GPU 使用率（%） |
| `active_requests` | int | 活跃请求数 |
| `request_latency_p50` | float | 请求延迟 P50（毫秒） |
| `request_latency_p95` | float | 请求延迟 P95（毫秒） |
| `error_rate` | float | 错误率（0-1） |

**隐私约束**：
- ✅ 可返回：系统资源指标、聚合统计
- ❌ 不返回：请求详情、用户 ID、模型名称、敏感标签、错误详情

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足
- `NODE_NOT_FOUND` - 节点不存在
- `INVALID_TIME_RANGE` - 时间范围无效

---
#### POST /api/v1/admin/models

**端点编号**：EP-ADMIN-068
**描述**：注册新的模型配置

**权限**：SYSTEM_ADMIN（仅系统管理员可创建模型）

**请求头**：
```
Authorization: Bearer <admin_token>
Idempotency-Key: <uuid>  # 见 1.4
```

**请求体**：
```json
{
  "name": "local-llama-7b",
  "version": "1.0.0",
  "provider": "local",
  "model_type": "chat",
  "endpoint": "http://edge-node-01:8000/v1/chat",
  "capabilities": ["chat", "structured_output"],
  "max_tokens": 2048,
  "default_temperature": 0.7,
  "enabled": true,
  "metadata": {
    "description": "Local LLaMA 7B model",
    " quantization": "q4_0"
  }
}
```

**响应**：201 Created

```json
{
  "model_id": "uuid",
  "name": "local-llama-7b",
  "version": "1.0.0",
  "provider": "local",
  "model_type": "chat",
  "enabled": true,
  "created_at": "2026-07-14T12:00:00Z"
}
```

**隐私约束**：
- ✅ 可返回：模型 ID、名称、版本、提供商、类型、启用状态、配置元数据
- ❌ 不返回：API 密钥、认证 Token、Prompt 模板、系统指令

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足（非 SYSTEM_ADMIN）
- `MODEL_ALREADY_EXISTS` - 模型已存在（Idempotency-Key 冲突）
- `INVALID_MODEL_CONFIG` - 模型配置无效

---
#### GET /api/v1/admin/models

**端点编号**：EP-ADMIN-069
**描述**：获取所有模型配置列表

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**请求头**：
```
Authorization: Bearer <admin_token>
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider` | string | 否 | 按提供商过滤 |
| `enabled` | bool | 否 | 按启用状态过滤 |
| `page` | int | 否 | 页码（默认 1） |
| `limit` | int | 否 | 每页数量（默认 20，最大 100） |

**响应**：200 OK

```json
{
  "models": [
    {
      "model_id": "uuid",
      "name": "local-llama-7b",
      "version": "1.0.0",
      "provider": "local",
      "model_type": "chat",
      "enabled": true,
      "created_at": "2026-07-14T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

**隐私约束**：
- ✅ 可返回：模型 ID、名称、版本、提供商、类型、启用状态、创建时间
- ❌ 不返回：API 密钥、认证 Token、Prompt 模板、系统指令、成本信息

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足
- `INVALID_PAGINATION` - 分页参数无效

---
#### POST /api/v1/admin/deployments

**端点编号**：EP-ADMIN-070
**描述**：创建模型部署记录（记录模型部署历史）

**权限**：SYSTEM_ADMIN（仅系统管理员可创建部署）

**请求头**：
```
Authorization: Bearer <admin_token>
Idempotency-Key: <uuid>  # 见 1.4
```

**请求体**：
```json
{
  "model_id": "uuid",
  "node_id": "uuid",
  "version": "1.0.0",
  "status": "deployed",
  "metadata": {
    "deployed_by": "admin-user-id",
    "deployment_notes": "Production deployment"
  }
}
```

**响应**：201 Created

```json
{
  "deployment_id": "uuid",
  "model_id": "uuid",
  "node_id": "uuid",
  "version": "1.0.0",
  "status": "deployed",
  "deployed_at": "2026-07-14T12:00:00Z"
}
```

**隐私约束**：
- ✅ 可返回：部署 ID、模型 ID、节点 ID、版本、状态、时间戳
- ❌ 不返回：部署者信息（除非审计需要）、密钥、配置详情

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足（非 SYSTEM_ADMIN）
- `MODEL_NOT_FOUND` - 模型不存在
- `NODE_NOT_FOUND` - 节点不存在
- `DEPLOYMENT_ALREADY_EXISTS` - 部署已存在（Idempotency-Key 冲突）

---
#### GET /api/v1/admin/deployments

**端点编号**：EP-ADMIN-071
**描述**：获取所有模型部署记录列表

**权限**：SCHOOL_ADMIN 或 SYSTEM_ADMIN

**请求头**：
```
Authorization: Bearer <admin_token>
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model_id` | uuid | 否 | 按模型过滤 |
| `node_id` | uuid | 否 | 按节点过滤 |
| `status` | string | 否 | 按状态过滤（`deployed`/`failed`/`rolled_back`） |
| `page` | int | 否 | 页码（默认 1） |
| `limit` | int | 否 | 每页数量（默认 20，最大 100） |

**响应**：200 OK

```json
{
  "deployments": [
    {
      "deployment_id": "uuid",
      "model_id": "uuid",
      "model_name": "local-llama-7b",
      "node_id": "uuid",
      "node_name": "edge-node-01",
      "version": "1.0.0",
      "status": "deployed",
      "deployed_at": "2026-07-14T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 20
  }
}
```

**隐私约束**：
- ✅ 可返回：部署 ID、模型/节点 ID 和名称、版本、状态、时间戳
- ❌ 不返回：部署者信息、配置详情、密钥、成本信息

**错误码**：
- `ADMIN_PERMISSION_DENIED` - 权限不足
- `INVALID_PAGINATION` - 分页参数无效

---

## 3. WebSocket 事件（P0-10）

见 [实时与事件契约](./WEBSOCKET_CONTRACT.md)

---

## 4. 版本管理

### 4.1 API 版本

当前版本：`v1`

版本变更必须：
1. 更新本文档版本号
2. 更新 OpenAPI 规范
3. 通知前端团队
4. 至少保留1个旧版本

### 4.2 破坏性变更

破坏性变更必须：
1. 提前至少2周通知
2. 提供迁移指南
3. 保持旧版本可用
4. 通过 ADR 记录原因

---

## 5. 相关文档

- [领域词汇表](../domain/DOMAIN_VOCABULARY.md)
- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [场景状态机](../architecture/SCENE_STATE_MACHINE.md)

---

**下一步**：P0-10（草拟实时与事件契约）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
| 2026-07-15 | R1-C：认证/CSRF 契约复审修订 | Claude |
| | - 明确 CSRF bootstrap 流程（login/register 豁免，成功后签发 csrf_token） | |
| | - register 自动登录增加 Set-Cookie: csrf_token（与 login 一致） | |
| | - 统一 auth 端点 CSRF 豁免范围（login/register 豁免，refresh/logout 强制） | |
| | - CSRF_TOKEN_EXPIRED 降级为可选增强（P2 实现），MVP 仅用 MISSING/MISMATCH | |
| | - 新增 AUTH_REFRESH_TOKEN_EXPIRED、AUTH_INVALID_CREDENTIALS 错误码 | |
| | - 修正 Refresh 流程：Token 轮换、token family、重放检测 | |
| | - 移除 Bearer Admin API 的 CSRF 错误码，统一 Bearer 请求豁免规则 | |
