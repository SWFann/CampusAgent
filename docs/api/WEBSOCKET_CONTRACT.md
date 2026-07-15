# WebSocket 与事件契约

> **版本**：v1.0-frozen
> **冻结日期**：2026-07-15
> **状态**：已评审/已冻结
> **冻结范围**：连接协议、事件信封、全部事件 Schema、错误事件、版本策略、隐私投影规则
> **维护者**：开发团队

## 1. WebSocket 连接

### 1.1 连接地址

生产环境：

```
wss://<host>/api/v1/ws
```

本地开发：

```
ws://localhost:8000/api/v1/ws
```

> **路径说明**：使用 `/api/v1/ws` 而非 `/ws/v1`，因为 `access_token` Cookie 的 `Path=/api/v1`，WebSocket 路径在 Cookie 作用域内，可复用现有 HttpOnly Cookie，无需扩大 Cookie Path 或新增 ticket 端点。

### 1.2 认证

WebSocket 握手通过 `HttpOnly access_token Cookie` 完成认证，不使用 URL 查询参数、不使用一次性 ticket、不在连接成功后发送 Token。

```
GET /api/v1/ws HTTP/1.1
Host: <host>
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: ...
Sec-WebSocket-Version: 13
Origin: https://app.example.com
Cookie: access_token=<jwt>; csrf_token=<random>
```

**认证流程**：

1. 浏览器发起 `GET /api/v1/ws` Upgrade 请求
2. 浏览器自动携带 `access_token` Cookie（`HttpOnly`、`Secure`、`SameSite=Lax`、`Path=/api/v1`）
3. 服务端首先校验 `Origin` 白名单
4. 服务端读取 `access_token` Cookie
5. 服务端校验 JWT 签名、`exp`、用户状态和撤销状态
6. 校验成功后返回 `101 Switching Protocols`
7. 校验失败时拒绝升级，返回对应 HTTP 状态码
8. 连接成功后发送 `connection.established` 事件

**禁止的形式**：

以下形式明确禁止：

| 禁止形式 | 原因 |
|----------|------|
| `ws://localhost:8000/ws/v1?token=<access_token>` | Token 出现在 URL 查询参数，可能被日志记录 |
| `ws://localhost:8000/api/v1/ws?token=<access_token>` | Token 出现在 URL 查询参数 |
| `ws://localhost:8000/api/v1/ws?ticket=<ticket>` | 需要新增 ticket 端点，增加复杂度 |
| 连接成功后发送 `access_token` | 需要 JavaScript 读取 Token，破坏 HttpOnly 防护 |
| 从 `localStorage`/`sessionStorage` 获取 Token | XSS 风险，Token 可被窃取 |

### 1.3 Origin 校验

服务端维护允许的 Origin 白名单，在协议升级前完成校验。

**白名单规则**：

| 环境 | 允许的 Origin | 说明 |
|------|-------------|------|
| 生产 | `https://app.example.com` | 仅允许正式 Web 前端 Origin |
| 本地开发 | `http://localhost:3000`、`http://127.0.0.1:3000` | 显式配置的本地开发 Origin |

**校验规则**：

- 缺少 `Origin` 请求头：默认拒绝
- `Origin` 不匹配白名单：拒绝
- `Origin` 为 `null`：拒绝（浏览器在跨站请求中可能发送 `null`）
- 不允许使用通配符 `*`
- Origin 校验在协议升级前完成，是防止 Cross-Site WebSocket Hijacking 的关键控制

### 1.4 握手失败响应

握手阶段尚未建立 WebSocket 连接，因此返回 HTTP 状态码而非 WebSocket close code。

| 场景 | HTTP 状态码 | 错误码 | 说明 |
|------|:----------:|--------|---------|
| `access_token` Cookie 缺失 | 401 | `AUTH_INVALID_TOKEN` | 未认证 |
| Token 无效（签名错误） | 401 | `AUTH_INVALID_TOKEN` | 认证失败 |
| Token 已过期 | 401 | `AUTH_INVALID_TOKEN` | 认证失败 |
| Token 已撤销或认证上下文已失效 | 401 | `AUTH_INVALID_TOKEN` | 认证失败 |
| 用户被冻结或禁用 | 401 | `AUTH_ACCOUNT_DISABLED` | 账号状态异常 |
| `Origin` 缺失 | 403 | `WS_ORIGIN_NOT_ALLOWED` | CSWH 防护 |
| `Origin` 为 `null` | 403 | `WS_ORIGIN_NOT_ALLOWED` | CSWH 防护 |
| `Origin` 不在白名单 | 403 | `WS_ORIGIN_NOT_ALLOWED` | CSWH 防护 |
| WebSocket 服务暂不可用 | 503 | `SERVICE_UNAVAILABLE` | 服务端错误 |

**响应示例**（401）：

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "success": false,
  "error": {
    "code": "AUTH_INVALID_TOKEN",
    "message": "访问令牌无效或已过期",
    "details": {},
    "request_id": "d4e5f6a7-b8c9-4d0e-8f2a-3b4c5d6e7f80",
    "retryable": false
  }
}
```

**响应示例**（403 Origin 不匹配）：

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "success": false,
  "error": {
    "code": "WS_ORIGIN_NOT_ALLOWED",
    "message": "Origin 不在允许列表中",
    "details": {},
    "request_id": "e5f6a7b8-c9d0-4e1f-a3b4-4c5d6e7f8090",
    "retryable": false
  }
}
```

### 1.5 CSRF 关系

WebSocket 握手是 `GET` Upgrade 请求，不使用 `X-CSRF-Token` 请求头。

WebSocket 依靠以下机制防护：

1. **SameSite Cookie**：`SameSite=Lax` 提供纵深防护，但 WebSocket 安全不能只依赖 SameSite；严格 Origin 白名单校验是防止 Cross-Site WebSocket Hijacking 的强制控制
2. **严格 Origin 白名单**：防止 Cross-Site WebSocket Hijacking（协议升级前完成校验）
3. **服务端身份校验**：JWT 签名、exp、用户状态和撤销状态

**业务写操作**：

- 当前客户端事件仅包括订阅、取消订阅和心跳，不直接执行业务写操作
- 消息发送、投票、确认等写操作继续通过 HTTP API，并使用现有 CSRF 方案（Section 1.5.6）
- 未来如果增加 WebSocket 业务写命令，必须单独定义消息级授权、幂等和防重放规则

### 1.6 订阅授权

连接认证成功不代表可以订阅所有会话。

- `conversation.subscribe` 时必须重新校验当前用户是否为会话参与者
- 每次订阅都进行资源级授权
- 用户退出会话或权限被撤销后，服务端停止向该连接推送该会话事件
- 禁止通过猜测 `conversation_id` 订阅他人会话

### 1.7 日志和隐私

**明确禁止记录**：

- Cookie 原文
- JWT 原文
- WebSocket URL 中的认证凭据（即使现在不使用 URL Token，仍禁止记录任何认证凭据）
- 私有消息正文
- P2/P3/P4 数据
- 完整事件 `data` 内容

**允许记录**：

- `event`
- `event_id`
- `request_id`
- `connection_id`
- `user_id`
- `sequence`
- Origin 校验结果
- 握手成功/失败状态
- 脱敏错误码
- `payload_size`
- `duration`
- 连接时长

### 1.8 浏览器握手失败恢复流程

浏览器 WebSocket API 通常不向 JavaScript 暴露握手失败的 HTTP 401/403 详情。当握手失败时，浏览器只触发 `onerror` 和 `onclose`，不提供 HTTP 状态码或响应体。因此客户端不能直接从 WebSocket 错误推断认证状态。

**应用启动时**：

1. 应用启动时先调用 `GET /api/v1/auth/me` 检查当前认证状态。
2. `/me` 返回 200 后才建立 WebSocket 连接。
3. `/me` 返回 401 时，只尝试一次 single-flight `POST /api/v1/auth/refresh`。
4. Refresh 成功后重新调用 `/me` 确认认证状态，再建立 WebSocket。
5. Refresh 失败后跳转登录页，不建立 WebSocket。

**WebSocket 在建立前触发 `onerror` 时**：

1. 不得直接推断为 401 或 403。
2. 调用 `GET /api/v1/auth/me` 检查认证状态。
3. `/me` 返回 401 时，执行一次 single-flight `POST /api/v1/auth/refresh`。Refresh 成功后重试建立 WebSocket。Refresh 失败后进入 `AUTH_FAILED` 状态，跳转登录页。
4. `/me` 返回 200 时，按网络异常、Origin 配置错误或服务异常处理，进入 `RECONNECTING` 状态执行退避重连。
5. 禁止握手失败导致无限 refresh 循环。同一应用会话中，握手失败后的 refresh 最多执行一次；如果 refresh 成功后 WebSocket 仍然握手失败，按网络或服务异常处理，不再触发 refresh。

---

## 2. 事件格式

### 2.1 客户端命令信封

客户端发送给服务端的每条消息必须使用以下统一信封：

```json
{
  "event": "conversation.subscribe",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "version": "v1",
  "request_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "timestamp": "2026-07-15T10:30:00Z"
}
```

**字段规则**：

| 字段 | 类型 | 必填 | 允许 null | 说明 |
|------|------|:----:|:---------:|------|
| `event` | string | 是 | 否 | 固定事件名，如 `conversation.subscribe` |
| `data` | object | 是 | 否 | 事件数据；没有数据时使用空对象 `{}`，不使用 `null` |
| `version` | string | 是 | 否 | 协议主版本，MVP 固定为 `v1` |
| `request_id` | UUID v4 | 是 | 否 | 客户端生成的请求唯一标识，用于请求与响应关联。必须为合法小写 UUID v4 |
| `timestamp` | string | 是 | 否 | UTC RFC 3339，秒级精度，`Z` 后缀 |

