# R1-19 任务日志：定义 CSRF 防护方案

> **任务编号**：R1-19
> **执行日期**：2026-07-14
> **执行人**：Claude
> **任务目标**：为所有浏览器端写请求（POST/PATCH/PUT/DELETE）定义 CSRF 防护方案

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：定义 CSRF 方案
- **具体操作**：Token 来源、Header、轮换和失败响应
- **完成标准**：所有 Cookie 写请求具有明确 CSRF 防护

### 前置条件验证

✅ R1-18 已完成：浏览器认证方式统一为 HttpOnly Secure SameSite Cookie + JWT
✅ ADR-003 已存在：`docs/decisions/0003-authentication.md`（状态：Accepted）
✅ API_CONTRACT.md v1.0-frozen：71 个端点已文档化

### 阅读的权威文档

1. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
2. ✅ docs/decisions/0003-authentication.md - ADR-003（认证方式决策）
3. ✅ docs/security/THREAT_MODEL.md - 威胁模型
4. ✅ docs/privacy/PRIVACY_BASELINE.md - 隐私基线
5. ✅ development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md - R1-18 完成记录
6. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划

## 执行过程

### 1. 现状分析

#### 1.1 现有 CSRF 防护

**当前状态**：
- Section 1.5.5 Cookie 属性定义中提到 `SameSite=Lax` 可防止 CSRF
- 无明确的 CSRF Token 机制定义
- 无 CSRF 错误码定义
- 端点错误码清单中无 CSRF 相关错误码

**问题**：
1. `SameSite=Lax` 仅提供部分保护（同站导航携带 Cookie，跨站 POST 不携带）
2. 缺少显式的 CSRF Token 校验机制
3. 缺少 CSRF 豁免规则定义
4. 缺少 CSRF 错误响应定义

#### 1.2 威胁模型分析

**威胁模型**（THREAT_MODEL.md）：
- T-06：横向访问（A 读取 B 的数据）
- CSRF 攻击路径：恶意网站诱导已登录用户执行非预期操作

**缓解措施**：
- Double-Submit Cookie 模式
- SameSite=Lax 作为纵深防御
- Bearer Token 内部服务豁免 CSRF

### 2. CSRF 方案设计

#### 2.1 CSRF Token 来源

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

#### 2.2 强制 CSRF 校验的请求

| HTTP 方法 | 范围 | 说明 |
|-----------|------|------|
| `POST` | 所有浏览器端 POST | 创建资源、执行操作 |
| `PATCH` | 所有浏览器端 PATCH | 更新资源 |
| `PUT` | 所有浏览器端 PUT | 替换资源（MVP 未使用，预留） |
| `DELETE` | 所有浏览器端 DELETE | 删除资源 |

**判断规则**：
- 请求通过 Cookie 认证（非 Bearer）→ 必须校验 CSRF
- 请求通过 Bearer 认证（内部服务）→ 跳过 CSRF 校验
- 请求为 GET/HEAD/OPTIONS → 跳过 CSRF 校验（只读操作）

#### 2.3 CSRF 豁免请求

| 请求类型 | 豁免原因 |
|----------|---------|
| `GET`、`HEAD`、`OPTIONS` | 只读操作，不改变服务端状态 |
| Bearer Token 认证的请求 | 内部服务间调用，不通过 Cookie 认证 |
| WebSocket 握手（GET /ws/v1） | WebSocket 使用一次性 ticket，非 Cookie 认证 |
| 静态资源请求（`/static/*`、`/favicon.ico`） | 不涉及 API 认证 |

**WebSocket 握手特别说明**：
- 当前：`GET /ws/v1?ticket=<one_time_ticket>`（R1-22 将改为 Cookie）
- WebSocket 握手通过 ticket 认证，不使用 Cookie
- SameSite=Lax 已阻止跨站 WebSocket 连接携带 Cookie
- 豁免 CSRF 校验，但保留 ticket 过期检查（待 R1-23 实现）

