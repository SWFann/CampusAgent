---
task_id: R1-22
status: completed
stage: R1
title: 修正 WebSocket 鉴权
completed_at: 2026-07-14T13:10:00+09:00
estimated_hours: 0.5
actual_hours: 0.1
---

# R1-22：修正 WebSocket 鉴权

## 完成状态

✅ **WebSocket 鉴权已修正**

**完成时间**：2026-07-14T13:10:00+09:00

## 目标

禁止长期 Token 出现在 URL 查询参数，采用安全的 WebSocket 认证方式。

**来自整改计划**：R1-22 - 修正 WebSocket 鉴权

## 问题

**原方案（不安全）**：
```
ws://localhost:8000/ws/v1?token=<access_token>
```

**风险**：
- Token 出现在 URL 中 → 服务器日志、浏览器历史、Referer 泄露
- Access Token 长期有效（1小时）→ 一旦泄露后果严重

## 修正方案

### 方案 A：Cookie 认证（推荐）

```javascript
// 连接时自动携带 Cookie
const ws = new WebSocket('wss://api.example.com/ws/v1');
// Cookie 自动发送，后端从 Cookie 读取 refresh_token
// WebSocket 连接建立后，前端发送 access_token 进行认证
```

**流程**：
1. 建立 WebSocket 连接
2. 发送第一条消息：`{"type": "auth", "access_token": "..."}`
3. 服务器验证 access_token
4. 验证通过 → 连接激活

### 方案 B：一次性 Ticket（备选）

```javascript
// 1. 前端请求 ticket
POST /api/v1/ws/ticket
→ { "ticket": "uuid-v4", "expires_in": 300 }

// 2. 使用 ticket 连接
wss://api.example.com/ws/v1?ticket=<ticket>

// 3. 服务器验证 ticket 并建立连接
```

**优势**：
- Ticket 有效期短（5分钟）
- 一次性使用
- 不暴露长期 Token

## 决策

**采用方案 A（Cookie 认证）**

理由：
- Refresh Token 已在 HttpOnly Cookie 中
- WebSocket 连接复用现有认证机制
- Ticket 方案增加复杂度，收益有限

## WebSocket 连接流程

1. **建立连接**：`new WebSocket('wss://api.example.com/ws/v1')`
2. **发送认证**：`{"type": "auth", "access_token": "..."}`
3. **验证通过**：服务器发送 `{"type": "auth_success"}`
4. **失败处理**：服务器关闭连接，错误码 4001

## 验证结果

- [x] 禁止长期 Token 出现在 URL
- [x] 采用安全 Cookie + 连接后认证

## 下一步

- **R1-23**：定义 WebSocket Token 过期

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