**客户端命令不使用**：

- `event_id`
- `sequence`
- 单独的 `id` 字段

### 2.2 服务端事件信封

服务端发送给客户端的每条消息必须使用以下统一信封：

```json
{
  "event": "connection.established",
  "data": {
    "connection_id": "conn_xxx",
    "server_time": "2026-07-15T10:30:00Z",
    "access_token_expires_at": "2026-07-15T11:30:00Z"
  },
  "version": "v1",
  "event_id": "evt_001",
  "sequence": 1,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": null
}
```

**字段规则**：

| 字段 | 类型 | 必填 | 允许 null | 说明 |
|------|------|:----:|:---------:|------|
| `event` | string | 是 | 否 | 事件名称 |
| `data` | object | 是 | 否 | 事件数据；没有数据时使用空对象 `{}` |
| `version` | string | 是 | 否 | 协议主版本，固定为 `v1` |
| `event_id` | string | 是 | 否 | 服务端生成的事件唯一标识 |
| `sequence` | integer | 是 | 否 | 单连接内服务端事件序号，必须 ≥ 1 |
| `timestamp` | string | 是 | 否 | UTC RFC 3339，秒级精度，`Z` 后缀 |
| `request_id` | UUID v4 \| null | 是 | 是 | 请求关联标识。直接响应回显客户端 UUID v4；主动推送为 `null`；无法解析请求的 `error` 为 `null` |

**`request_id` 关联规则**：

| 场景 | `request_id` 值 |
|------|-----------------|
| 对客户端命令的直接响应 | 回显客户端 `request_id` |
| 主动推送事件 | 固定为 `null` |
| `error` 事件且可以关联有效命令 | 回显客户端 `request_id` |
| `error` 事件且无法解析请求或无法获得 `request_id` | 使用 `null` |

**`event_id` 约束**：

- 对每个服务端事件唯一
- 重复投递同一个逻辑事件时必须保持相同 `event_id`
- 客户端把它作为传输层去重键
- 不得包含用户数据、资源正文或可推断隐私的信息
- 客户端不得解析 `event_id` 的内部结构

### 2.3 sequence 语义

`sequence` 只保留一种语义：**单个 WebSocket 连接内的服务端事件序号**。

- `connection.established` 使用 `sequence=1`
- 此后该连接发送的所有服务端事件严格递增
- 同一连接内不得重复和倒退
- 新连接重新从 1 开始
- 不保证跨连接连续
- 不保证全局连续
- 客户端发现同一连接 `sequence` 跳号时，按照 §6.3 规则执行 HTTP 回补
- `sequence` 不用于业务幂等
- `event_id` 用于传输去重
- `message_id` 等资源 ID 用于业务幂等

### 2.4 时间格式

所有 WebSocket JSON 示例和实际传输中的时间字段统一使用：

```
2026-07-15T10:30:00Z
```

**规则**：

- UTC
- RFC 3339
- 秒级精度
- `Z` 后缀
- 不使用毫秒
- 不使用 `+09:00`、`+08:00` 等偏移示例
- `expires_at`、`expired_at`、`server_time`、`access_token_expires_at`、`created_at`、`updated_at`、`deleted_at`、`joined_at`、`left_at`、`timestamp` 全部遵守同一规则

WebSocket 使用 UTC `Z` 是 HTTP 契约（§1.3.4）允许范围内更严格的子集。

---

## 3. 客户端事件

### 3.1 conversation.subscribe

**方向**：客户端 → 服务端
**触发时机**：客户端需要订阅指定会话的实时事件推送
**授权前提**：连接已认证 + 当前用户为该会话参与者
**request_id 关联**：是，服务端通过 `conversation.subscribed` 回显

