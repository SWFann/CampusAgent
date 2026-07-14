---
task_id: R1-23
status: completed
stage: R1
title: 定义 WebSocket Token 过期
completed_at: 2026-07-14T13:11:00+09:00
estimated_hours: 0.5
actual_hours: 0.1
---

# R1-23：定义 WebSocket Token 过期

## 完成状态

✅ **WebSocket Token 过期策略已定义**

**完成时间**：2026-07-14T13:11:00+09:00

## 目标

定义 WebSocket Token 的过期处理：关闭码、刷新、重连和重新订阅。

**来自整改计划**：R1-23 - 定义 WebSocket Token 过期

## Token 过期策略

### Access Token 过期（1 小时）

**检测时机**：
- 连接建立后首次消息认证时
- 每隔 15 分钟检查一次 Token 有效期

**处理流程**：
1. Token 即将过期（<5分钟）→ 发送 `{"type": "token_expiring"}` 通知前端
2. Token 已过期 → 发送 `{"type": "token_expired"}` 并关闭连接
3. 关闭码：4001（Token Expired）

### 前端重连流程

```javascript
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === 'token_expiring') {
    // 1. 刷新 Access Token
    await refreshAccessToken();

    // 2. 重新认证 WebSocket
    ws.send(JSON.stringify({
      type: 'auth',
      access_token: newAccessToken
    }));
  }

  if (msg.type === 'token_expired') {
    // 3. 关闭连接
    ws.close(4001, 'Token expired');

    // 4. 重新登录
    setTimeout(() => connectWebSocket(), 1000);
  }
};
```

### 重新订阅

- WebSocket 重连后，需要重新订阅之前的场景
- 前端维护订阅列表，重连后重新发送订阅请求

## WebSocket 关闭码

| 关闭码 | 说明 | 处理 |
|-------|------|------|
| 4000 | 正常关闭 | 不重连 |
| 4001 | Token 过期 | 刷新 Token 后重连 |
| 4002 | 认证失败 | 重新登录 |
| 4003 | 服务器错误 | 1秒后重连 |
| 4004 | 客户端主动断开 | 不重连 |

## 验证结果

- [x] Token 过期处理已定义
- [x] 客户端行为可确定实现

## 下一步

- **R1-24**：冻结事件 Schema

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
