# R1-18 任务日志：冻结浏览器认证方式

> **任务编号**：R1-18
> **执行日期**：2026-07-14
> **执行人**：Claude
> **任务目标**：统一浏览器认证方式，解决 API_CONTRACT、ADR、WebSocket 文档中 Bearer Token、HttpOnly Cookie、URL token 混用的问题

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：冻结浏览器认证方式
- **具体操作**：依据 ADR-003 统一为 HttpOnly Cookie 或明确替代方案
- **完成标准**：HTTP 契约与 ADR 一致

### 前置条件验证

✅ R1-17 已完成：API_CONTRACT.md v1.0-frozen
✅ ADR-003 已存在：`docs/decisions/0003-authentication.md`（状态：Accepted）

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
4. ✅ docs/architecture/0003-authentication.md - ADR-003（认证方式决策）
5. ✅ docs/security/THREAT_MODEL.md - 威胁模型
6. ✅ docs/privacy/PRIVACY_BASELINE.md - 隐私基线
7. ✅ docs/api/WEBSOCKET_CONTRACT.md - WebSocket 契约（当前状态）

## 执行过程

### 1. 现状分析

#### 1.1 ADR-003 现状

**文档**：`docs/decisions/0003-authentication.md`

**已决策**：
- 采用 JWT + HttpOnly Cookie
- Access Token：有效期 1 小时，HttpOnly Cookie
- Refresh Token：有效期 7 天，HttpOnly Cookie，单次使用（旋转）

**缺失**：
- Cookie 属性详细定义（Secure、SameSite、Path、Max-Age）
- 开发环境例外说明
- 非浏览器内部调用的认证方式范围

#### 1.2 API_CONTRACT.md 现状

**Section 1.5 鉴权**（当前）：
```
Authorization: Bearer <access_token>
或使用 HttpOnly Cookie。
```

**问题**：
1. 主认证方式不明确（Bearer vs Cookie 并列）
2. 未区分浏览器端和非浏览器端
3. 未定义 Cookie 属性

**登录端点**（当前）：
- 响应体返回 `access_token`、`refresh_token`、`token_type: "Bearer"`
- 前端需要将 Token 存储到 localStorage/sessionStorage

**问题**：
1. Token 返回在响应体中，前端需要手动存储
2. 不符合 ADR-003（Token 应存储在 HttpOnly Cookie 中）
3. 存在 XSS 风险（localStorage 可被 JavaScript 读取）

#### 1.3 WebSocket 契约现状

**WebSocket 连接**（当前）：
```
ws://localhost:8000/ws/v1?token=<access_token>
```

**问题**：
1. Token 通过 URL 查询参数传递（安全风险）
2. 与 R1-18 的 Cookie 方案冲突
3. 待 R1-22 修正

#### 1.4 威胁模型与隐私基线

**威胁模型**（THREAT_MODEL.md）：
- T-05：重放攻击（授权令牌、场景提交）
- T-06：横向访问（A读B）
- T-08：外发敏感数据

**缓解措施**：
- HttpOnly Cookie 防 XSS（窃取 Token）
- Secure Cookie 防中间人攻击
- SameSite Cookie 防 CSRF
- Refresh Token 旋转防重放

**隐私基线**（PRIVACY_BASELINE.md）：
- 敏感访问必须同时明确：who、what、purpose、scope、expiration 和 consent
- Token 是访问控制的依据，必须安全存储

### 2. 统一实施

#### 2.1 Section 1.5 重写

**新增内容**：
1. **1.5.1 Web 浏览器端（主认证方式）**：JWT + HttpOnly Secure SameSite Cookie
2. **1.5.2 非浏览器内部调用（辅助认证方式）**：Bearer Token（仅限内部服务）
3. **1.5.3 认证流程**：登录 → Cookie → 后续请求 → 刷新 → 过期跳转
4. **1.5.4 参考**：ADR-003、R1-19、R1-20