#### 2.4 CSRF 校验失败响应

| 场景 | HTTP 状态码 | 错误码 | message |
|------|:----------:|--------|---------|
| 缺少 `X-CSRF-Token` 请求头（写请求） | 403 | `CSRF_TOKEN_MISSING` | 缺少 CSRF Token，请刷新页面后重试 |
| `X-CSRF-Token` 与 `csrf_token` Cookie 值不匹配 | 403 | `CSRF_TOKEN_MISMATCH` | CSRF Token 不匹配，请刷新页面后重试 |
| `csrf_token` Cookie 已过期（可选增强） | 403 | `CSRF_TOKEN_EXPIRED` | CSRF Token 已过期，请重新登录 |

**前端处理**：
- `CSRF_TOKEN_MISSING` / `CSRF_TOKEN_MISMATCH`：页面刷新（Token 已失效）
- `CSRF_TOKEN_EXPIRED`：跳转到登录页（重新登录刷新 Token）

#### 2.5 CSRF Token 生命周期

| 事件 | CSRF Token 行为 |
|------|----------------|
| 用户登录（POST /api/v1/auth/login） | 生成新的 `csrf_token` Cookie |
| Token 刷新（POST /api/v1/auth/refresh） | 保持 `csrf_token` 不变（或选择刷新） |
| 用户注销（POST /api/v1/auth/logout） | 清除 `csrf_token` Cookie（Max-Age=0） |
| Token 过期（access_token 过期） | `csrf_token` 保留但失效（前端应跳转登录） |

### 3. 实施变更

#### 3.1 API_CONTRACT.md 变更

1. **Section 1.5.6 CSRF 防护方案**（新增）：
   - 1.5.6.1 CSRF Token 来源（Double-Submit Cookie 模式）
   - 1.5.6.2 强制 CSRF 校验的请求（POST/PATCH/PUT/DELETE）
   - 1.5.6.3 CSRF 豁免请求（GET/HEAD/OPTIONS/Bearer/WebSocket）
   - 1.5.6.4 CSRF 校验失败响应（403 + 3 个错误码）
   - 1.5.6.5 CSRF Token 生命周期
   - 1.5.6.6 参考

2. **Section 1.6.2 错误分类与 HTTP 状态码映射**（新增 CSRF 分类）：
   - `csrf`：`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH`、`CSRF_TOKEN_EXPIRED` | 403

3. **Section 1.6.3 错误码总表**（新增 CSRF 错误码）：
   - `CSRF_TOKEN_MISSING` - 403 - 缺少 CSRF Token
   - `CSRF_TOKEN_MISMATCH` - 403 - CSRF Token 不匹配
   - `CSRF_TOKEN_EXPIRED` - 403 - CSRF Token 已过期

4. **Section 1.6.6 端点错误码清单**（新增 CSRF 校验规则）：
   - 所有写端点（POST/PATCH/PUT/DELETE）添加 `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH`
   - 豁免端点（GET/HEAD/OPTIONS）不添加
   - 内部端点（`/internal/v1/*`）不添加

5. **端点错误码更新统计**：
   - Auth：5 个端点（3 个写端点 + 1 个登出 + 1 个获取）
   - User：1 个写端点（PATCH）
   - Organization：7 个写端点（POST/PATCH/DELETE × 多个）
   - Conversation：5 个写端点（POST/PATCH/DELETE × 多个）
   - Agent：4 个写端点（PATCH/POST × 多个）
   - Memory：3 个写端点（POST/PATCH/DELETE/export）
   - Scene：8 个写端点（POST × 多个 + PATCH/DELETE）
   - Admin：5 个写端点（POST/PATCH/DELETE/health-check）

#### 3.2 P0_P1_REMEDIATION_PLAN.md 变更

1. **R1-19 状态**：`[ ]` → `[x]`
2. **返工说明**：新增 R1-19 完成说明

## 验证检查

