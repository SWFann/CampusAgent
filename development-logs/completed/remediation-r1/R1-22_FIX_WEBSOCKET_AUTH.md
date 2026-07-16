# R1-22 任务日志：修正 WebSocket 鉴权

> **任务编号**：R1-22
> **执行日期**：2026-07-15
> **执行人**：Claude
> **状态**：等待 Codex 审计

## 任务目标

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：修正 WebSocket 鉴权
- **具体操作**：禁止长期 Token 出现在 URL 查询参数
- **完成标准**：采用安全 Cookie 认证

### 前置条件验证

✅ R1-18 已完成：浏览器认证方式统一为 HttpOnly Secure SameSite Cookie + JWT
✅ R1-19 已完成：CSRF 防护方案定义（Double-Submit Cookie 模式）
✅ R1-20 已完成：登录响应修正（Set-Cookie + csrf_token）
✅ R1-21 已完成：Refresh 流程修正（Token 轮换、撤销）
✅ API_CONTRACT.md v1.0-frozen：71 个端点已文档化
✅ ADR-003：JWT + HttpOnly Cookie

### 阅读的权威文档

1. ✅ docs/api/WEBSOCKET_CONTRACT.md - WebSocket 契约（当前状态）
2. ✅ docs/api/API_CONTRACT.md - HTTP API 契约
3. ✅ docs/decisions/0003-authentication.md - ADR-003（认证方式决策）
4. ✅ docs/privacy/PRIVACY_BASELINE.md - 隐私基线
5. ✅ docs/security/THREAT_MODEL.md - 威胁模型
6. ✅ docs/product/MVP_SCOPE.md - MVP 范围定义
7. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
8. ✅ development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md - R1-18 完成记录
9. ✅ development-logs/completed/remediation-r1/R1-19_DEFINE_CSRF_SCHEME.md - R1-19 完成记录
10. ✅ development-logs/completed/remediation-r1/R1-21_FIX_REFRESH_FLOW.md - R1-21 完成记录

## 原始风险

### 1. URL Token 风险

**当前不安全设计**：

```
ws://localhost:8000/ws/v1?token=<access_token>
```

**风险**：
1. Token 出现在 URL 查询参数中，可能被服务器日志记录
2. Token 出现在浏览器历史记录中
3. Token 可能被 Referer 头泄露
4. Token 长期有效（1 小时），一旦泄露攻击窗口大
5. JavaScript 需要读取 Token 并写入 URL，破坏 HttpOnly 防护

### 2. Ticket 端点风险

**替代方案**：`GET /auth/ws-ticket`

**风险**：
1. 需要新增 HTTP 端点，增加攻击面
2. 需要维护 ticket 的颁发和验证逻辑
3. 与既有 Cookie 体系重复
4. 增加客户端复杂度

### 3. 连接后发送 Token 风险

**替代方案**：连接成功后发送 `access_token`

**风险**：
1. JavaScript 需要读取 HttpOnly Cookie 中的 Token（不可能）
2. 或者 Token 存储在 localStorage/sessionStorage（XSS 风险）
3. 连接建立后的一段时间内无认证，可能被滥用

## 最终选择方案

### 采用 Cookie 认证

**方案**：

```
wss://<host>/api/v1/ws
```

**认证凭据**：`access_token` HttpOnly Cookie

**为什么选择此方案**：
1. 复用既有 JWT + HttpOnly Cookie 体系
2. 不需要新增 HTTP 端点
3. 不需要 JavaScript 读取 Token
4. 浏览器原生 WebSocket API 自动携带 Cookie
5. Token 不出现在 URL 中
6. 与 HTTP API 认证方式一致

### 为什么不使用 URL Token

1. Token 出现在 URL 查询参数中，可能被日志记录
2. Token 可能被 Referer 头泄露
3. 破坏 HttpOnly 防护（JavaScript 需要读取 Token）
4. 与 R1-18 冻结的 Cookie 认证方案冲突

### 为什么不新增 ticket 端点

1. 需要新增 HTTP 端点，增加攻击面
2. 与既有 Cookie 体系重复
3. 需要维护 ticket 的颁发和验证逻辑
4. 增加客户端复杂度

### 为什么选择 /api/v1/ws