**关键决策**：
- 浏览器端：Cookie（HttpOnly + Secure + SameSite=Lax）
- 内部服务：Bearer Token（Model Gateway）
- 管理后台：Bearer Token（Admin）
- 前端不得将 Token 存入 localStorage/sessionStorage

#### 2.2 端点定义更新

**登录（POST /api/v1/auth/login）**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 响应体 | `access_token`、`refresh_token`、`token_type: "Bearer"` | 用户信息（`id`、`email`、`display_name`、`global_role`） |
| 响应头 | 无 | `Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Lax` |
| 前端存储 | 需要手动存储到 localStorage | 浏览器自动管理（HttpOnly） |

**刷新（POST /api/v1/auth/refresh）**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 请求体 | `{ "refresh_token": "..." }` | 无（从 Cookie 读取） |
| 响应头 | 无 | `Set-Cookie: access_token=...` |
| 认证方式 | Bearer Token | Cookie |

**注销（POST /api/v1/auth/logout）**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 响应头 | 无 | `Set-Cookie: access_token=; Max-Age=0` |
| 服务端行为 | 未定义 | 撤销 refresh_token（加入黑名单） |

**当前用户（GET /api/v1/auth/me）**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 认证方式 | Authorization: Bearer | Cookie: access_token |
| 请求头 | `Authorization: Bearer <token>` | `Cookie: access_token=<jwt>` |

**注册（POST /api/v1/auth/register）**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 响应头 | 无 | `Set-Cookie: access_token=...; refresh_token=...` |
| 说明 | 仅返回 201 Created | Token 通过 Cookie 发放，注册成功后自动登录 |

#### 2.3 Cookie 属性详细定义（Section 1.5.5）

**access_token Cookie**：

| 属性 | 值 | 说明 |
|------|-----|------|
| HttpOnly | true | 禁止 JavaScript 访问（防 XSS） |
| Secure | true | 仅 HTTPS 传输 |
| SameSite | Lax | 跨站请求不携带 Cookie（防 CSRF） |
| Path | `/api/v1` | 仅对 `/api/v1/*` 路径发送 |
| Max-Age | 3600 | 有效期 1 小时 |

**refresh_token Cookie**：

| 属性 | 值 | 说明 |
|------|-----|------|
| HttpOnly | true | 禁止 JavaScript 访问 |
| Secure | true | 仅 HTTPS 传输 |
| SameSite | Lax | 同 access_token |
| Path | `/api/v1/auth` | 仅对 `/api/v1/auth/*` 路径发送（限制暴露面） |
| Max-Age | 604800 | 有效期 7 天 |

**SameSite=Lax 选择理由**：
- 从外部链接点击进入站点时保持登录状态
- 跨站 POST 请求不携带 Cookie，防止 CSRF
- 可升级为 `SameSite=Strict`（更严格，但影响外部链接登录体验）

**开发环境例外**：
- `APP_ENV=development` 允许 `Secure=false`（HTTP 本地开发）
- 生产环境必须 `Secure=true`

### 3. 验证检查

#### 3.1 端点定义一致性

| 端点 | Cookie 设置 | Cookie 读取 | 认证方式 |
|------|-----------|-----------|---------|
| POST /api/v1/auth/register | ✅ Set-Cookie (access + refresh) | - | 公开 |
| POST /api/v1/auth/login | ✅ Set-Cookie (access + refresh) | - | 公开 |
| POST /api/v1/auth/refresh | ✅ Set-Cookie (access) | ✅ Cookie (refresh) | 已认证 |
| POST /api/v1/auth/logout | ✅ Set-Cookie (Max-Age=0) | - | 已认证 |
| GET /api/v1/auth/me | - | ✅ Cookie (access) | 已认证 |

#### 3.2 ADR-003 一致性

| ADR-003 决策 | API_CONTRACT.md 实现 | 状态 |
|------------|-------------------|------|
| JWT + HttpOnly Cookie | ✅ Section 1.5.1 | 一致 |
| Access Token 1 小时 | ✅ Max-Age=3600 | 一致 |
| Refresh Token 7 天 | ✅ Max-Age=604800 | 一致 |
| 单次使用（旋转） | ✅ 待 R1-21 实现 | 待完善 |
| CSRF Token | ✅ 待 R1-19 实现 | 待完善 |