### 3.1 CSRF 防护覆盖检查

| 端点类型 | CSRF 校验 | 状态 |
|----------|:---------:|------|
| 浏览器端 POST | ✅ 强制 | 所有 POST 端点已添加错误码 |
| 浏览器端 PATCH | ✅ 强制 | 所有 PATCH 端点已添加错误码 |
| 浏览器端 DELETE | ✅ 强制 | 所有 DELETE 端点已添加错误码 |
| 浏览器端 GET | ❌ 豁免 | 无 CSRF 错误码 |
| Bearer Token 内部服务 | ❌ 豁免 | 无 CSRF 错误码 |
| WebSocket 握手 | ❌ 豁免 | 无 CSRF 错误码 |

### 3.2 CSRF 错误码一致性检查

| 错误码 | HTTP | 错误分类 | 出现位置 |
|--------|:----:|---------|---------|
| `CSRF_TOKEN_MISSING` | 403 | `csrf` | 通用 |
| `CSRF_TOKEN_MISMATCH` | 403 | `csrf` | 通用 |
| `CSRF_TOKEN_EXPIRED` | 403 | `csrf` | 通用 |

### 3.3 端点错误码统计

**写端点（CSRF 校验）**：
- Auth：3 个（register、login、refresh）+ logout
- User：1 个（PATCH /users/{user_id}）
- Organization：7 个
- Conversation：5 个
- Agent：4 个
- Memory：3 个
- Scene：8 个
- Admin：5 个

**总计**：36 个写端点已添加 CSRF 错误码

**豁免端点（无 CSRF）**：
- GET 端点：~30 个
- Bearer Token 内部端点：3 个（`/internal/v1/*`）

## 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/API_CONTRACT.md | Section 1.5.6 新增 | CSRF 防护方案（6 个小节） |
| docs/api/API_CONTRACT.md | Section 1.6.2 更新 | 新增 `csrf` 错误分类 |
| docs/api/API_CONTRACT.md | Section 1.6.3 更新 | 新增 3 个 CSRF 错误码 |
| docs/api/API_CONTRACT.md | Section 1.6.6 更新 | 新增 CSRF 校验规则 + 36 个写端点添加 CSRF 错误码 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-19：`[ ]` → `[x]` |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明 | 添加 R1-19 完成说明 |

## 验收结果

### 4.1 验收检查清单

- [x] CSRF Token 来源定义（非 HttpOnly `csrf_token` Cookie + `X-CSRF-Token` 请求头）
- [x] 强制 CSRF 请求范围定义（POST/PATCH/PUT/DELETE）
- [x] 豁免请求规则定义（GET/HEAD/OPTIONS、Bearer Token、WebSocket、静态资源）
- [x] CSRF 校验失败响应定义（403 + 3 个错误码）
- [x] 3 个 CSRF 错误码加入 API_CONTRACT 错误码总表（Section 1.6.3）
- [x] 3 个 CSRF 错误码加入错误分类映射（Section 1.6.2）
- [x] 36 个写端点错误码清单添加 CSRF 错误码（Section 1.6.6）
- [x] CSRF Token 生命周期定义（登录/刷新/注销/过期）
- [x] 前端伪代码和后端校验伪代码提供
- [x] 豁免规则明确（内部服务、WebSocket ticket、静态资源）
- [x] P0_P1_REMEDIATION_PLAN.md 已更新
- [x] 任务日志已归档

### 4.2 CSRF 错误码总结

| 错误码 | HTTP | message | retryable |
|--------|:----:|---------|:---------:|
| `CSRF_TOKEN_MISSING` | 403 | 缺少 CSRF Token，请刷新页面后重试 | false |
| `CSRF_TOKEN_MISMATCH` | 403 | CSRF Token 不匹配，请刷新页面后重试 | false |
| `CSRF_TOKEN_EXPIRED` | 403 | CSRF Token 已过期，请重新登录 | false |