1. `access_token` Cookie 的 `Path=/api/v1`
2. `/api/v1/ws` 在 Cookie 作用域内
3. 可以复用现有 HttpOnly Cookie
4. 不需要扩大 Cookie Path 到 `/`
5. 不需要新增 ticket 端点
6. 路径与 HTTP API 保持一致性

## 执行过程

### 1. WEBSOCKET_CONTRACT.md 重写

**Section 1 重写**：

1. **1.1 连接地址**：
   - 生产：`wss://<host>/api/v1/ws`
   - 本地开发：`ws://localhost:8000/api/v1/ws`
   - 路径说明：`/api/v1/ws` 在 `access_token` Cookie 的 `Path=/api/v1` 作用域内

2. **1.2 认证**：
   - 使用 `access_token` HttpOnly Cookie
   - 认证流程：浏览器发起 GET Upgrade → 自动携带 Cookie → 服务端校验 Origin → 读取 Cookie → 校验 JWT → 101 Switching Protocols
   - 禁止的形式：URL Token、ticket、连接后发送 Token、localStorage

3. **1.3 Origin 校验**：
   - 服务端维护 Origin 白名单
   - 生产仅允许正式 Web 前端 Origin
   - 本地开发只允许显式配置的 localhost Origin
   - 缺少/不匹配/null 默认拒绝
   - 不允许通配符 `*`

4. **1.4 握手失败响应**：
   - 401：Token 缺失/无效/过期/撤销
   - 403：用户被冻结/Origin 不匹配
   - 503：服务异常

5. **1.5 CSRF 关系**：
   - WebSocket 握手是 GET Upgrade，不使用 X-CSRF-Token
   - 依靠 SameSite Cookie、Origin 白名单、JWT 校验防护
   - 业务写操作继续走 HTTP API + CSRF

6. **1.6 订阅授权**：
   - 连接认证成功不代表可以订阅所有会话
   - conversation.subscribe 时重新校验参与者身份
   - 禁止猜测 conversation_id 订阅他人会话

7. **1.7 日志和隐私**：
   - 禁止记录：Cookie 原文、JWT 原文、URL 认证凭据、私有消息、P2/P3/P4 数据
   - 允许记录：connection_id、user_id、request_id、Origin 校验结果、握手状态、脱敏错误码、连接时长

**Section 7 连接生命周期更新**：

1. **7.1 连接建立**：更新为 Cookie 认证流程
2. **7.4 Token 过期**：标记为"待 R1-23 定义"

### 2. API_CONTRACT.md 同步

**Section 1.5.6.3 WebSocket 豁免说明更新**：

- 路径：`GET /api/v1/ws`（R1-22 已修正为 Cookie）
- 认证：`access_token` Cookie
- 豁免 CSRF 校验
- 强制校验 Origin
- 不使用 URL Token、不使用 ticket
- 不新增 HTTP API
- 68 个 MVP HTTP 端点数量不变

### 3. ADR-003 补充

**新增"WebSocket 认证"小节**：

- WebSocket 复用 access_token HttpOnly Cookie
- 路径：`/api/v1/ws`
- 必须验证 Origin
- 禁止 URL Token
- 禁止前端读取长期 Token
- 认证失败时拒绝协议升级

### 4. P0_P1_REMEDIATION_PLAN.md 更新

- R1-22 状态：`[ ]` → `[x]`
- 增加 R1-22 完成摘要

## 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/WEBSOCKET_CONTRACT.md | Section 1 重写 | 连接地址改为 /api/v1/ws，认证改为 Cookie，新增 Origin 校验、握手失败响应、CSRF 关系、订阅授权、日志隐私 |
| docs/api/WEBSOCKET_CONTRACT.md | Section 7 更新 | 连接建立流程更新，Token 过期标记为待 R1-23 |
| docs/api/API_CONTRACT.md | Section 1.5.6.3 更新 | WebSocket 豁免说明更新为 Cookie 认证 |
| docs/decisions/0003-authentication.md | 补充 | 新增 WebSocket 认证小节 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-22：`[ ]` → `[x]` |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 完成摘要 | 增加 R1-22 完成摘要 |

## 验证检查

