# R1-21 任务日志：修正 Refresh 流程

> **任务编号**：R1-21
> **执行日期**：2026-07-15
> **执行人**：Claude
> **任务目标**：使 POST /api/v1/auth/refresh 的 Cookie、轮换、重放检测、登出撤销逻辑与认证方案完全一致

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：修正 Refresh 流程
- **具体操作**：Cookie、轮换、重放检测、注销撤销
- **完成标准**：ADR 与 API 契约完全一致

### 前置条件验证

✅ R1-18 已完成：浏览器认证方式统一为 HttpOnly Secure SameSite Cookie + JWT
✅ R1-19 已完成：CSRF 防护方案定义（Double-Submit Cookie 模式）
✅ R1-20 已完成：登录响应修正（Set-Cookie + csrf_token）
✅ API_CONTRACT.md v1.0-frozen：71 个端点已文档化
✅ ADR-003：Refresh Token 单次使用（旋转）

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
4. ✅ docs/security/THREAT_MODEL.md - 威胁模型（T-05 重放攻击）
5. ✅ docs/decisions/0003-authentication.md - ADR-003（认证方式决策）
6. ✅ development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md - R1-18 完成记录
7. ✅ development-logs/completed/remediation-r1/R1-19_DEFINE_CSRF_SCHEME.md - R1-19 完成记录
8. ✅ development-logs/completed/remediation-r1/R1-20_FIX_LOGIN_RESPONSE.md - R1-20 完成记录

## 执行过程

### 1. 现状分析

#### 1.1 Refresh 端点现状

**当前状态**（API_CONTRACT.md 第 1491-1524 行）：
- 请求：无请求体，从 Cookie 读取 refresh_token
- 响应：200 OK + 用户元数据 + Set-Cookie: access_token
- 说明：refresh_token 保持不变（旋转策略见 R1-21）
- 错误码：`AUTH_REFRESH_TOKEN_REVOKED` - Refresh Token 已被撤销或已使用

**问题**：
1. refresh_token 未轮换（与 ADR-003 "单次使用" 冲突）
2. 无重放检测机制定义
3. 无 token family 机制定义
4. 缺少 `AUTH_REFRESH_TOKEN_EXPIRED` 错误码
5. 缺少 `AUTH_INVALID_TOKEN`（Cookie 缺失）
6. 响应体缺少 session_version（无法检测会话状态变化）

#### 1.2 Logout 端点现状

**当前状态**（API_CONTRACT.md 第 1527-1552 行）：
- 响应：204 No Content
- 响应头：Set-Cookie: access_token=; Max-Age=0, Set-Cookie: refresh_token=; Max-Age=0
- 说明：服务端撤销 refresh_token（加入黑名单）
- 错误码：`AUTH_INVALID_TOKEN` - 未认证或令牌无效

**问题**：
1. 缺少 csrf_token Cookie 清除
2. 未明确撤销整个 token family
3. 缺少 CSRF 错误码

#### 1.3 ADR-003 要求

**Refresh Token 轮换**（ADR-003）：
- 单次使用（旋转）
- 每次刷新颁发新 refresh_token
- 旧 refresh_token 立即失效

**重放检测**（威胁模型 T-05）：
- 检测到重放攻击时撤销整个 token family
- 标记 session compromised

### 2. 修正实施

#### 2.1 Refresh 端点修正

**变更内容**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 响应体 | `{ "id", "email" }` | `{ "id", "email", "display_name", "global_role", "session_version" }` |
| 响应头 | `Set-Cookie: access_token` | `Set-Cookie: access_token` + `Set-Cookie: refresh_token`（轮换） |
| 错误码 | `AUTH_REFRESH_TOKEN_REVOKED` | `AUTH_REFRESH_TOKEN_REVOKED`、`AUTH_REFRESH_TOKEN_EXPIRED`、`AUTH_INVALID_TOKEN` |
| Token 轮换 | 未实现（见 R1-21） | ✅ 每次刷新颁发新 refresh_token，旧 token 失效 |
| 重放检测 | 未定义 | ✅ 检测到重放时撤销整个 token family |

**Token Family 机制**：
- 每次登录/刷新时生成新的 token family ID
- `refresh_token` 包含 family ID
- 重放检测：同一 family ID 的 refresh_token 只能使用一次
- 检测到重放时：撤销整个 family（所有关联的 refresh_token），标记 session compromised

**session_version**：
- 每次刷新递增
- 前端通过 `/api/v1/auth/me` 检测 session_version 变化
- 如果版本号突然变化，提示用户重新登录（安全警告）

#### 2.2 Logout 端点修正