### 4.3 待后续任务完善

- R1-20：修正登录响应格式
- R1-21：修正 Refresh 流程（Token 旋转、撤销）
- R1-22：WebSocket 鉴权修正（URL Token → Cookie）
- R1-23：定义 WebSocket Token 过期
- R2 阶段：后端实现 CSRF 中间件

## 下一步

R1-19 已完成，R1 批次剩余任务：
- R1-20：修正登录响应格式
- R1-21：修正 Refresh 流程
- R1-22：修正 WebSocket 鉴权
- R1-23：定义 WebSocket Token 过期
- R1-24：冻结事件 Schema
- R1-25：修正威胁编号
- R1-26：修正威胁数量

可继续执行 R1-20 或进入 R4 验收（前提：R1-20～R1-26 全部完成）

## 备注

**R1-19 与 R1-18/R1-22 的关系**：
- R1-18 冻结浏览器认证方式（Cookie + JWT）
- R1-19 定义 CSRF 防护方案（Cookie 写请求）
- R1-22 修正 WebSocket 鉴权（URL Token → Cookie）
- R1-19 为 R1-22 提供基础（CSRF 豁免规则已定义）

## R1-C 认证/CSRF 契约复审整改（2026-07-15）

### 整改原因

R1-19 初版定义 CSRF 方案时，存在以下问题：
1. **CSRF 首次启动链路矛盾**：login/register 端点要求 CSRF Token，但此时客户端尚未持有 csrf_token Cookie（Chicken-and-Egg 问题）
2. **register 端点缺少 csrf_token Cookie**：register 自动登录后应和 login 一样设置 csrf_token
3. **CSRF_TOKEN_EXPIRED 进入 MVP**：MVP 阶段应简化，仅使用 MISSING/MISMATCH

### 整改内容

1. **明确 CSRF 豁免范围**：login/register 为未认证端点，豁免 CSRF 校验
2. **CSRF Bootstrap 流程**：login/register 成功后一次性签发 access_token + refresh_token + csrf_token，前端从 Cookie 读取 csrf_token 用于后续写请求
3. **CSRF_TOKEN_EXPIRED 降级为可选增强**：标记为 P2 实现，MVP 阶段不进入端点错误码清单
4. **register 增加 csrf_token Cookie**：注册成功后自动登录，前端可读取 csrf_token 用于后续写请求

### 整改后 CSRF 校验规则

| 请求类型 | CSRF 校验 | 错误码 |
|----------|:---------:|--------|
| Cookie 已认证的浏览器端 POST/PATCH/PUT/DELETE | ✅ 必须 | `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| 未认证端点（login/register） | ❌ 豁免 | 无 |
| Bearer Token 内部服务 | ❌ 豁免 | 无 |
| GET/HEAD/OPTIONS | ❌ 豁免 | 无 |
| WebSocket 握手 | ❌ 豁免 | 无 |

### API_CONTRACT.md 变更记录

已在 API_CONTRACT.md 变更记录中增加：
- R1-C：认证/CSRF 契约复审修订，明确 CSRF bootstrap、register 自动登录 csrf_token、auth 端点 CSRF 豁免范围

### 关联任务

- R1-20：登录响应已包含 csrf_token Cookie（保持一致）
- R1-21：Refresh/Logout 端点已包含 CSRF 错误码（保持一致）

## R1-22 WebSocket 鉴权说明（历史状态标注）

本日志中提到的 `GET /ws/v1?ticket=<one_time_ticket>` 和 WebSocket 使用一次性 ticket 为 R1-19 完成时的历史状态。

R1-22 已修正 WebSocket 鉴权：
- 路径改为 `/api/v1/ws`
- 认证方式改为 `access_token` HttpOnly Cookie
- 禁止 URL Token 和 ticket
- 强制 Origin 白名单校验

当前有效契约以 `WEBSOCKET_CONTRACT.md` 和 `API_CONTRACT.md` 为准。
