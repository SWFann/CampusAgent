# WebSocket 与事件契约

> **版本**：v1.0-DRAFT  
> **基线日期**：2026-07-14  
> **状态**：草稿  
> **维护者**：开发团队

## 1. WebSocket 连接

### 1.1 连接地址

```
ws://localhost:8000/ws/v1?token=<access_token>
```

或通过负载均衡器的 WSS。

### 1.2 认证

Token 通过 URL 查询参数传递：

```
ws://localhost:8000/ws/v1?token=eyJhbGciOiJIUzI1NiIs...
```

**替代方案**：连接后发送认证消息。

---

## 2. 事件格式

### 2.1 事件信封（Envelope）

所有事件使用统一格式：

```json
{
  "event": "message.created",
  "data": {
    // 事件特定数据
  },
  "version": "v1",
  "event_id": "evt_xxx",
  "timestamp": "2026-07-14T12:00:00+09:00"
}
```

**字段说明**：
- `event`：事件名称
- `data`：事件数据
- `version`：协议版本
- `event_id`：唯一事件ID（用于去重）
- `timestamp`：事件时间戳

---

## 3. 客户端事件

客户端可以发送的事件：

### 3.1 订阅会话

```json
{
  "event": "conversation.subscribe",
  "data": {
    "conversation_id": "uuid"
  },
  "id": "msg_xxx"
}
```

**响应**：
```json
{
  "event": "conversation.subscribed",
  "data": {
    "conversation_id": "uuid",
    "success": true
  }
}
```

---

### 3.2 取消订阅

```json
{
  "event": "conversation.unsubscribe",
  "data": {
    "conversation_id": "uuid"
  }
}
```

---

### 3.3 心跳

```json
{
  "event": "ping",
  "data": {},
  "id": "ping_xxx"
}
```

**响应**：
```json
{
  "event": "pong",
  "data": {},
  "id": "ping_xxx"
}
```

---

## 4. 服务端事件

### 4.1 消息事件

#### message.created

```json
{
  "event": "message.created",
  "data": {
    "message_id": "uuid",
    "conversation_id": "uuid",
    "sender": {
      "type": "USER",
      "user_id": "uuid",
      "display_name": "..."
    },
    "message_type": "TEXT",
    "content": "...",
    "created_at": "2026-07-14T12:00:00+09:00"
  },
  "event_id": "evt_xxx",
  "timestamp": "2026-07-14T12:00:00+09:00"
}
```

**隐私**：只发送公开消息，不含私有内容。

---

#### message.deleted

```json
{
  "event": "message.deleted",
  "data": {
    "message_id": "uuid",
    "conversation_id": "uuid",
    "deleted_at": "2026-07-14T12:00:00+09:00"
  }
}
```

---

### 4.2 会话事件

#### conversation.updated

```json
{
  "event": "conversation.updated",
  "data": {
    "conversation_id": "uuid",
    "title": "...",
    "updated_at": "2026-07-14T12:00:00+09:00"
  }
}
```

---

#### participant.joined

```json
{
  "event": "participant.joined",
  "data": {
    "conversation_id": "uuid",
    "participant": {
      "type": "USER",
      "user_id": "uuid",
      "display_name": "..."
    },
    "joined_at": "2026-07-14T12:00:00+09:00"
  }
}
```

---

#### participant.left

```json
{
  "event": "participant.left",
  "data": {
    "conversation_id": "uuid",
    "participant": {
      "type": "USER",
      "user_id": "uuid"
    },
    "left_at": "2026-07-14T12:00:00+09:00"
  }
}
```

---

### 4.3 场景事件 ⭐ 关键

#### scene.updated

**重要**：只发送公开信息，不含私有内容。

```json
{
  "event": "scene.updated",
  "data": {
    "scene_instance_id": "uuid",
    "stage": "WAITING_FOR_PRIVATE_INPUT",
    "submitted_count": 3,
    "total_count": 4,
    "privacy": {
      "debate_visible": false,
      "raw_preferences_visible": false
    }
  },
  "event_id": "evt_xxx",
  "timestamp": "2026-07-14T12:00:00+09:00"
}
```

**隐私控制**：
- ✅ 只包含进度数字
- ❌ 不含任何个人偏好
- ❌ 不含智能体辩论
- ❌ 不含私有评价

---

#### scene.result.generated

```json
{
  "event": "scene.result.generated",
  "data": {
    "scene_instance_id": "uuid",
    "candidates": [
      {
        "title": "南门粤菜馆",
        "match_score": 88,
        "aggregate_reasons": [
          "满足全部成员的硬性限制",
          "整体预算匹配度较高"
        ]
      }
    ],
    "privacy_notice": "个人偏好和智能体协商过程未公开。"
  }
}
```