**变更内容**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 响应头 | `Set-Cookie: access_token`、`Set-Cookie: refresh_token` | 新增 `Set-Cookie: csrf_token` |
| 服务端行为 | 撤销 refresh_token（加入黑名单） | 撤销整个 token family（所有关联的 refresh_token） |
| 错误码 | `AUTH_INVALID_TOKEN` | `AUTH_INVALID_TOKEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

#### 2.3 错误码总表更新

**Section 1.6.3 新增错误码**：

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `AUTH_REFRESH_TOKEN_EXPIRED` | 401 | Refresh Token 已过期 | false | Auth |

**位置**：Auth 错误码分类中，`AUTH_REFRESH_TOKEN_REVOKED` 之后

**更新现有错误码**：
- `AUTH_REFRESH_TOKEN_REVOKED` message：Refresh Token 已被撤销（包括重放检测触发撤销）

#### 2.4 端点错误码清单更新

**Section 1.6.6 Auth 端点错误码**：

| 端点 | 错误码 |
|------|--------|
| POST /api/v1/auth/refresh | `AUTH_REFRESH_TOKEN_REVOKED`、`AUTH_REFRESH_TOKEN_EXPIRED`、`AUTH_INVALID_TOKEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/auth/logout | `AUTH_INVALID_TOKEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

### 3. 验证检查

#### 3.1 Refresh 流程一致性检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| Refresh 使用 Cookie | ✅ | 从 Cookie 读取 refresh_token，不通过请求体 |
| Refresh 轮换 | ✅ | 每次刷新颁发新 refresh_token，旧 token 失效 |
| 响应体不暴露 Token | ✅ | 仅返回用户元数据 + session_version |
| 错误码完整 | ✅ | `AUTH_REFRESH_TOKEN_REVOKED`、`AUTH_REFRESH_TOKEN_EXPIRED`、`AUTH_INVALID_TOKEN` |
| 重放检测 | ✅ | 检测到重放时撤销整个 token family |
| Token family 机制 | ✅ | 定义 token family 机制和重放处理流程 |

#### 3.2 Logout 流程一致性检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| Logout 清除 Cookie | ✅ | access_token、refresh_token、csrf_token |
| Logout 撤销 Token | ✅ | 撤销整个 token family |
| 错误码 | ✅ | `AUTH_INVALID_TOKEN`、`CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

#### 3.3 认证流程一致性检查

| 端点 | 认证方式 | Cookie 设置 | Token 暴露 | 错误码 |
|------|---------|------------|-----------|--------|
| login | 无（公开） | access_token + refresh_token + csrf_token | ❌ | AUTH_INVALID_CREDENTIALS |
| refresh | refresh_token Cookie | access_token + refresh_token（轮换） | ❌ | AUTH_REFRESH_TOKEN_REVOKED/EXPIRED |
| logout | access_token Cookie | 清除所有 Cookie | ❌ | AUTH_INVALID_TOKEN |
| me | access_token Cookie | 无 | ❌ | AUTH_INVALID_TOKEN |

## 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/API_CONTRACT.md | Refresh 端点更新 | 新增 Token 轮换（每次刷新颁发新 refresh_token） |
| docs/api/API_CONTRACT.md | Refresh 端点更新 | 新增 Token Family 机制和重放检测 |
| docs/api/API_CONTRACT.md | Refresh 端点更新 | 新增 session_version 字段 |
| docs/api/API_CONTRACT.md | Refresh 端点更新 | 新增错误码：AUTH_REFRESH_TOKEN_EXPIRED、AUTH_INVALID_TOKEN |
| docs/api/API_CONTRACT.md | Logout 端点更新 | 新增 csrf_token Cookie 清除 |
| docs/api/API_CONTRACT.md | Logout 端点更新 | 新增撤销整个 token family |
| docs/api/API_CONTRACT.md | Logout 端点更新 | 新增 CSRF 错误码 |
| docs/api/API_CONTRACT.md | Section 1.6.3 更新 | 新增 AUTH_REFRESH_TOKEN_EXPIRED 错误码 |
| docs/api/API_CONTRACT.md | Section 1.6.3 更新 | 更新 AUTH_REFRESH_TOKEN_REVOKED message |
| docs/api/API_CONTRACT.md | Section 1.6.6 更新 | 更新 refresh 和 logout 端点错误码 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-21：[ ] → [x] |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明 | 添加 R1-21 完成说明 |

## 验收结果

### 4.1 验收检查清单

