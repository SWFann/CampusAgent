# R1-20 任务日志：修正登录响应

> **任务编号**：R1-20
> **执行日期**：2026-07-15
> **执行人**：Claude
> **任务目标**：修正登录接口契约，避免同时声称"只用 HttpOnly Cookie"又在响应体返回可持久化 token

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：修正登录响应
- **具体操作**：不再同时声称只用 Cookie 又返回持久化 Token
- **完成标准**：前端无须把 Token 写入浏览器存储

### 前置条件验证

✅ R1-18 已完成：浏览器认证方式统一为 HttpOnly Secure SameSite Cookie + JWT
✅ R1-19 已完成：CSRF 防护方案定义（Double-Submit Cookie 模式）
✅ API_CONTRACT.md v1.0-frozen：71 个端点已文档化

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
4. ✅ development-logs/completed/remediation-r1/R1-18_UNIFY_BROWSER_AUTH.md - R1-18 完成记录
5. ✅ development-logs/completed/remediation-r1/R1-19_DEFINE_CSRF_SCHEME.md - R1-19 完成记录

## 执行过程

### 1. 现状分析

#### 1.1 登录端点现状

**当前状态**（API_CONTRACT.md 第 1434-1483 行）：
- 响应体：返回用户元数据（`id`、`email`、`display_name`、`global_role`）
- 响应头：`Set-Cookie: access_token`、`Set-Cookie: refresh_token`
- 错误码：`AUTH_INVALID_TOKEN` - 邮箱或密码错误

**问题**：
1. 缺少 `csrf_token` Cookie（R1-19 要求登录时生成 CSRF Token）
2. 错误码 `AUTH_INVALID_TOKEN` 不准确（登录失败不是"Token 无效"，而是"凭证无效"）
3. 缺少 CSRF 错误码（R1-19 要求）

#### 1.2 错误码现状

**AUTH_INVALID_TOKEN**（当前）：
- HTTP 401
- message：访问令牌无效或已过期
- 出现位置：Auth
- 用途：登录失败、Token 验证失败

**问题**：
- 登录失败使用 `AUTH_INVALID_TOKEN` 语义不准确（登录时还没有 Token）
- 无法区分"登录凭证错误"和"Token 过期/无效"
- 不利于前端统一处理

#### 1.3 文档检查

**README.md**：
- ✅ 无 token 存储相关说明（无 localStorage/sessionStorage 要求）

**docs/development/QUICK_START.md**：
- ✅ 无 token 存储相关说明