### 3.1 WebSocket 路径检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 唯一路径 | ✅ | `/api/v1/ws` |
| 生产地址 | ✅ | `wss://<host>/api/v1/ws` |
| 本地开发地址 | ✅ | `ws://localhost:8000/api/v1/ws` |
| URL 无 token | ✅ | 无 `?token=`、`?ticket=` |
| URL 无 access_token | ✅ | 无 `access_token` |
| URL 无 refresh_token | ✅ | 无 `refresh_token` |

### 3.2 认证方式检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 使用 Cookie | ✅ | `access_token` HttpOnly Cookie |
| 不使用 Authorization 头 | ✅ | 浏览器原生 WebSocket API 无法稳定设置 |
| 不使用 URL Token | ✅ | 无 `?token=` |
| 不使用 ticket | ✅ | 无 `/auth/ws-ticket` 端点 |
| 不使用连接后发送 | ✅ | 无连接后认证阶段 |
| JavaScript 不读取 Token | ✅ | 无 `document.cookie` 读取 access_token |
| 不使用 localStorage | ✅ | 无 localStorage/sessionStorage |

### 3.3 Origin 校验检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 白名单规则 | ✅ | 生产/本地开发分别定义 |
| 缺少 Origin 拒绝 | ✅ | 默认拒绝 |
| Origin 不匹配拒绝 | ✅ | 拒绝 |
| Origin 为 null 拒绝 | ✅ | 拒绝 |
| 不允许通配符 | ✅ | 无 `*` |
| 协议升级前校验 | ✅ | 在 101 前完成 |

### 3.4 握手失败检查

| 场景 | HTTP 状态码 | 状态 |
|--------|:----------:|:----:|
| access_token Cookie 缺失 | 401 | ✅ |
| Token 无效 | 401 | ✅ |
| Token 已过期 | 401 | ✅ |
| Token 已撤销 | 401 | ✅ |
| 用户被冻结或禁用 | 403 | ✅ |
| Origin 缺失或不受信任 | 403 | ✅ |
| 服务异常 | 503 | ✅ |

### 3.5 CSRF 关系检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 握手不使用 X-CSRF-Token | ✅ | GET Upgrade 请求 |
| 业务写操作走 HTTP API | ✅ | 继续使用现有 CSRF 方案 |
| 未来 WebSocket 写命令需单独定义 | ✅ | 已说明 |

### 3.6 订阅授权检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 连接认证 ≠ 订阅授权 | ✅ | 已说明 |
| conversation.subscribe 重新校验 | ✅ | 已说明 |
| 禁止猜测 conversation_id | ✅ | 已说明 |

### 3.7 日志和隐私检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 禁止记录 Cookie 原文 | ✅ | 已说明 |
| 禁止记录 JWT 原文 | ✅ | 已说明 |
| 禁止记录 URL 认证凭据 | ✅ | 已说明 |
| 禁止记录私有消息 | ✅ | 已说明 |
| 禁止记录 P2/P3/P4 数据 | ✅ | 已说明 |
| 允许记录 connection_id | ✅ | 已说明 |
| 允许记录 user_id | ✅ | 已说明 |
| 允许记录 Origin 校验结果 | ✅ | 已说明 |

### 3.8 一致性检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| API_CONTRACT Section 1.5.6.3 更新 | ✅ | WebSocket 豁免说明更新 |
| ADR-003 补充 WebSocket 认证 | ✅ | 新增小节 |
| WEBSOCKET_CONTRACT 仍为 DRAFT | ✅ | 未修改版本状态 |
| R1-23、R1-24 仍为未完成 | ✅ | 未修改状态 |

## 全仓一致性扫描

执行搜索：

```bash
rg -n "\?token=|\?ticket=|token=<access_token>|ticket=<one_time_ticket>|ws://localhost:8000/ws/v1|/ws/v1" README.md docs development-logs --glob "*.md"
```

**结果**：
- 当前有效契约和说明中不再出现旧地址或 URL Token
- 历史日志保留旧内容，但明确标注为"整改前历史状态"
- 已完成任务的历史记录未被擅自重写

## 尚待后续任务

### R1-23：定义 WebSocket Token 过期

- 关闭码定义
- Token 过期时的客户端行为
- 重连策略
- 重新订阅逻辑

### R1-24：冻结事件 Schema

- 所有事件字段定义
- 版本策略
- 公共事件不包含 P2-P4 数据

## 下一步

R1-22 已完成，等待 Codex 审计。