- [x] Refresh 使用 HttpOnly refresh Cookie，不通过请求体传递
- [x] Refresh 成功时轮换 refresh cookie（颁发新 token，旧 token 失效）
- [x] Refresh 成功时返回 user/session 元数据（不暴露 Token）
- [x] Refresh 失败时有稳定错误码（AUTH_REFRESH_TOKEN_REVOKED/EXPIRED、AUTH_INVALID_TOKEN）
- [x] 重放检测定义（撤销整个 token family，标记 session compromised）
- [x] Logout 撤销 refresh token/session（整个 token family）
- [x] Logout 清除所有 Cookie（access_token、refresh_token、csrf_token）
- [x] login/refresh/logout/me 认证语义一致
- [x] AUTH_REFRESH_TOKEN_EXPIRED 加入错误码总表
- [x] P0_P1_REMEDIATION_PLAN.md 已更新
- [x] 任务日志已归档

### 4.2 Refresh 流程总结

**成功流程**：
1. 前端发送 POST /api/v1/auth/refresh（携带 Cookie）
2. 服务端验证 refresh_token（检查 Cookie）
3. 验证通过：
   - 颁发新的 refresh_token（旧 token 加入黑名单）
   - 颁发新的 access_token
   - 递增 session_version
   - 返回用户元数据 + session_version
4. 前端更新 Cookie 和 session_version

**失败流程**：
- refresh_token 缺失：`AUTH_INVALID_TOKEN`（401）
- refresh_token 过期：`AUTH_REFRESH_TOKEN_EXPIRED`（401）
- refresh_token 已撤销：`AUTH_REFRESH_TOKEN_REVOKED`（401）
- 检测到重放：撤销整个 token family，返回 `AUTH_REFRESH_TOKEN_REVOKED`（401）

**重放检测**：
- 同一 token family 的 refresh_token 只能使用一次
- 检测到重放时：
  - 撤销整个 family（所有关联的 refresh_token）
  - 标记 session compromised
  - 返回 `AUTH_REFRESH_TOKEN_REVOKED`

### 4.3 Logout 流程总结

**成功流程**：
1. 前端发送 POST /api/v1/auth/logout（携带 Cookie）
2. 服务端验证 access_token
3. 验证通过：
   - 撤销当前 refresh_token（加入黑名单）
   - 撤销整个 token family
   - 清除 access_token、refresh_token、csrf_token Cookie
4. 前端清除客户端状态

### 4.4 安全特性

1. **Refresh Token 轮换**：每次刷新颁发新 token，旧 token 立即失效
2. **重放检测**：同一 token family 只能使用一次，检测到重放时撤销整个 family
3. **Session 版本追踪**：session_version 递增，前端可检测会话状态变化
4. **全面 Cookie 清除**：Logout 时清除所有认证相关 Cookie

## 下一步

R1-21 已完成，R1 批次剩余任务：
- R1-22：修正 WebSocket 鉴权
- R1-23：定义 WebSocket Token 过期
- R1-24：冻结事件 Schema
- R1-25：修正威胁编号
- R1-26：修正威胁数量

可继续执行 R1-22 或进入 R4 验收（前提：R1-22～R1-26 全部完成）

## 备注

**R1-21 与 R1-18/R1-19/R1-20 的关系**：
- R1-18 冻结浏览器认证方式（Cookie + JWT）
- R1-19 定义 CSRF 防护方案
- R1-20 修正登录响应（Set-Cookie + csrf_token）
- R1-21 修正 Refresh 流程（轮换、重放检测、撤销）
- R1-18～R1-21 共同构成完整的认证生命周期管理

## R1-C 认证/CSRF 契约复审整改（2026-07-15）

### 整改内容

1. **CSRF 豁免范围澄清**：refresh/logout 为 Cookie 已认证端点，必须 CSRF 校验（R1-19 已明确）
2. **CSRF_TOKEN_EXPIRED 降级**：refresh/logout 端点错误码清单中不包含 CSRF_TOKEN_EXPIRED（MVP 仅用 MISSING/MISMATCH）

### 认证端点 CSRF 规则总结

| 端点 | 认证状态 | CSRF 校验 | 错误码 |
|------|---------|:---------:|--------|
| POST /api/v1/auth/register | 未认证 | ❌ 豁免 | 无 |
| POST /api/v1/auth/login | 未认证 | ❌ 豁免 | 无 |
| POST /api/v1/auth/refresh | Cookie 已认证 | ✅ 必须 | `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |
| POST /api/v1/auth/logout | Cookie 已认证 | ✅ 必须 | `CSRF_TOKEN_MISSING`、`CSRF_TOKEN_MISMATCH` |

### 关联任务

- R1-19：CSRF 豁免范围已明确
- R1-20：login/register 已包含 csrf_token Cookie