**docs/development/*.md**：
- ✅ 无 token 存储相关说明

### 2. 修正实施

#### 2.1 登录端点修正

**变更内容**：

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| 响应头 | `Set-Cookie: access_token`、`Set-Cookie: refresh_token` | 新增 `Set-Cookie: csrf_token` |
| 错误码 | `AUTH_INVALID_TOKEN` | `AUTH_INVALID_CREDENTIALS` |
| CSRF 校验 | 未定义 | 豁免（login/register 为未认证 bootstrap 端点） |

**新增 csrf_token Cookie**：
```
Set-Cookie: csrf_token=<random>; Secure; SameSite=Lax; Path=/; Max-Age=604800
```

**属性说明**：
- `Secure`：仅 HTTPS 传输（开发环境允许 `Secure=false`）
- `SameSite=Lax`：跨站请求不携带 Cookie（防 CSRF）
- `Path=/`：所有路径可访问（前端需要读取）
- `HttpOnly`：**false**（前端需要读取）
- `Max-Age=604800`：有效期 7 天（与 refresh_token 一致）

**错误码变更**：
- 旧：`AUTH_INVALID_TOKEN` - 邮箱或密码错误
- 新：`AUTH_INVALID_CREDENTIALS` - 邮箱或密码错误（统一响应，不区分具体原因，防止账号枚举）

#### 2.2 错误码总表更新

**Section 1.6.3 新增错误码**：

| 错误码 | HTTP | message | retryable | 出现位置 |
|--------|:----:|---------|:---------:|---------|
| `AUTH_INVALID_CREDENTIALS` | 401 | 邮箱或密码错误 | false | Auth |

**位置**：Auth 错误码分类中，`AUTH_WEAK_PASSWORD` 之后，`USER_ALREADY_EXISTS` 之前

#### 2.3 端点错误码清单更新

**Section 1.6.6 Auth 端点错误码**：

| 端点 | 错误码 |
|------|--------|
| POST /api/v1/auth/login | `AUTH_INVALID_CREDENTIALS` |

**变更**：
- `AUTH_INVALID_TOKEN` → `AUTH_INVALID_CREDENTIALS`（登录失败）
- **R1-C 复审修正**：login/register 为未认证 bootstrap 端点，豁免 CSRF 校验（R1-19 初版曾添加 CSRF 错误码，R1-C 已移除）

#### 2.4 登录端点说明更新

**新增说明**：
- `csrf_token` Cookie 用于 CSRF 防护（非 HttpOnly，前端可读取）
- 前端需读取 `csrf_token` Cookie 值，并在写请求中通过 `X-CSRF-Token` 请求头携带
- 登录失败统一返回 `AUTH_INVALID_CREDENTIALS`，不区分"用户不存在"和"密码错误"（防止账号枚举攻击）

### 3. 验证检查

#### 3.1 登录响应检查

| 检查项 | 状态 | 说明 |
|--------|:----:|------|
| 响应体不返回 access_token | ✅ | 仅返回用户元数据 |
| 响应体不返回 refresh_token | ✅ | 仅返回用户元数据 |
| Set-Cookie: access_token | ✅ | HttpOnly; Secure; SameSite=Lax; Path=/api/v1; Max-Age=3600 |
| Set-Cookie: refresh_token | ✅ | HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800 |
| Set-Cookie: csrf_token | ✅ | Secure; SameSite=Lax; Path=/; Max-Age=604800（非 HttpOnly） |
| 错误码统一 | ✅ | `AUTH_INVALID_CREDENTIALS`（防止账号枚举） |
| CSRF 校验 | ✅ | login/register 为未认证 bootstrap 端点，豁免 CSRF（R1-C 复审确认） |

#### 3.2 错误码一致性检查

| 错误码 | HTTP | 用途 | 出现位置 |
|--------|:----:|------|---------|
| `AUTH_INVALID_CREDENTIALS` | 401 | 登录失败（邮箱或密码错误） | Auth |
| `AUTH_INVALID_TOKEN` | 401 | Token 验证失败（过期/无效） | Auth（保留，用于 /me 等端点） |

**区分**：
- `AUTH_INVALID_CREDENTIALS`：登录时使用（没有 Token，凭证错误）
- `AUTH_INVALID_TOKEN`：已认证请求使用（Token 过期/无效）

#### 3.3 文档检查

| 文档 | 检查项 | 状态 |
|------|--------|:----:|
| README.md | localStorage/sessionStorage 要求 | ✅ 无 |
| docs/development/QUICK_START.md | token 存储说明 | ✅ 无 |
| docs/development/*.md | token 存储说明 | ✅ 无 |

## 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/API_CONTRACT.md | 登录端点更新 | 新增 `Set-Cookie: csrf_token`（R1-19 要求） |
| docs/api/API_CONTRACT.md | 登录端点更新 | 错误码 `AUTH_INVALID_TOKEN` → `AUTH_INVALID_CREDENTIALS` |
| docs/api/API_CONTRACT.md | 登录端点更新 | **R1-C 复审修正**：login/register 为未认证 bootstrap 端点，豁免 CSRF 校验（R1-19 初版曾添加 CSRF 错误码，R1-C 已移除） |
| docs/api/API_CONTRACT.md | 登录端点更新 | 说明中添加 csrf_token 读取要求和账号枚举防护说明 |
| docs/api/API_CONTRACT.md | Section 1.6.3 更新 | 新增 `AUTH_INVALID_CREDENTIALS` 错误码 |
| docs/api/API_CONTRACT.md | Section 1.6.6 更新 | 登录端点错误码更新（移除 CSRF 错误码） |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-20：`[ ]` → `[x]` |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明 | 添加 R1-20 完成说明 |

## 验收结果

### 4.1 验收检查清单

- [x] 登录响应体不返回 access_token/refresh_token
- [x] 登录响应通过 Set-Cookie 写入认证 Cookie（access_token + refresh_token）
- [x] 登录响应通过 Set-Cookie 写入 csrf_token Cookie（R1-19 要求）
- [x] 错误码统一为 AUTH_INVALID_CREDENTIALS（防止账号枚举）
- [x] AUTH_INVALID_CREDENTIALS 加入错误码总表（Section 1.6.3）
- [x] 登录端点错误码清单更新（Section 1.6.6）
- [x] README 和开发文档中无 localStorage/sessionStorage 要求
- [x] P0_P1_REMEDIATION_PLAN.md 已更新
- [x] 任务日志已归档

### 4.2 登录响应示例

**成功响应**：

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1; Max-Age=3600
Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth; Max-Age=604800
Set-Cookie: csrf_token=<random>; Secure; SameSite=Lax; Path=/; Max-Age=604800

{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "student@example.edu",
    "display_name": "张三",
    "global_role": "STUDENT"
  },
  "request_id": "req_xxx"
}
```

**失败响应**（邮箱或密码错误）：

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "success": false,
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "邮箱或密码错误",
    "details": {},
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

**失败响应**（refresh/logout 缺少 CSRF Token，login/register 豁免 CSRF）：

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "success": false,
  "error": {
    "code": "CSRF_TOKEN_MISSING",
    "message": "缺少 CSRF Token，请刷新页面后重试",
    "details": {},
    "request_id": "req_xxx",
    "retryable": false
  }
}
```

### 4.3 安全特性

1. **防止账号枚举**：登录失败统一返回 `AUTH_INVALID_CREDENTIALS`，不区分"用户不存在"和"密码错误"
2. **防止 XSS**：access_token/refresh_token 通过 HttpOnly Cookie 存储，JavaScript 无法读取
3. **防止 CSRF**：csrf_token Cookie + X-CSRF-Token 请求头双重校验（login/register 为 bootstrap 端点豁免，refresh/logout 和其他写请求强制）
4. **前端无 Token 存储**：响应体不返回 Token，前端无须 localStorage/sessionStorage

## 下一步

R1-20 已完成，R1 批次剩余任务：
- R1-21：修正 Refresh 流程（Cookie、轮换、重放检测、注销撤销）
- R1-22：修正 WebSocket 鉴权
- R1-23：定义 WebSocket Token 过期
- R1-24：冻结事件 Schema
- R1-25：修正威胁编号
- R1-26：修正威胁数量

可继续执行 R1-21 或进入 R4 验收（前提：R1-21～R1-26 全部完成）

## 备注

**R1-20 与 R1-18/R1-19 的关系**：
- R1-18 冻结浏览器认证方式（Cookie + JWT）
- R1-19 定义 CSRF 防护方案（csrf_token Cookie + X-CSRF-Token）
- R1-20 修正登录响应（整合 R1-18 + R1-19，确保登录时同时设置 access_token、refresh_token、csrf_token）

## R1-C 认证/CSRF 契约复审整改（2026-07-15）

### 整改内容

1. **register 端点增加 csrf_token Cookie**：注册成功后自动登录，应和 login 一样设置 Set-Cookie: csrf_token
2. **CSRF 豁免范围澄清**：login/register 为未认证端点，豁免 CSRF 校验（R1-19 已明确）

### register 端点变更

| 项目 | 变更前 | 变更后 |
|------|--------|--------|
| Set-Cookie | access_token + refresh_token | access_token + refresh_token + csrf_token |
| 说明 | 注册成功后自动登录 | 注册成功后自动登录，前端可读取 csrf_token 用于后续写请求 |

### 关联任务

- R1-19：CSRF 豁免范围已明确（login/register 豁免）
- R1-21：Refresh/Logout 端点 CSRF 错误码保持一致