R1 批次剩余任务：
- R1-23：定义 WebSocket Token 过期
- R1-24：冻结事件 Schema
- R1-25：修正威胁编号
- R1-26：修正威胁数量

## 备注

**R1-22 与 R1-18/R1-19/R1-21 的关系**：
- R1-18 冻结浏览器认证方式（Cookie + JWT）
- R1-19 定义 CSRF 防护方案
- R1-21 修正 Refresh 流程（Token 轮换、撤销）
- R1-22 修正 WebSocket 鉴权（Cookie 认证，与 R1-18 一致）

## Codex 审计整改（2026-07-15）

### 整改内容

1. **统一握手失败错误码**：WEBSOCKET_CONTRACT.md Section 1.4 握手失败表中，每种失败场景已映射稳定错误码：
   - Token 相关失败（缺失/无效/过期/撤销）→ 401 + `AUTH_INVALID_TOKEN`
   - 用户被冻结或禁用 → 401 + `AUTH_ACCOUNT_DISABLED`（统一保持 HTTP 401，与 API_CONTRACT.md 一致）
   - Origin 相关失败（缺失/null/不匹配）→ 403 + `WS_ORIGIN_NOT_ALLOWED`
   - 服务异常 → 503 + `SERVICE_UNAVAILABLE`
2. **注册 WS_ORIGIN_NOT_ALLOWED**：API_CONTRACT.md 新增 `websocket` 错误分类，`WS_ORIGIN_NOT_ALLOWED` 已加入统一错误码总表（Section 1.6.3），HTTP 403，message：WebSocket Origin 不在允许列表中，retryable：false，出现位置：WebSocket
3. **完善 SameSite 说明**：WEBSOCKET_CONTRACT.md 中 SameSite 描述从"SameSite=Lax 阻止跨站请求携带 Cookie"调整为"SameSite=Lax 提供纵深防护，但 WebSocket 安全不能只依赖 SameSite；严格 Origin 白名单校验是防止 Cross-Site WebSocket Hijacking 的强制控制"
4. **恢复 ADR 链接**：docs/decisions/0003-authentication.md 相关文档中恢复 `[角色权限矩阵](../../../docs/architecture/PERMISSION_MATRIX.md)` 链接

### 变更内容

- WEBSOCKET_CONTRACT.md：握手失败表新增错误码列，AUTH_ACCOUNT_DISABLED 统一为 401，Origin 失败统一为 WS_ORIGIN_NOT_ALLOWED
- API_CONTRACT.md：Section 1.6.2 新增 websocket 错误分类，Section 1.6.3 新增 WS_ORIGIN_NOT_ALLOWED 错误码，Section 1.6.6 新增 WebSocket 端点错误码
- ADR-003：相关文档恢复角色权限矩阵链接

### 关联任务

- WS_ORIGIN_NOT_ALLOWED 已进入统一错误码总表
- AUTH_ACCOUNT_DISABLED 统一保持 HTTP 401
- SameSite 只作为纵深防护，Origin 校验为强制控制

## Codex 复审修正（2026-07-15）

### 修正内容

1. **AUTH_INVALID_TOKEN 出现位置**：API_CONTRACT.md 错误码总表中从 `Auth` 更新为 `Auth / WebSocket`
2. **AUTH_ACCOUNT_DISABLED 出现位置**：API_CONTRACT.md 错误码总表中从 `Auth` 更新为 `Auth / WebSocket`
3. **SERVICE_UNAVAILABLE 出现位置**：API_CONTRACT.md 错误码总表中从 `Admin / Model Gateway` 更新为 `Admin / Model Gateway / WebSocket`

### 一致性验证

- WebSocket 端点清单（Section 1.6.6）与错误码总表（Section 1.6.3）已一致
- 4 个 WebSocket 错误码的 HTTP 状态与端点定义一致：
  - AUTH_INVALID_TOKEN → 401
  - AUTH_ACCOUNT_DISABLED → 401
  - WS_ORIGIN_NOT_ALLOWED → 403
  - SERVICE_UNAVAILABLE → 503
- 未新增其他错误码或分类
- R1-23、R1-24 保持未完成

### 状态

仍为等待 Codex 复审

## 审计记录

- 审计结论：通过
- WebSocket路径：/api/v1/ws
- 认证方式：HttpOnly access_token Cookie
- R1-23可以开始
- R1-24仍未开始