**隐私控制**：
- ✅ 只发送候选、匹配分、聚合理由
- ❌ 不含任何个人偏好
- ❌ 不含智能体推理过程

---

### 4.4 通知事件

#### notification.created

```json
{
  "event": "notification.created",
  "data": {
    "notification_id": "uuid",
    "type": "SCENE_INVITE",
    "title": "邀请您参与聚餐协商",
    "body": "...",
    "created_at": "2026-07-14T12:00:00+09:00"
  }
}
```

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

### 6.1 客户端退避

```
第1次重连：立即
第2次重连：1秒后
第3次重连：2秒后
第4次重连：4秒后
第n次重连：min(2^(n-1), 30)秒
```

### 6.2 漏消息回补

重连后，客户端应通过 HTTP 获取断开期间的消息：

```
GET /api/v1/conversations/{id}/messages?since=2026-07-14T12:00:00+09:00
```

---

### 6.3 事件去重

使用 `event_id` 去重：

```python
processed_events = set()

def handle_event(event):
    if event["event_id"] in processed_events:
        return  # 重复事件，忽略

    processed_events.add(event["event_id"])
    # 处理事件
```

---

## 7. 连接生命周期

### 7.1 连接建立

1. 客户端发起连接
2. 服务端验证 Token
3. 建立连接
4. 发送 `connection.established` 事件

### 7.2 连接保持

1. 客户端定期发送 `ping`
2. 服务端返回 `pong`
3. 心跳间隔：30秒

### 7.3 连接断开

1. 客户端主动断开
2. 服务端主动断开（Token过期）
3. 网络异常断开

**处理**：
- 客户端尝试重连
- 重连失败后提示用户

### 7.4 Token 过期

1. 服务端检测 Token 过期
2. 发送 `connection.expired` 事件
3. 客户端跳转到登录页

---

## 8. 版本策略

### 8.1 版本标识

每个事件包含 `version` 字段：

```json
{
  "version": "v1",
  "event": "...",
  "data": { ... }
}
```

### 8.2 版本变更

破坏性变更时：
1. 更新版本号（v1 → v2）
2. 同时支持旧版本（至少2周）
3. 通知前端团队
4. 更新文档

---

## 9. 事件清单

### 9.1 消息事件

| 事件名 | 描述 | 触发时机 |
|--------|------|---------|
| `message.created` | 消息创建 | 新消息发送时 |
| `message.updated` | 消息更新 | 消息编辑时 |
| `message.deleted` | 消息删除 | 消息删除时 |

---

### 9.2 会话事件

| 事件名 | 描述 | 触发时机 |
|--------|------|---------|
| `conversation.updated` | 会话更新 | 会话信息变更时 |
| `participant.joined` | 参与者加入 | 新成员加入时 |
| `participant.left` | 参与者离开 | 成员退出时 |
| `participant.updated` | 参与者更新 | 成员信息变更时 |

---

### 9.3 场景事件

| 事件名 | 描述 | 触发时机 | 隐私 |
|--------|------|---------|------|
| `scene.updated` | 场景更新 | 阶段变化时 | ✅ 不含私有内容 |
| `scene.result.generated` | 结果生成 | 候选生成后 | ✅ 不含私有内容 |
| `scene.completed` | 场景完成 | 状态变为 COMPLETED | ✅ 不含私有内容 |

---

### 9.4 通知事件

| 事件名 | 描述 | 触发时机 |
|--------|------|---------|
| `notification.created` | 通知创建 | 新通知产生时 |

---

## 10. 错误处理

### 10.1 错误事件

```json
{
  "event": "error",
  "data": {
    "code": "INVALID_MESSAGE",
    "message": "消息格式错误",
    "original_event": { ... }
  }
}
```

### 10.2 常见错误

| 错误码 | 说明 | 处理方式 |
|--------|------|---------|
| `INVALID_MESSAGE` | 消息格式错误 | 检查格式后重试 |
| `UNAUTHORIZED` | 未授权 | 重新登录 |
| `RATE_LIMITED` | 频率限制 | 退避后重试 |
| `CONNECTION_ERROR` | 连接错误 | 重连 |

---

## 11. 相关文档

- [HTTP API 契约](./API_CONTRACT.md)
- [领域词汇表](../domain/DOMAIN_VOCABULARY.md)

---

**下一步**：P0-11（建立隐私测试矩阵）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