#### 3.3 前端存储检查

**禁止的存储方式**：
- ❌ `localStorage.setItem('access_token', ...)`
- ❌ `sessionStorage.setItem('access_token', ...)`
- ❌ 响应体返回 `access_token`/`refresh_token`

**允许的存储方式**：
- ✅ HttpOnly Secure SameSite Cookie（浏览器自动管理）
- ✅ 前端通过 `/api/v1/auth/me` 验证登录状态

## 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/API_CONTRACT.md | Section 1.5 重写 | 新增 1.5.1～1.5.5（浏览器端 Cookie 认证、内部 Bearer 认证、认证流程、参考、Cookie 属性详细定义） |
| docs/api/API_CONTRACT.md | 端点定义更新 | login: 响应体不再返回 Token，改为 Set-Cookie |
| docs/api/API_CONTRACT.md | 端点定义更新 | refresh: 请求体不再传递 refresh_token，改为 Cookie 读取 |
| docs/api/API_CONTRACT.md | 端点定义更新 | logout: 新增 Set-Cookie 清除 Cookie |
| docs/api/API_CONTRACT.md | 端点定义更新 | register: 新增 Set-Cookie 设置 Token |
| docs/api/API_CONTRACT.md | 端点定义更新 | /me: 认证方式改为 Cookie |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-18：`[ ]` → `[x]` |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明 | 添加 R1-18 完成说明 |

## 验收结果

### 4.1 验收检查清单

- [x] Web 浏览器端主认证方式明确为 HttpOnly Secure SameSite Cookie + JWT
- [x] API_CONTRACT 不要求前端将 access_token 存入 localStorage/sessionStorage
- [x] 登录/注册响应体不再返回 access_token/refresh_token
- [x] 内部服务 Bearer Token 明确范围（Model Gateway、Admin）
- [x] login/refresh/logout/me 端点 Cookie 行为一致
- [x] Cookie 属性详细定义（HttpOnly、Secure、SameSite、Path、Max-Age）
- [x] SameSite=Lax 选择理由明确
- [x] 开发环境例外说明（Secure=false）
- [x] HTTP 契约与 ADR-003 一致
- [x] P0_P1_REMEDIATION_PLAN.md 已更新

### 4.2 Cookie 属性总结

| Cookie | HttpOnly | Secure | SameSite | Path | Max-Age |
|--------|:--------:|:------:|:--------:|------|:-------:|
| access_token | ✅ | ✅ | Lax | `/api/v1` | 3600s |
| refresh_token | ✅ | ✅ | Lax | `/api/v1/auth` | 604800s |

### 4.3 待后续任务完善

- R1-19：CSRF 防护方案（Cookie 写请求需 CSRF Token）
- R1-20：修正登录响应（确认响应格式）
- R1-21：Refresh Token 轮换（单次使用、撤销旧 Token）
- R1-22：WebSocket 鉴权（URL Token → Cookie）

## 下一步

R1-18 已完成，R1 批次剩余任务：
- R1-19：定义 CSRF 方案
- R1-20：修正登录响应
- R1-21：修正 Refresh 流程
- R1-22：修正 WebSocket 鉴权
- R1-23：定义 WebSocket Token 过期
- R1-24：冻结事件 Schema
- R1-25：修正威胁编号
- R1-26：修正威胁数量

可继续执行 R1-19 或进入 R4 验收（前提：R1-19～R1-26 全部完成）

## 备注

**R1-18 与 R1-19/R1-20/R1-21 的关系**：
- R1-18 冻结浏览器认证方式（Cookie + JWT 主方案）
- R1-19 定义 CSRF 防护方案（Cookie 写请求）
- R1-20 修正登录响应格式（确认响应体结构）
- R1-21 修正 Refresh 流程（Token 旋转、撤销）
- R1-18 为 R1-19～R1-21 提供基础（认证方式已统一）