```json
{
  "event": "conversation.subscribe",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "version": "v1",
  "request_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "timestamp": "2026-07-15T10:30:00Z"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 订阅的会话 ID | P1 |

**客户端处理方式**：发送后等待 `conversation.subscribed` 确认。如果收到 `error` 事件，从本地订阅集合移除该 `conversation_id`。

---

### 3.2 conversation.unsubscribe

**方向**：客户端 → 服务端
**触发时机**：客户端不再需要指定会话的实时事件推送
**授权前提**：连接已认证
**request_id 关联**：是，服务端通过 `conversation.unsubscribed` 回显

```json
{
  "event": "conversation.unsubscribe",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "version": "v1",
  "request_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
  "timestamp": "2026-07-15T10:31:00Z"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 取消订阅的会话 ID | P1 |

**客户端处理方式**：发送后等待 `conversation.unsubscribed` 确认。

---

### 3.3 ping

**方向**：客户端 → 服务端
**触发时机**：客户端心跳定时器触发，每 30 秒发送一次
**授权前提**：连接已建立
**request_id 关联**：是，服务端通过 `pong` 回显

```json
{
  "event": "ping",
  "data": {},
  "version": "v1",
  "request_id": "c3d4e5f6-a7b8-4c9d-8e1f-2a3b4c5d6e7f",
  "timestamp": "2026-07-15T10:30:00Z"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| （无字段） | — | — | — | — | 固定为空对象 `{}` | P0 元数据 |

**客户端处理方式**：等待 `pong` 响应。连续两次未收到 `pong`，主动关闭连接（关闭码 4408）。

---

## 4. 服务端事件

### 4.1 连接事件

#### 4.1.1 connection.established

**方向**：服务端 → 客户端
**触发时机**：连接认证成功后服务端立即发送
**授权前提**：握手认证通过
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "connection.established",
  "data": {
    "connection_id": "conn_xxx",
    "server_time": "2026-07-15T10:30:00Z",
    "access_token_expires_at": "2026-07-15T11:30:00Z"
  },
  "version": "v1",
  "event_id": "evt_001",
  "sequence": 1,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `connection_id` | string | 是 | 否 | 服务端生成 | 连接唯一标识 | P0 元数据 |
| `server_time` | string | 是 | 否 | UTC RFC 3339 | 服务端当前时间，用于时钟偏差校正 | P0 元数据 |
| `access_token_expires_at` | string | 是 | 否 | UTC RFC 3339 | 当前 access_token 的过期时间，客户端用于计算何时触发 Refresh | P0 元数据 |

**客户端处理方式**：收到后根据状态机进入 `OPEN`（首次连接无历史订阅）或 `RESTORING`（有历史订阅）。

---

#### 4.1.2 connection.expiring

**方向**：服务端 → 客户端
**触发时机**：服务端在 access_token 到期前固定 60 秒发送。如果连接建立时 Token 剩余有效期 ≤ 60 秒，应立即发送。60 秒宽限期是服务端固定行为，不在 payload 中重复传递。
**授权前提**：连接处于 `OPEN` 或 `RESTORING` 状态
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "connection.expiring",
  "data": {
    "expires_at": "2026-07-15T11:30:00Z",
    "refresh_required": true,
    "reconnect_required": true
  },
  "version": "v1",
  "event_id": "evt_042",
  "sequence": 42,
  "timestamp": "2026-07-15T11:29:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `expires_at` | string | 是 | 否 | UTC RFC 3339 | access_token 的过期时间 | P0 元数据 |
| `refresh_required` | boolean | 是 | 否 | 固定 `true` | 指示客户端必须执行 Refresh | P0 元数据 |
| `reconnect_required` | boolean | 是 | 否 | 固定 `true` | 指示 Refresh 成功后必须创建新 WebSocket 连接 | P0 元数据 |

**客户端处理方式**：收到后进入 `REFRESHING` 状态，执行 single-flight Refresh。

---

#### 4.1.3 connection.expired

**方向**：服务端 → 客户端
**触发时机**：access_token 已经正式过期，服务端停止发送业务事件，准备使用 4401 关闭连接。如果连接状态允许，先发送该事件；如果无法可靠发送，可以直接关闭 4401。
**授权前提**：连接尚未关闭
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "connection.expired",
  "data": {
    "expired_at": "2026-07-15T11:30:00Z",
    "reconnect_required": true,
    "reason": "access_token_expired"
  },
  "version": "v1",
  "event_id": "evt_043",
  "sequence": 43,
  "timestamp": "2026-07-15T11:30:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `expired_at` | string | 是 | 否 | UTC RFC 3339 | access_token 的实际过期时间 | P0 元数据 |
| `reconnect_required` | boolean | 是 | 否 | 固定 `true` | 指示客户端必须创建新连接 | P0 元数据 |
| `reason` | string | 是 | 否 | `access_token_expired` | 过期原因，固定机器可读字符串 | P0 元数据 |

**要求**：

1. 不包含 Token、Cookie 或用户数据。
2. 发送后立即使用 4401 关闭连接。
3. 客户端不能依赖一定收到该事件，必须同时处理 4401 关闭码。
4. 如果 TCP 连接已不稳定或发送缓冲区已满，服务端可以直接关闭 4401 而不发送该事件。

**客户端处理方式**：收到后准备执行 single-flight Refresh，随后处理 4401 关闭码。

---

### 4.2 命令响应事件

#### 4.2.1 conversation.subscribed

**方向**：服务端 → 客户端
**触发时机**：服务端成功处理 `conversation.subscribe` 并完成资源级授权后发送
**授权前提**：当前用户为该会话参与者
**request_id 关联**：是，回显 `conversation.subscribe` 的 `request_id`

```json
{
  "event": "conversation.subscribed",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "success": true
  },
  "version": "v1",
  "event_id": "evt_010",
  "sequence": 10,
  "timestamp": "2026-07-15T10:30:01Z",
  "request_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 已订阅的会话 ID | P1 |
| `success` | boolean | 是 | 否 | 固定 `true` | 订阅成功标识 | P0 元数据 |

**客户端处理方式**：确认订阅成功，开始接收该会话的实时事件。订阅失败不返回 `success=false`，统一返回 `error` 事件。

---

#### 4.2.2 conversation.unsubscribed

**方向**：服务端 → 客户端
**触发时机**：服务端成功处理 `conversation.unsubscribe` 后发送
**授权前提**：连接已认证
**request_id 关联**：是，回显 `conversation.unsubscribe` 的 `request_id`

```json
{
  "event": "conversation.unsubscribed",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "success": true
  },
  "version": "v1",
  "event_id": "evt_011",
  "sequence": 11,
  "timestamp": "2026-07-15T10:31:01Z",
  "request_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 已取消订阅的会话 ID | P1 |
| `success` | boolean | 是 | 否 | 固定 `true` | 取消订阅成功标识 | P0 元数据 |

**客户端处理方式**：确认取消订阅成功，停止接收该会话的实时事件。取消订阅失败统一返回 `error` 事件。

---

#### 4.2.3 pong

**方向**：服务端 → 客户端
**触发时机**：服务端收到 `ping` 后响应
**授权前提**：连接已建立
**request_id 关联**：是，回显 `ping` 的 `request_id`

```json
{
  "event": "pong",
  "data": {},
  "version": "v1",
  "event_id": "evt_012",
  "sequence": 12,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": "c3d4e5f6-a7b8-4c9d-8e1f-2a3b4c5d6e7f"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| （无字段） | — | — | — | — | 固定为空对象 `{}` | P0 元数据 |

**客户端处理方式**：确认心跳正常。ping/pong 数据不得携带用户数据。

---

### 4.3 消息事件

#### 4.3.1 message.created

**方向**：服务端 → 客户端
**触发时机**：会话中产生新消息时推送
**授权前提**：当前连接已通过 `conversation.subscribe` 订阅该会话，且用户仍为会话参与者
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "message.created",
  "data": {
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "conversation_id": "660e8400-e29b-41d4-a716-446655440000",
    "sender_type": "USER",
    "sender_user_id": "770e8400-e29b-41d4-a716-446655440000",
    "sender_agent_id": null,
    "message_type": "TEXT",
    "content": "今晚一起去吃饭吗？",
    "created_at": "2026-07-15T10:30:00Z"
  },
  "version": "v1",
  "event_id": "evt_020",
  "sequence": 20,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | HTTP Message 字段映射 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------------------|---------|
| `message_id` | UUID | 是 | 否 | UUID v4 | 消息唯一标识 | `Message.id` | P0 |
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 会话 ID | `Message.conversation_id` | P1 |
| `sender_type` | string | 是 | 否 | `USER`、`AGENT`、`SYSTEM` | 发送者类型 | `Message.sender_type` | P1 |
| `sender_user_id` | UUID \| null | 是 | 是 | UUID v4 | 发送用户 ID | `Message.sender_user_id` | P1 |
| `sender_agent_id` | UUID \| null | 是 | 是 | UUID v4 | 发送智能体 ID | `Message.sender_agent_id` | P1 |
| `message_type` | string | 是 | 否 | 见下方完整枚举 | 消息类型 | `Message.message_type` | P1 |
| `content` | string \| null | 是 | 是 | — | 消息文本内容 | `Message.content` | P1/P2 |
| `created_at` | string | 是 | 否 | UTC RFC 3339 | 消息创建时间 | `Message.created_at` | P0 |

**`message_type` 完整 v1 枚举**（来源：`DOMAIN_VOCABULARY.md`）：

| 值 | 说明 |
|----|------|
| `TEXT` | 文本消息 |
| `IMAGE` | 图片 |
| `FILE` | 文件 |
| `SYSTEM` | 系统消息 |
| `AGENT_PUBLIC` | 智能体公开消息 |
| `SCENE_CARD` | 场景卡片 |
| `VOTE` | 投票 |
| `PROPOSAL` | 提案 |
| `RESULT` | 结果 |
| `PRIVACY_NOTICE` | 隐私说明 |

**`sender_type` 条件规则**：

| `sender_type` | `sender_user_id` | `sender_agent_id` |
|-------------|-----------------|------------------|
| `USER` | 必须为 UUID v4 | 必须为 `null` |
| `AGENT` | 必须为 `null` | 必须为 UUID v4 |
| `SYSTEM` | 必须为 `null` | 必须为 `null` |

所有字段必须始终出现在 payload 中，不允许“有时省略、有时 null”的不确定形态。

**推送范围与禁止规则**：

- 客户端通过 HTTP 发送消息时，MVP 当前只允许 `API_CONTRACT.md` 已声明的 `TEXT`/`IMAGE`。
- 其他类型属于系统或场景生成的会话可见消息。
- WebSocket 只负责推送用户已经有权通过 HTTP Message API 读取的会话可见投影。
- `visibility=PRIVATE`/`HIDDEN` 的消息不得推送。
- Agent 私域消息不得推送。
- P3/P4 数据不得推送。
- `content` 可以是 `string` 或 `null`。
- 非文本结构化详情以 HTTP API 为最终事实来源。
- 不在 WebSocket 中加入任意 `structured_payload` 对象。
- 不加入 `metadata`。
- 不加入智能体推理信息。
- 如果 WebSocket 与 HTTP 消息内容冲突，以 HTTP API 为最终事实来源。

**客户端处理方式**：将消息追加到对应会话的消息列表，使用 `message_id` 进行业务幂等去重。

---

#### 4.3.2 message.deleted

**方向**：服务端 → 客户端
**触发时机**：会话中的消息被删除（软删除）时推送
**授权前提**：当前连接已订阅该会话，且用户仍为会话参与者
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "message.deleted",
  "data": {
    "message_id": "550e8400-e29b-41d4-a716-446655440000",
    "conversation_id": "660e8400-e29b-41d4-a716-446655440000",
    "deleted_at": "2026-07-15T10:35:00Z"
  },
  "version": "v1",
  "event_id": "evt_021",
  "sequence": 21,
  "timestamp": "2026-07-15T10:35:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `message_id` | UUID | 是 | 否 | UUID v4 | 被删除的消息 ID，映射自 HTTP `Message.id` | P0 |
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 会话 ID | P1 |
| `deleted_at` | string | 是 | 否 | UTC RFC 3339 | 消息删除时间 | P0 |

**客户端处理方式**：从对应会话的消息列表中标记或移除该消息。

---

### 4.4 会话事件

#### 4.4.1 conversation.updated

**方向**：服务端 → 客户端
**触发时机**：会话信息（如标题）发生变更时推送
**授权前提**：当前连接已订阅该会话，且用户仍为会话参与者
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "conversation.updated",
  "data": {
    "conversation_id": "660e8400-e29b-41d4-a716-446655440000",
    "title": "聚餐讨论群",
    "updated_at": "2026-07-15T10:32:00Z"
  },
  "version": "v1",
  "event_id": "evt_030",
  "sequence": 30,
  "timestamp": "2026-07-15T10:32:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 会话 ID | P1 |
| `title` | string | 是 | 否 | — | 会话标题 | P0/P1 |
| `updated_at` | string | 是 | 否 | UTC RFC 3339 | 会话更新时间 | P0 |

**约束**：

- 与 `API_CONTRACT.md` 的 Conversation 模型保持字段类型一致。
- 只向仍具有该会话访问权的订阅者发送。
- 用户被移出会话后必须停止继续发送该会话事件。
- 不得暴露 `email`、`phone`、`student_no`、权限详情或私有资料。

**客户端处理方式**：更新对应会话的本地缓存。

---

#### 4.4.2 participant.joined

**方向**：服务端 → 客户端
**触发时机**：新成员加入会话时推送
**授权前提**：当前连接已订阅该会话，且用户仍为会话参与者
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "participant.joined",
  "data": {
    "conversation_id": "660e8400-e29b-41d4-a716-446655440000",
    "participant": {
      "type": "USER",
      "user_id": "770e8400-e29b-41d4-a716-446655440000",
      "display_name": "李四"
    },
    "joined_at": "2026-07-15T10:33:00Z"
  },
  "version": "v1",
  "event_id": "evt_031",
  "sequence": 31,
  "timestamp": "2026-07-15T10:33:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 会话 ID | P1 |
| `participant` | object | 是 | 否 | — | 参与者结构 | P1 |
| `participant.type` | string | 是 | 否 | `USER`、`AGENT` | 参与者类型，与 HTTP API `participant_type` 一致 | P1 |
| `participant.user_id` | UUID | 条件必填 | 是 | UUID v4 | 用户 ID（`type=USER` 时必填） | P1 |
| `participant.agent_id` | UUID | 条件必填 | 是 | UUID v4 | 智能体 ID（`type=AGENT` 时必填） | P1 |
| `participant.display_name` | string | 是 | 否 | — | 参与者显示名称 | P1 |
| `joined_at` | string | 是 | 否 | UTC RFC 3339 | 加入时间 | P0 |

**约束**：

- `participant` 结构必须明确，不允许任意扩展。
- 不得暴露 `email`、`phone`、`student_no`、权限详情或私有资料。
- 只向仍具有该会话访问权的订阅者发送。

**客户端处理方式**：将新参与者添加到对应会话的参与者列表。

---

#### 4.4.3 participant.left

**方向**：服务端 → 客户端
**触发时机**：成员退出或被移出会话时推送
**授权前提**：当前连接已订阅该会话，且用户仍为会话参与者
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "participant.left",
  "data": {
    "conversation_id": "660e8400-e29b-41d4-a716-446655440000",
    "participant": {
      "type": "USER",
      "user_id": "770e8400-e29b-41d4-a716-446655440000",
      "display_name": "李四"
    },
    "left_at": "2026-07-15T10:34:00Z"
  },
  "version": "v1",
  "event_id": "evt_032",
  "sequence": 32,
  "timestamp": "2026-07-15T10:34:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `conversation_id` | UUID | 是 | 否 | UUID v4 | 会话 ID | P1 |
| `participant` | object | 是 | 否 | — | 参与者结构 | P1 |
| `participant.type` | string | 是 | 否 | `USER`、`AGENT` | 参与者类型 | P1 |
| `participant.user_id` | UUID | 条件必填 | 是 | UUID v4 | 用户 ID | P1 |
| `participant.agent_id` | UUID | 条件必填 | 是 | UUID v4 | 智能体 ID | P1 |
| `participant.display_name` | string | 是 | 否 | — | 参与者显示名称 | P1 |
| `left_at` | string | 是 | 否 | UTC RFC 3339 | 离开时间 | P0 |

**约束**：与 `participant.joined` 相同。被移出的用户不再收到该会话后续事件。

**客户端处理方式**：从对应会话的参与者列表中移除该参与者。如果离开的是当前用户，停止接收该会话事件。

---

### 4.5 场景事件

#### 4.5.1 scene.updated

**方向**：服务端 → 客户端
**触发时机**：场景阶段变化或提交进度更新时推送
**授权前提**：当前用户为该场景参与者，连接已认证
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "scene.updated",
  "data": {
    "scene_instance_id": "880e8400-e29b-41d4-a716-446655440000",
    "state": "WAITING_FOR_PRIVATE_INPUT",
    "submitted_count": 3,
    "total_count": 4,
    "privacy": {
      "debate_visible": false,
      "raw_preferences_visible": false
    }
  },
  "version": "v1",
  "event_id": "evt_040",
  "sequence": 40,
  "timestamp": "2026-07-15T10:40:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `scene_instance_id` | UUID | 是 | 否 | UUID v4 | 场景实例 ID | P1 |
| `state` | string | 是 | 否 | 见下方完整封闭枚举 | 场景当前状态，与 `SCENE_STATE_MACHINE.md` 生命周期状态一致 | P1 |
| `submitted_count` | integer | 是 | 否 | ≥ 0 | 已提交偏好的参与者数量 | P0/P1 |
| `total_count` | integer | 是 | 否 | ≥ 0 | 总参与者数量 | P0/P1 |
| `privacy` | object | 是 | 否 | — | 隐私标记 | P0 元数据 |
| `privacy.debate_visible` | boolean | 是 | 否 | 固定 `false` | 智能体辩论不可见 | P0 元数据 |
| `privacy.raw_preferences_visible` | boolean | 是 | 否 | 固定 `false` | 原始偏好不可见 | P0 元数据 |

**`state` 完整封闭枚举**（与 `SCENE_STATE_MACHINE.md` 一致）：

| 状态 | 说明 |
|------|------|
| `DRAFT` | 草稿 |
| `WAITING_FOR_PARTICIPANTS` | 等待参与者 |
| `WAITING_FOR_CONSENT` | 等待授权 |
| `WAITING_FOR_PRIVATE_INPUT` | 等待私有输入 |
| `PROCESSING` | 处理中 |
| `CANDIDATES_READY` | 候选就绪 |
| `VOTING` | 投票中 |
| `CONFIRMING` | 确认中 |
| `COMPLETED` | 已完成（终态） |
| `CANCELLED` | 已取消（终态） |
| `FAILED` | 失败（终态） |
| `EXPIRED` | 已过期（终态） |

WebSocket 不再自行定义第二套场景枚举。`state` 与 `SCENE_STATE_MACHINE.md` 的生命周期状态一致。

**约束**：

- `submitted_count >= 0`
- `total_count >= 0`
- `submitted_count <= total_count`
- `submitted_count` 只在与提交进度有关的阶段具有业务意义，但为了固定 Schema 始终存在
- `submitted_count` 和 `total_count` 不得暴露具体提交者身份
- `scene.completed` 不作为独立事件
- `COMPLETED`/`CANCELLED`/`FAILED`/`EXPIRED` 都通过 `scene.updated` 表达

**客户端处理方式**：更新场景进度显示。如果需要详细结果，通过 HTTP API `GET /api/v1/scene-instances/{scene_instance_id}` 获取。

---

#### 4.5.2 scene.result.generated

**方向**：服务端 → 客户端
**触发时机**：场景结果生成完成时推送最小通知
**授权前提**：当前用户为该场景参与者，连接已认证
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "scene.result.generated",
  "data": {
    "scene_instance_id": "880e8400-e29b-41d4-a716-446655440000",
    "state": "CANDIDATES_READY",
    "result_available": true
  },
  "version": "v1",
  "event_id": "evt_041",
  "sequence": 41,
  "timestamp": "2026-07-15T10:45:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `scene_instance_id` | UUID | 是 | 否 | UUID v4 | 场景实例 ID | P1 |
| `state` | string | 是 | 否 | 固定 `CANDIDATES_READY` | 场景当前状态 | P1 |
| `result_available` | boolean | 是 | 否 | 固定 `true` | 结果已可用 | P0 元数据 |

**约束**：

- `state` 固定为 `CANDIDATES_READY`。
- 触发时机是 `PROCESSING` → `CANDIDATES_READY` 的状态转换。
- 不能写成 `COMPLETED`。该事件表示候选结果已经生成并可通过现有 HTTP API 读取。
- 最终结果确认完成由后续 `scene.updated`/`state=COMPLETED` 表达。
- 采用“最小事件通知 + HTTP 回源”原则，不在 WebSocket 中复制可能与 HTTP 漂移的 candidates 结果模型。
- 客户端收到后通过已存在的 Scene HTTP API 获取结果。
- HTTP API 是最终事实来源。
- 不新增 HTTP 端点。
- 不在 WebSocket 中推送个人偏好。
- 不推送偏好胶囊。
- 不推送智能体辩论。
- 不推送私有评价。
- 不推送模型 Prompt、模型响应或中间推理。
- 不推送能够反推出个人偏好的逐人分数。
- 公共事件不得包含 P2、P3、P4 数据。

**客户端处理方式**：收到通知后，调用 `GET /api/v1/scene-instances/{scene_instance_id}` 获取完整结果。

---

### 4.6 通知事件

#### 4.6.1 notification.created

**方向**：服务端 → 客户端
**触发时机**：当前用户产生新通知时推送
**授权前提**：通知所有者对应的连接
**request_id 关联**：否，`request_id` 固定为 `null`

```json
{
  "event": "notification.created",
  "data": {
    "notification_id": "990e8400-e29b-41d4-a716-446655440000",
    "type": "SCENE_INVITE",
    "title": "邀请您参与聚餐协商",
    "body": "张三邀请您参与一次聚餐场景协商",
    "created_at": "2026-07-15T10:30:00Z"
  },
  "version": "v1",
  "event_id": "evt_050",
  "sequence": 50,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": null
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `notification_id` | UUID | 是 | 否 | UUID v4 | 通知唯一标识 | P0 |
| `type` | string | 是 | 否 | WebSocket v1 开放枚举，当前已定义值：`SCENE_INVITE`；未来允许以非破坏性变更增加新的安全类型 | 通知类型 | P0/P1 |
| `title` | string | 是 | 否 | 最大长度 200 字符 | 通知标题，面向当前用户的安全通知投影 | P1 |
| `body` | string | 是 | 否 | 最大长度 500 字符 | 通知正文，面向当前用户的安全通知投影 | P1 |
| `created_at` | string | 是 | 否 | UTC RFC 3339 | 通知创建时间 | P0 |

**约束**：

- `type` 为 WebSocket v1 的开放枚举，当前权威来源是本契约（`WEBSOCKET_CONTRACT.md`），而不是 HTTP Notification 模型。
- 当前已定义值：`SCENE_INVITE`。未来允许以非破坏性变更增加新的安全类型。
- 客户端遇到未知 `type` 时按通用通知展示，不得崩溃。
- 未知 `type` 不得触发敏感操作或自动导航。
- `title`/`body` 长度边界：标题最大 200 字符，正文最大 500 字符。
- `title`/`body` 只能是面向当前用户的安全通知投影。
- 不得包含私有场景提交、记忆正文、其他用户偏好、P3/P4 数据。
- 如果某种通知需要敏感详情，只发送资源 ID 和通用提示，详情通过授权 HTTP API 获取。
- 通知只发送给通知所有者对应的连接。

**客户端处理方式**：将通知添加到通知列表。如果需要详细内容，通过授权 HTTP API 获取。

---

### 4.7 错误事件

#### 4.7.1 error

**方向**：服务端 → 客户端
**触发时机**：客户端命令处理失败、协议违规或服务端内部错误
**授权前提**：连接已建立
**request_id 关联**：如果可以关联有效命令，回显客户端 `request_id`；无法解析请求或无法获得 `request_id` 时使用 `null`

```json
{
  "event": "error",
  "data": {
    "code": "WS_INVALID_MESSAGE",
    "message": "WebSocket 消息格式无效",
    "details": {
      "field": "event",
      "reason": "unsupported_event"
    },
    "retryable": false,
    "retry_after_ms": null
  },
  "version": "v1",
  "event_id": "evt_099",
  "sequence": 99,
  "timestamp": "2026-07-15T10:30:00Z",
  "request_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
}
```

**data 字段表**：

| 字段 | 类型 | 必填 | 允许 null | 枚举/取值范围 | 语义 | 隐私等级 |
|------|------|:----:|:---------:|-------------|------|---------|
| `code` | string | 是 | 否 | 见下方错误码表 | 稳定机器可读错误码 | P0 元数据 |
| `message` | string | 是 | 否 | — | 安全的人类可读提示，不允许包含输入原文 | P0 元数据 |
| `details` | object | 是 | 否 | 只允许白名单安全字段（如 `field`、`reason`） | 附加信息，无详情使用 `{}` | P0 元数据 |
| `retryable` | boolean | 是 | 否 | `true`/`false` | 是否可重试 | P0 元数据 |
| `retry_after_ms` | integer \| null | 是 | 是 | `1000`～`300000`，或 `null` | 重试等待毫秒数；只有 `WS_RATE_LIMITED` 可使用非 `null` | P0 元数据 |

**禁止 `error` 事件回显**：

- 原始请求对象
- 原始消息正文
- Token
- Cookie
- Authorization
- X-CSRF-Token
- 私有偏好
- 记忆正文
- Prompt
- 模型响应
- 堆栈信息
- SQL
- 内部节点地址
- 用户不可见资源标识

**应用层 WebSocket 错误码**：

| 错误码 | `retryable` | `retry_after_ms` | 说明 |
|--------|:-----------:|:-----------------:|------|
| `WS_INVALID_MESSAGE` | false | null | WebSocket 消息格式无效 |
| `WS_UNSUPPORTED_EVENT` | false | null | 不支持的事件类型 |
| `WS_UNAUTHORIZED` | false | null | WebSocket 未授权操作 |
| `WS_FORBIDDEN` | false | null | WebSocket 权限拒绝 |
| `WS_SUBSCRIPTION_NOT_FOUND` | false | null | 订阅不存在 |
| `WS_RATE_LIMITED` | true | 1000～300000 | WebSocket 频率受限 |
| `WS_INTERNAL_ERROR` | false | null | WebSocket 内部错误 |

**握手阶段错误码（不使用 `error` 事件）**：

握手阶段继续使用既有 HTTP 错误码，不与连接建立后的 `error` 事件混为一谈：

- `AUTH_INVALID_TOKEN`
- `AUTH_ACCOUNT_DISABLED`
- `WS_ORIGIN_NOT_ALLOWED`
- `SERVICE_UNAVAILABLE`

**`WS_RATE_LIMITED` 的 `retry_after_ms` 规则**：

1. 服务端在关闭 4429 前尽可能发送 `error` 事件。
2. `error.data` 中包含 `code: WS_RATE_LIMITED`、`retryable: true`、`retry_after_ms`（正整数）。
3. 客户端收到后保存 `retry_after_ms`。
4. 随后收到 4429 时，等待该时间再重连。
5. 如果没有收到 `retry_after_ms`，使用默认 30000 毫秒。
6. `retry_after_ms` 必须限制在合理范围：1000～300000 毫秒。

**客户端处理方式**：根据 `code` 进行分支处理。`retryable=true` 时可安全重试，`retryable=false` 时不应重试。不要将 `message` 内容展示给用户作为操作指引。

---

## 5. 订阅管理

### 5.1 订阅范围

WebSocket 连接建立后，客户端必须显式订阅：

1. **会话订阅**：`conversation.subscribe`
2. **用户通知**：自动订阅当前用户

### 5.2 取消订阅

客户端可以取消订阅：
- `conversation.unsubscribe`

连接断开时自动取消所有订阅。

---

## 6. 重连策略

### 6.1 网络重连退避

**退避时间表**：

| 重连次数 | 基础延迟 | 说明 |
|:--------:|:--------:|------|
| 第 1 次 | 0 秒 | 立即重连 |
| 第 2 次 | 1 秒 | |
| 第 3 次 | 2 秒 | |
| 第 4 次 | 4 秒 | |
| 第 5 次 | 8 秒 | |
| 第 6 次 | 16 秒 | |
| 第 7 次及以后 | 30 秒 | 最大延迟上限 |

**Jitter 规则**：

- 每次重连的实际延迟在基础延迟上增加 ±20% 的随机抖动（jitter）。
- 公式：`actual_delay = base_delay * (1 + random(-0.2, 0.2))`。
- Jitter 防止大量客户端在服务恢复后同时重连造成惊群效应。

**连续失败处理**：

- 连续10次重连失败后，进入 `PAUSED` 状态。
- `PAUSED` 状态下停止自动重连，允许用户手动重试。
- 手动重试时重置失败计数器，从第 1 次退避重新开始。

**网络恢复检测**：

- 客户端监听浏览器 `online` 事件。
- 当从 `offline` 变为 `online` 时，重置失败计数器并立即尝试一次重连。
- 如果该次重连失败，继续按退避时间表重试。

### 6.2 自动重连白名单与禁止清单

**允许自动重连的关闭码和场景**：

| 关闭码/场景 | 说明 | 重连行为 |
|-------------|------|---------|
| 网络异常 | TCP 连接断开、DNS 解析失败等 | 按退避时间表重连 |
| 1001 | 服务离开（Going Away） | 按退避时间表重连 |
| 1011 | 服务端内部错误 | 按退避时间表重连 |
| 1012 | 服务重启（Service Restart） | 按退避时间表重连 |
| 4408 | 心跳超时 | 按退避时间表重连 |
| 4429 | 频率受限 | 等待 `retry_after_ms` 后重连 |

**禁止自动重连的关闭码和场景**：

| 关闭码/场景 | 说明 | 客户端行为 |
|-------------|------|-----------|
| 1000 | 正常关闭 | 不重连，进入 `CLOSED` |
| 1008 | 协议违规 | 不重连，提示协议错误 |
| 4403 | 权限拒绝或账号禁用 | 不重连，进入 `FORBIDDEN` |
| 4406 | 协议主版本不支持 | 不重连，提示升级客户端 |
| 用户注销 | 用户主动退出 | 不重连，进入 `CLOSED` |
| Refresh 失败 | Token 刷新失败 | 不重连，进入 `AUTH_FAILED`，跳转登录页 |
| 明确 Origin 配置错误 | Origin 不在白名单 | 不重连，提示配置错误，进入 `FORBIDDEN` |

### 6.3 漏消息 HTTP 回补

重连或重新订阅后，客户端通过 HTTP API 获取断开期间遗漏的消息。HTTP API 是最终事实来源。

**回补路径**：

```
GET /api/v1/conversations/{conversation_id}/messages?page=1&page_size=50
```

**回补规则**：

1. 客户端记录每个会话最后确认的 `message_id` 和 `created_at`。
2. 从第一页开始分页拉取（`page=1`，`page_size=50`）。
3. 使用 `message_id` 去重：已处理的 `message_id` 跳过。
4. 遇到最后确认的 `message_id` 时停止翻页——后续消息客户端已经收到。
5. 达到安全页数上限（默认 20 页，即 1000 条）时停止翻页，并提示用户手动刷新。
6. 会话元数据回源：
   ```
   GET /api/v1/conversations/{conversation_id}
   ```
7. 场景状态回源：
   ```
   GET /api/v1/scene-instances/{scene_instance_id}
   ```
8. `sequence` 跳号触发 HTTP 回补：当客户端检测到 `sequence` 不连续时，主动执行上述分页回补流程。
9. HTTP API是最终事实来源：当 WebSocket 事件与 HTTP API 响应冲突时，以 HTTP API 为准。
10. 不新增 `since`、`cursor` 或 `last_event_id` 参数：回补完全基于分页和 `message_id` 去重，不引入新的查询参数。

### 6.4 事件去重

使用 `event_id` 进行传输层去重，使用有界缓存防止内存无限增长。

**有界缓存规则**：

- 最多保留 1000 个 `event_id`。
- 或保留 24 小时（以 `event_id` 对应事件的 `timestamp` 为准）。
- 先达到者触发淘汰：当缓存达到 1000 条时，按 FIFO 淘汰最早加入的 `event_id`；当缓存中存在超过 24 小时的 `event_id` 时，删除过期条目。

**去重实现示例**：

```python
from collections import OrderedDict
from time import time

MAX_CACHE_SIZE = 1000
MAX_CACHE_AGE_SECONDS = 24 * 60 * 60  # 24 hours

class EventDedupCache:
    def __init__(self):
        self._cache: OrderedDict[str, float] = OrderedDict()

    def is_duplicate(self, event_id: str, timestamp: float) -> bool:
        self._evict_expired()
        if event_id in self._cache:
            return True
        self._add(event_id, timestamp)
        return False

    def _add(self, event_id: str, timestamp: float) -> None:
        self._cache[event_id] = timestamp
        if len(self._cache) > MAX_CACHE_SIZE:
            self._cache.popitem(last=False)  # FIFO eviction

    def _evict_expired(self) -> None:
        now = time()
        expired = [
            eid for eid, ts in self._cache.items()
            if now - ts > MAX_CACHE_AGE_SECONDS
        ]
        for eid in expired:
            del self._cache[eid]
```

**去重层级**：

| 层级 | ID | 作用域 | 说明 |
|------|-----|--------|------|
| 传输去重 | `event_id` | 单客户端 | 防止同一事件被处理两次 |
| 业务幂等 | `message_id` 等业务 ID | 业务逻辑 | 确保业务操作的幂等性 |
| 序列检测 | `sequence` | 单连接 | 检测跳号，触发 HTTP 回补 |

- `event_id` 用于传输去重，确保同一事件不会因为网络重传或重连后被处理两次。
- `message_id` 等业务 ID 用于业务幂等，确保同一业务操作不会被执行两次。
- `sequence` 只保证单连接内递增，不保证跨连接连续。

---

## 7. 连接生命周期

### 7.1 连接建立

1. 浏览器发起 `GET /api/v1/ws` Upgrade 请求
2. 浏览器自动携带 `access_token` Cookie
3. 服务端校验 `Origin` 白名单
4. 服务端读取 `access_token` Cookie 并校验 JWT
5. 校验成功后返回 `101 Switching Protocols`
6. 发送 `connection.established` 事件

### 7.2 连接保持

1. 客户端定期发送 `ping`
2. 服务端返回 `pong`
3. 心跳间隔：30秒

### 7.3 连接断开

1. 客户端主动断开
2. 服务端主动断开（Token 过期/撤销、用户状态变更）
3. 网络异常断开

**处理**：
- 客户端尝试重连
- 重连失败后提示用户

### 7.4 Token 过期

#### 7.4.1 技术事实

在连接认证上下文中必须明确以下事实：

1. **服务端在握手时验证access_token**：WebSocket连接建立时，服务端验证HttpOnly access_token Cookie。
2. **服务端从JWT exp得到当前连接认证上下文的失效时间**：服务端从JWT中提取exp字段，作为当前连接的认证上下文有效期。
3. **浏览器刷新Cookie不会改变已经建立的WebSocket连接**：已建立的连接不会自动更新Cookie认证上下文。
4. **不能在原连接上替换Token**：已建立的WebSocket不允许更新或替换认证凭据。
5. **不允许通过WebSocket发送新Token**：禁止通过WebSocket消息发送access_token、refresh_token或任何认证凭据。
6. **Refresh成功后必须创建一个新WebSocket连接**：刷新Token后必须建立全新的WebSocket连接。
7. **新连接认证、重订阅成功后才能替换旧连接**：新连接完成认证和订阅恢复后才能接管旧连接。
8. **Token过期后，旧连接不得继续接收业务事件**：服务端在Token正式到期后停止推送业务事件。
9. **Refresh失败时进入登录失效流程，不能无限重试**：Refresh失败时清除客户端状态，提示重新登录。

#### 7.4.2 Token临近过期 - connection.expiring

**服务端行为**：
- 服务端在access_token到期前60秒发送connection.expiring事件
- 如果连接建立时Token剩余有效期≤60秒，应立即发送connection.expiring

**客户端行为**：
- 收到connection.expiring后进入REFRESHING状态
- 不立即跳转登录
- 调用HTTP refresh端点（POST /api/v1/auth/refresh）
- 请求必须携带X-CSRF-Token

#### 7.4.3 HTTP Refresh流程与连接迁移

**Refresh 请求**：

1. 客户端调用 `POST /api/v1/auth/refresh`。
2. 请求必须携带 `X-CSRF-Token` 请求头。
3. 浏览器自动携带 `refresh_token` Cookie。
4. Refresh 成功后服务端轮换 `access_token` Cookie 和 `refresh_token` Cookie（Token 轮换，旧 refresh_token 立即失效）。

**连接迁移流程**（Refresh 成功后执行）：

1. `POST /api/v1/auth/refresh` 必须携带 `X-CSRF-Token`。
2. Refresh 成功后创建新 WebSocket 连接。
3. 等待新连接的 `connection.established` 事件，进入 `RESTORING` 状态。
4. 在新连接上逐项恢复订阅（按 7.8 重新订阅流程执行）。
5. 等待每个 `conversation.subscribed` 确认。
6. 服务端重新校验每个订阅权限。无权限的订阅从本地集合移除，不关闭连接。
7. 必要订阅全部恢复且 HTTP 回补完成后，新连接成为活动连接，进入 `OPEN` 状态。
8. 正常关闭旧连接（关闭码 1000）。
9. 清理旧连接的心跳计时器、事件监听器和重连计时器。
10. Refresh 失败进入 `AUTH_FAILED` 状态，不再建立新连接，清除登录状态，跳转登录页。

#### 7.4.4 Single-flight Refresh

1. 同一个应用上下文同时最多存在一个refresh请求
2. 多个connection.expiring复用同一个refresh Promise
3. Refresh成功后所有等待者复用结果
4. Refresh失败后进入统一AUTH_FAILED流程

#### 7.4.5 Token过期主动关闭 - 4401

4401 允许两个固定 reason，区分不同的认证失效场景：

**reason 1：`access_token_expired`**

- access_token 自然过期（JWT `exp` 到期）
- 服务端在关闭前尽可能先发送 `connection.expired` 事件
- 客户端可以尝试一次 single-flight refresh

**reason 2：`authentication_context_invalid`**

- session 或 token family 被撤销（如管理员强制下线、重放检测触发撤销）
- 认证上下文失效，但并非 Token 自然过期
- 客户端可以尝试一次 single-flight refresh
- 如果 refresh 失败则进入 `AUTH_FAILED`

**服务端行为**：
- Token 正式到期后，服务端停止推送业务事件
- 如果条件允许，先发送 `connection.expired` 事件
- 使用关闭码 4401，reason 为 `access_token_expired` 或 `authentication_context_invalid`

**客户端行为**：
- 收到 4401 后最多执行一次 single-flight refresh
- Refresh 成功后新建连接
- Refresh 失败后进入 `AUTH_FAILED`
- 不得对 4401 进行普通网络重连循环
- 客户端根据 reason 区分日志和用户提示，但两种 reason 的恢复流程相同

---

### 7.5 连接状态机

客户端 WebSocket 连接状态机定义如下。所有状态转换必须遵守此表格，不允许未定义的转换。

**状态定义**：

| 状态 | 说明 |
|------|------|
| `DISCONNECTED` | 未连接，尚未发起或已完全关闭 |
| `CONNECTING` | 正在发起 WebSocket 握手 |
| `OPEN` | 连接已建立，正常收发事件 |
| `REFRESHING` | 正在执行 Token Refresh |
| `RESTORING` | 新连接已建立，正在恢复订阅和执行必要 HTTP 回补，尚未成为活动连接 |
| `RECONNECTING` | 网络异常后退避重连中 |
| `AUTH_FAILED` | 认证失败，需重新登录 |
| `FORBIDDEN` | 权限拒绝或 Origin 配置错误，不可自动恢复 |
| `PAUSED` | 连续10次重连失败，暂停自动重连，等待手动重试 |
| `CLOSED` | 用户主动注销或正常关闭，不再连接 |

**状态转换表**：

| 当前状态 | 触发条件 | 下一状态 | 是否自动重试 | UI 行为 |
|----------|---------|---------|:----------:|---------|
| `DISCONNECTED` | 应用启动，`/me` 返回 200 | `CONNECTING` | — | 显示"连接中" |
| `DISCONNECTED` | 应用启动，`/me` 返回 401，refresh 成功 | `CONNECTING` | — | 显示"连接中" |
| `DISCONNECTED` | 应用启动，`/me` 返回 401，refresh 失败 | `AUTH_FAILED` | 否 | 跳转登录页 |
| `CONNECTING` | 收到 `connection.established`（首次连接，无历史订阅） | `OPEN` | — | 显示"已连接" |
| `CONNECTING` | 收到 `connection.established`（有历史订阅） | `RESTORING` | — | 显示"恢复订阅中" |
| `CONNECTING` | 握手失败（`onerror`），`/me` 返回 200 | `RECONNECTING` | 是 | 显示"重连中" |
| `CONNECTING` | 握手失败（`onerror`），`/me` 返回 401，refresh 成功 | `CONNECTING` | — | 显示"连接中" |
| `CONNECTING` | 握手失败（`onerror`），`/me` 返回 401，refresh 失败 | `AUTH_FAILED` | 否 | 跳转登录页 |
| `OPEN` | 收到 `connection.expiring` | `REFRESHING` | — | 显示"正在刷新认证" |
| `OPEN` | 收到 4401 关闭码 | `REFRESHING` | — | 显示"正在刷新认证" |
| `OPEN` | 收到 4403 关闭码 | `FORBIDDEN` | 否 | 显示"权限不足" |
| `OPEN` | 收到 4406 关闭码 | `FORBIDDEN` | 否 | 显示"协议版本不支持，请升级" |
| `OPEN` | 收到 1000 关闭码 | `CLOSED` | 否 | 显示"已断开" |
| `OPEN` | 收到 1001/1011/1012/4408 关闭码 | `RECONNECTING` | 是 | 显示"重连中" |
| `OPEN` | 收到 4429 关闭码 | `RECONNECTING` | 是（等待 `retry_after_ms`） | 显示"频率受限，重连中" |
| `OPEN` | 网络断开 | `RECONNECTING` | 是 | 显示"网络断开，重连中" |
| `OPEN` | 心跳超时（连续两次未收到 pong） | `RECONNECTING` | 是 | 显示"连接超时，重连中" |
| `OPEN` | 服务重启（1012） | `RECONNECTING` | 是 | 显示"服务重启，重连中" |
| `OPEN` | 用户注销 | `CLOSED` | 否 | 显示"已退出" |
| `REFRESHING` | Refresh 成功，新连接 `connection.established` | `RESTORING` | — | 显示"恢复订阅中" |
| `REFRESHING` | Refresh 失败 | `AUTH_FAILED` | 否 | 跳转登录页 |
| `RECONNECTING` | 重连成功，收到 `connection.established` | `RESTORING` | — | 显示"恢复订阅中" |
| `RECONNECTING` | 连续10次失败 | `PAUSED` | 否 | 显示"连接失败，点击重试" |
| `RECONNECTING` | 网络从 offline 变为 online | `CONNECTING` | — | 显示"连接中" |
| `RESTORING` | 必要订阅全部确认且 HTTP 回补完成 | `OPEN` | — | 显示"已连接" |
| `RESTORING` | 单个订阅无权限 | `RESTORING`（移除该订阅，继续恢复） | — | 显示"恢复订阅中" |
| `RESTORING` | 连接再次断开 | `RECONNECTING` | 是 | 显示"重连中" |
| `RESTORING` | 认证失败 | `AUTH_FAILED` | 否 | 跳转登录页 |
| `PAUSED` | 用户手动重试 | `CONNECTING` | — | 显示"连接中" |
| `PAUSED` | 网络从 offline 变为 online | `CONNECTING` | — | 显示"连接中" |
| `AUTH_FAILED` | 用户重新登录成功 | `DISCONNECTED` | — | 显示"登录成功，连接中" |
| `FORBIDDEN` | 管理员修复权限后用户手动重试 | `DISCONNECTED` | — | 显示"连接中" |
| `CLOSED` | 用户重新登录 | `DISCONNECTED` | — | 显示"连接中" |

**状态机约束**：

- `AUTH_FAILED` 只能通过用户重新登录退出。
- `FORBIDDEN` 只能通过用户手动重试退出（管理员修复权限或修正 Origin 配置后）。
- `CLOSED` 只能通过用户重新登录或重新打开应用退出。
- `PAUSED` 允许手动重试和网络恢复自动触发。
- 禁止从 `AUTH_FAILED`、`FORBIDDEN`、`CLOSED` 自动转换到 `CONNECTING`。
- `RESTORING` 是 `REFRESHING`/`RECONNECTING` 到 `OPEN` 之间的必经中间状态。收到 `connection.established` 后不会直接进入 `OPEN`，除非是首次连接且没有历史订阅。
- `RESTORING` 中单个订阅无权限不关闭连接，移除该订阅后继续恢复其他订阅。

---

### 7.6 关闭码总表

| 关闭码 | 含义 | close reason（固定机器可读字符串） | 处理方式 | 是否自动重连 |
|:------:|------|------|---------|:----------:|
| 1000 | 正常关闭 | `normal_closure` | 不重连，进入 `CLOSED` | 否 |
| 1001 | 服务离开 | `going_away` | 按退避时间表重连 | 是 |
| 1008 | 协议违规 | `policy_violation` | 不重连，提示协议错误 | 否 |
| 1011 | 服务端错误 | `internal_error` | 按退避时间表重连 | 是 |
| 1012 | 服务重启 | `service_restart` | 按退避时间表重连 | 是 |
| 4401 | Token 过期或认证上下文失效 | `access_token_expired` 或 `authentication_context_invalid` | 执行一次 single-flight refresh | 否（走 Refresh 流程） |
| 4403 | 权限拒绝或账号禁用 | `forbidden` | 不重连，进入 `FORBIDDEN` | 否 |
| 4406 | 协议主版本不支持 | `unsupported_version` | 不重连，提示升级客户端 | 否 |
| 4408 | 心跳超时 | `heartbeat_timeout` | 按退避时间表重连 | 是 |
| 4429 | 频率受限 | `rate_limited` | 等待 `retry_after_ms` 后重连 | 是 |

**重要规定**：

- 4xxx 是应用自定义关闭码。
- 握手失败使用 HTTP 响应，不使用关闭码。
- 所有 close reason 必须是固定机器可读字符串，不得使用自由文本。
- close reason 不得包含 Token、Cookie、用户隐私或可变信息。
- 用户注销不重连：客户端主动调用 `POST /api/v1/auth/logout` 后，进入 `CLOSED` 状态，不再发起任何连接。
- 4401 和 4403 的区别：4401 表示认证上下文失效（可通过 Refresh 恢复），4403 表示权限拒绝或账号禁用（不可通过 Refresh 恢复）。
- 4401 允许两个固定 reason：`access_token_expired`（access_token 自然过期）和 `authentication_context_invalid`（session/token family 被撤销或认证上下文失效）。两种 reason 的客户端恢复流程相同：尝试一次 single-flight refresh，成功后新建连接，失败后进入 `AUTH_FAILED`。
- 4429 的 `retry_after_ms` 不写入 close reason。服务端在关闭 4429 前尽可能发送一个 `error` 事件，`error.data` 中包含 `code: WS_RATE_LIMITED`、`retryable: true`、`retry_after_ms`（正整数）。客户端收到后保存 `retry_after_ms`，随后收到 4429 时等待该时间再重连。如果没有收到 `retry_after_ms`，使用默认 30000 毫秒。`retry_after_ms` 必须限制在合理范围：1000～300000 毫秒。

---

### 7.7 心跳机制详细定义

**心跳参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| 客户端 ping 间隔 | 30 秒 | 客户端每 30 秒发送 `ping` |
| 服务端 pong 响应超时 | 10 秒 | 服务端应在 10 秒内返回 `pong` |
| 心跳失败阈值 | 连续 2 次 | 连续两次未收到 `pong`，客户端主动关闭连接 |
| 心跳超时关闭码 | 4408 | `reason=heartbeat_timeout` |
| ping/pong 数据 | 空 | ping/pong 不得携带用户数据 |
| pong 关联 | `request_id` | pong 必须关联原 ping 的 `request_id` |

**心跳计时器清理规则**：

心跳计时器必须在以下所有场景中清理，防止内存泄漏和无效回调：

1. **连接断线**：检测到连接断开时，立即清理心跳计时器。
2. **Refresh 刷新**：进入 `REFRESHING` 状态时，清理旧连接的心跳计时器。
3. **旧连接替换**：新连接成为活动连接后，清理旧连接的心跳计时器。
4. **页面销毁**：监听 `beforeunload` 或 `pagehide` 事件，页面销毁时清理所有心跳计时器。
5. **状态机转换到 `CLOSED`/`AUTH_FAILED`/`FORBIDDEN`**：进入这些终态时清理心跳计时器。

---

### 7.8 重新订阅

连接断开重连或 Refresh 后建立新连接时，客户端必须重新订阅之前活跃的会话。重新订阅遵循以下规则：

1. **客户端只保存 `conversation_id`**：客户端本地只保存订阅的 `conversation_id` 列表，不保存事件正文。事件是瞬时的，不作为恢复数据源。
2. **收到 `connection.established` 后才能重订阅**：必须等待新连接的 `connection.established` 事件后，才能发送 `conversation.subscribe`。
3. **按顺序发送 `conversation.subscribe`**：逐项发送订阅请求，不并行批量发送。
4. **每项等待 `conversation.subscribed` 确认**：每发送一个订阅请求后，等待对应的 `conversation.subscribed` 确认再发送下一个。
5. **服务端重新鉴权**：服务端对每个订阅请求重新校验当前用户是否为会话参与者。权限可能在断开期间发生变化（如被移出会话）。
6. **无权限项从本地订阅集合移除**：如果服务端返回订阅失败（权限不足），客户端从本地订阅集合中移除该 `conversation_id`，不保留无效订阅。
7. **单项失败不关闭整个连接**：单个会话订阅失败不会导致整个 WebSocket 连接关闭。客户端继续处理剩余订阅。
8. **全部完成后才切换活动连接**：所有必要订阅恢复完成后，新连接才正式成为活动连接，旧连接在此之后才被关闭。

**重新订阅与 HTTP 回补的关系**：

- 重新订阅恢复的是实时事件推送通道。
- 断开期间遗漏的消息通过 HTTP 回补获取（见 6.3）。
- 两者独立执行：先完成重新订阅，再触发 HTTP 回补。

---

## 8. 版本策略

### 8.1 协议主版本

1. MVP 协议主版本固定为 `v1`。
2. 客户端命令和服务端事件都必须带 `version` 字段。
3. 客户端必须忽略自己不认识的"可选字段"。
4. 客户端收到未知事件名时：
   - 不得崩溃
   - 不得执行未知操作
   - 安全忽略并记录脱敏指标

### 8.2 非破坏性变更

以下属于非破坏性变更，不需要升级主版本：

- 新增可选字段
- 新增客户端可以安全忽略的服务端事件
- 扩展明确声明为开放集合的安全枚举

### 8.3 破坏性变更

以下属于破坏性变更：

- 删除字段
- 重命名字段
- 修改字段类型
- 将可选字段改为必填
- 修改字段含义
- 修改 `sequence`、`event_id`、`request_id` 的语义
- 收紧已有枚举导致旧值失效

### 8.4 破坏性变更流程

1. 破坏性变更必须升级主版本：`v1` → `v2`
2. 同时支持旧版本（至少 2 周并行支持期）
3. 2 周兼容期只表示旧主版本的最低并行支持时间，不能替代主版本升级
4. 通知前端团队
5. 更新文档
6. 更新客户端类型
7. 更新 Mock
8. 更新测试
9. 通过 ADR 或正式变更记录

### 8.5 不支持的主版本

- 如果连接已经建立，发送安全 `error` 事件后使用 4406 + `unsupported_version` 关闭
- 不允许静默降级到未知协议

### 8.6 冻结后约束

- `v1` 冻结后，不得在没有变更记录的情况下修改必填字段。
- 任何破坏性变更必须同步更新：
  - `WEBSOCKET_CONTRACT.md`
  - 相关 API 文档
  - 客户端类型
  - Mock
  - 测试
  - ADR 或正式变更记录

---

## 9. 事件级隐私投影规则

### 9.1 核心原则

1. WebSocket 不是绕过 HTTP 权限检查的数据通道。
2. 连接认证成功不代表可以接收所有资源事件。
3. conversation 事件必须经过会话参与者授权。
4. scene 事件必须经过场景参与者授权。
5. notification 只能发送给通知所有者。
6. 公共场景事件不得包含 P2、P3、P4 数据。
7. 所有 WebSocket 事件禁止包含：
   - 原始私有偏好
   - 偏好胶囊
   - 私有评价
   - 记忆正文
   - 心理数据
   - 智能体内部推理
   - chain-of-thought
   - system prompt
   - 模型原始输入输出
   - Token、Cookie、认证凭据
8. 日志不得记录完整事件 `data`。
9. 日志只允许记录：
   - `event`
   - `event_id`
   - `request_id`
   - `connection_id`
   - `sequence`
   - 脱敏错误码
   - `payload_size`
   - `duration`
10. 错误事件不得回显原始输入。
11. 订阅权限撤销后立即停止推送。
12. HTTP API 与 WebSocket 数据冲突时，以 HTTP API 为准。

### 9.2 事件数据分类标注

| 事件类别 | 数据级别 | 说明 |
|----------|---------|------|
| `connection.established`、`connection.expiring`、`connection.expired` | P0/P1 元数据 | 连接元信息，不含用户业务数据 |
| `ping`、`pong` | P0 元数据 | 心跳，不含任何业务数据 |
| `error` | P0 元数据 | 错误码和脱敏信息 |
| `conversation.subscribed`、`conversation.unsubscribed` | P0/P1 元数据 | 订阅确认 |
| `message.created`、`message.deleted` | 授权会话投影 | `message.created` 使用扁平字段映射 HTTP Message 模型；`visibility=PRIVATE`/`HIDDEN`、Agent 私域消息、P3/P4 数据、记忆正文和智能体内部推理均不得推送；`content` 可以是 P1/P2 的授权会话可见内容，但不能是 P3/P4；WebSocket Schema 中不存在 `metadata` 字段 |
| `conversation.updated`、`participant.joined`、`participant.left` | 仅授权会话投影 | 只推送给仍具有该会话访问权的订阅者 |
| `scene.updated` | P0/P1 公共进度投影 | `state` 与 `SCENE_STATE_MACHINE.md` 一致；只包含进度数字，不含个人偏好 |
| `scene.result.generated` | P0/P1 最小结果可用通知 | `state` 固定 `CANDIDATES_READY`；只通知结果可用，不推送结果详情 |
| `notification.created` | 当前用户授权投影 | 只发送给通知所有者对应的连接 |

### 9.3 WebSocket 失败关闭规则（R1-30）

与 THREAT_MODEL.md §4.3 FC-008 对齐，以下规则强制实施：

1. **握手失败不建立连接**：access_token 缺失、过期或无效时返回 HTTP 401/403，不建立 WebSocket 连接
2. **Origin 失败不建立连接**：Origin 不在白名单时返回 HTTP 403（`WS_ORIGIN_NOT_ALLOWED`），不建立连接
3. **用户被冻结不建立连接**：账号被禁用时返回 HTTP 401（`AUTH_ACCOUNT_DISABLED`），不建立连接
4. **token 过期后停止推送**：access_token 过期后发送 `connection.expired` 事件并使用 4401 关闭，不继续推送业务事件
5. **订阅资源授权失败返回 error**：订阅未授权 conversation/scene 时返回 `error` 事件（`WS_FORBIDDEN`），不推送该资源事件
6. **回补期间权限撤销停止回补**：HTTP 回补时发现权限已撤销，停止回补该资源，不回补未授权消息
7. **断线重连后重新做资源级授权**：重连后服务端重新校验每个订阅权限，无权限的订阅从本地集合移除，不沿用旧订阅权限
8. **不得通过 WebSocket 执行业务写操作**：WebSocket 只用于事件推送和订阅管理，不承载创建、更新、删除等业务写操作
9. **不得推送 P3/P4 数据**：所有 WebSocket 事件禁止包含 P3/P4 数据（见 §9.1 第 6-7 条）
10. **不得推送非法模型输出**：模型输出校验失败时不通过 WebSocket 推送（与 FC-007 对齐）
11. **不得把订阅失败解释为空数据**：订阅失败返回 `error` 事件，不返回 `success=false` 或空结果

---

## 10. 事件清单

### 10.1 完整事件清单

| 事件名 | 方向 | 触发者 | 授权/订阅条件 | request_id 规则 | 数据分类 | Schema 章节 |
|--------|------|--------|-------------|----------------|---------|------------|
| `conversation.subscribe` | 客户端→服务端 | 客户端 | 连接已认证 + 会话参与者 | 客户端生成 | P1 | §3.1 |
| `conversation.unsubscribe` | 客户端→服务端 | 客户端 | 连接已认证 | 客户端生成 | P1 | §3.2 |
| `ping` | 客户端→服务端 | 客户端 | 连接已建立 | 客户端生成 | P0 元数据 | §3.3 |
| `connection.established` | 服务端→客户端 | 服务端 | 握手认证通过 | `null` | P0/P1 元数据 | §4.1.1 |
| `connection.expiring` | 服务端→客户端 | 服务端 | 连接处于 OPEN/RESTORING | `null` | P0/P1 元数据 | §4.1.2 |
| `connection.expired` | 服务端→客户端 | 服务端 | 连接尚未关闭 | `null` | P0/P1 元数据 | §4.1.3 |
| `conversation.subscribed` | 服务端→客户端 | 服务端 | 会话参与者 | 回显客户端 | P0/P1 元数据 | §4.2.1 |
| `conversation.unsubscribed` | 服务端→客户端 | 服务端 | 连接已认证 | 回显客户端 | P0/P1 元数据 | §4.2.2 |
| `pong` | 服务端→客户端 | 服务端 | 连接已建立 | 回显客户端 | P0 元数据 | §4.2.3 |
| `message.created` | 服务端→客户端 | 服务端 | 已订阅该会话 + 仍为参与者 | `null` | 授权会话投影 | §4.3.1 |
| `message.deleted` | 服务端→客户端 | 服务端 | 已订阅该会话 + 仍为参与者 | `null` | 授权会话投影 | §4.3.2 |
| `conversation.updated` | 服务端→客户端 | 服务端 | 已订阅该会话 + 仍为参与者 | `null` | 授权会话投影 | §4.4.1 |
| `participant.joined` | 服务端→客户端 | 服务端 | 已订阅该会话 + 仍为参与者 | `null` | 授权会话投影 | §4.4.2 |
| `participant.left` | 服务端→客户端 | 服务端 | 已订阅该会话 + 仍为参与者 | `null` | 授权会话投影 | §4.4.3 |
| `scene.updated` | 服务端→客户端 | 服务端 | 场景参与者 | `null` | P0/P1 公共进度 | §4.5.1 |
| `scene.result.generated` | 服务端→客户端 | 服务端 | 场景参与者 | `null` | P0/P1 最小通知 | §4.5.2 |
| `notification.created` | 服务端→客户端 | 服务端 | 通知所有者 | `null` | 当前用户授权投影 | §4.6.1 |
| `error` | 服务端→客户端 | 服务端 | 连接已建立 | 回显或 `null` | P0 元数据 | §4.7.1 |

### 10.2 事件清单一致性约束

- 事件清单中的每个事件必须在正文有完整 Schema。
- 正文定义的每个事件也必须出现在清单。
- 所有 JSON 示例必须包含完整信封字段。
- 客户端命令必须包含 `version`、`request_id`、`timestamp`。
- 服务端事件必须包含 `version`、`event_id`、`sequence`、`timestamp`、`request_id`。
- `scene.completed` 不作为独立事件：场景完成状态由 `scene.updated` 的 `state=COMPLETED` 表达。

---

## 11. 相关文档

- [HTTP API 契约](./API_CONTRACT.md)
- [领域词汇表](../domain/DOMAIN_VOCABULARY.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)
- [数据清单](../architecture/DATA_INVENTORY.md)
- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [认证方式 ADR](../decisions/0003-authentication.md)

---

**变更记录**：

| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
| 2026-07-15 | R1-23 补全：浏览器握手失败恢复流程（1.8）、事件信封 sequence 字段（2.1）、连接事件定义（4.1）、网络重连退避与 jitter（6.1）、自动重连白名单与禁止清单（6.2）、HTTP 回补完整规则（6.3）、事件去重有界缓存（6.4）、Refresh 连接迁移 10 步（7.4.3）、连接状态机 10 状态（7.5）、关闭码补全（7.6）、心跳计时器清理规则（7.7）、重新订阅 8 条规则（7.8） | - |
| 2026-07-15 | R1-23 复审整改：修正 connection.expiring 字段（删除 grace_seconds，统一为 expires_at/refresh_required/reconnect_required）、新增 connection.expired 事件（§4.1）、新增 RESTORING 状态并修复状态转换（§7.5）、区分 4401 两个 reason（§7.6）、定义 4429 retry_after_ms 来源和默认值（§7.6） | - |
| 2026-07-15 | R1-24 冻结：统一客户端/服务端事件信封（§2.1-2.2）、冻结 sequence 单连接语义（§2.3）、统一 UTC Z 时间格式（§2.4）、冻结全部事件 Schema（§3-§4）、删除 original_event 并冻结 error 事件（§4.7）、冻结版本兼容策略（§8）、新增事件级隐私投影规则（§9）、重构事件清单（§10）、删除 scene.completed 并由 scene.updated 表达完成状态、文档状态从 DRAFT 改为 frozen | - |
| 2026-07-15 | R1-24-C Codex 审计整改：scene.updated 字段名从 `stage` 改为 `state` 并补全 12 状态封闭枚举（§4.5.1）；scene.result.generated 从 `status=COMPLETED` 修正为 `state=CANDIDATES_READY`（§4.5.2）；message.created 从嵌套 `sender` 改为扁平 `sender_type`/`sender_user_id`/`sender_agent_id`，删除 `display_name`，补全 `message_type` 10 值枚举，新增 HTTP 字段映射表（§4.3.1）；`request_id` 统一为 UUID v4，替换所有 `req_*` 示例（§2-§4）；notification.created `type` 改为 WebSocket v1 开放枚举，删除不存在的 HTTP Notification 模型引用和 `MESSAGE_MENTION`（§4.6.1）；删除虚假 P3 metadata 描述（§9.2）；修正 `WS_RATE_LIMITED` 分类重叠和错误事件章节引用 §5→§4.7 | - |
| 2026-07-15 | R1-30 新增 §9.3 WebSocket 失败关闭规则（11 条规则，与 THREAT_MODEL.md §4.3 FC-008 对齐）；未修改事件 Schema；未修改关闭码总表 | - |
| 2026-07-15 | R1-31 确认 WebSocket dedupe buffer 口径（1000条/24h，§6.4）与 DATA_INVENTORY.md §13 R1-31 权威口径一致；确认回补以 HTTP API 为事实来源；未修改事件 Schema；未修改关闭码总表；未新增端点 | - |
