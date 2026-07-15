# ADR-003：认证方式

**状态**：Accepted  
**日期**：2026-07-14  
**决策者**：开发团队

## 背景

需要选择用户认证方案。

## 考虑选项

### 选项A：Session + Cookie

**优点**：
- 传统稳定
- 服务器控制

**缺点**：
- 分布式会话管理复杂
- CSRF 风险

---

### 选项B：JWT + Cookie

**优点**：
- 无状态
- 易于水平扩展
- 适合 API + Web 应用

**缺点**：
- Token  revocation 复杂
- Token 较大

---

### 选项C：OAuth 2.0

**优点**：
- 行业标准
- 支持第三方登录

**缺点**：
- 复杂度高
- MVP 不需要

---

## 决策

**采用 JWT + HttpOnly Cookie**。

## 实现细节

### Access Token

- 有效期：1 小时
- 存储：HttpOnly Cookie
- 内容：用户ID、角色、过期时间

### Refresh Token

- 有效期：7 天
- 存储：HttpOnly Cookie
- 单次使用（旋转）

### 认证流程

```
登录 → 颁发 Access + Refresh Token
→ 存储 HttpOnly Cookie
→ 后续请求自动携带
→ Refresh Token 轮换
→ 过期后跳转登录
```

---

## 安全措施

1. **密码**：bcrypt/argon2 强哈希
2. **HTTPS**：强制 HTTPS
3. **CSRF**：使用 CSRF Token
4. **限流**：登录/注册接口限流
5. **不泄露账号存在性**：统一响应

---

## 后果

- 简单可靠的认证方案
- 适合前后端分离架构
- 便于移动端扩展

## 相关文档

- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [API 契约](../api/API_CONTRACT.md)