## R1-C 认证/CSRF 契约复审整改（2026-07-15）

### 整改内容

1. **Admin API Bearer 认证豁免 CSRF**：Section 1.5.2 已将管理后台认证方式定义为 `Authorization: Bearer <admin_token>`，Section 1.5.6.3 豁免规则已包含 "Bearer Token 认证的请求"，但 Section 1.6.6 Admin 端点错误码清单仍错误包含 `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH`，与 Bearer 豁免规则冲突。
2. **统一 Bearer 豁免表述**：Section 1.5.6.3 豁免规则从 "内部服务间调用，不通过 Cookie 认证" 更新为 "内部服务间调用（`internal_service_token`）及管理后台（`admin_token`），不通过 Cookie 认证"，明确包含所有 Bearer 认证类型。

### 变更内容

- Section 1.6.6 Admin 端点错误码清单：移除所有 6 个写端点的 `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` 错误码
- Section 1.5.6.3 CSRF 豁免请求：Bearer Token 豁免规则明确包含 `internal_service_token` 和 `admin_token`
- API_CONTRACT.md 变更记录：R1-C 条目新增 "移除 Bearer Admin API 的 CSRF 错误码，统一 Bearer 请求豁免规则"

### 关联任务

- R1-19：CSRF 豁免规则已包含 Bearer Token（含 admin_token）
- R1-21：Refresh/Logout 端点已包含 CSRF 错误码（Cookie 认证端点，正确）

## R1-D 认证/CSRF 契约复审最终整改（2026-07-15）

### 整改内容

1. **Admin API 端点请求头完整性**：Section 2.10 共 11 个 Admin API 端点，其中 `GET /api/v1/admin/nodes/{node_id}`（EP-ADMIN-063）遗漏了 `Authorization: Bearer <admin_token>` 请求头声明，已补充。全部 11 个 Admin 端点现在均显式声明 Bearer admin_token。
2. **端点追踪文档统计清理**：`MVP_ENDPOINT_TRACEABILITY.md` 顶部已声明 68 个 MVP HTTP 端点、3 个内部端点、71 个总文档化端点、100% 覆盖率，但正文仍保留旧数据（41 个已文档化、27 个缺失、60.3% 覆盖率）。已将旧数据移至"整改前历史状态"章节并明确标注为历史记录，结论更新为当前权威统计。
3. **P0_P1_REMEDIATION_PLAN.md 口径统一**：将 R1-06 任务名称、R1 退出条件、R4-03 验收项中的"62 个端点"统一修正为"68 个端点"。

### 变更内容

- API_CONTRACT.md：`GET /api/v1/admin/nodes/{node_id}` 补充 `Authorization: Bearer <admin_token>` 请求头
- API_CONTRACT.md：Section 1.6.6 Admin 端点错误码清单继续不含 CSRF 错误码（R1-C 已清理）
- MVP_ENDPOINT_TRACEABILITY.md：旧统计（41/68、60.3%、27 个缺失）移至历史章节，结论更新为 68/71/100%
- P0_P1_REMEDIATION_PLAN.md：R1-06 任务名称、R1 退出条件、R4-03 验收项中的"62"→"68"

### 关联任务

- R1-17：端点追踪文档统计清理（MVP_ENDPOINT_TRACEABILITY.md）
- R1-C：Admin API Bearer CSRF 豁免规则确认

## R1-22 WebSocket 鉴权说明（历史状态标注）

本日志中提到的 `ws://localhost:8000/ws/v1?token=<access_token>` 为 R1-18 完成时的历史状态。

R1-22 已修正 WebSocket 鉴权：
- 路径改为 `/api/v1/ws`
- 认证方式改为 `access_token` HttpOnly Cookie
- 禁止 URL Token
- 强制 Origin 白名单校验

当前有效契约以 `WEBSOCKET_CONTRACT.md` 和 `API_CONTRACT.md` 为准。
