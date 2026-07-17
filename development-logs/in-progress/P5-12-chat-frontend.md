# P5-12: 聊天页面（列表 + 消息 + 输入 + 成员栏 + WS 状态）

> 任务 ID: P5-12
> 开始时间: 2026-07-17
> 状态: 已完成

## 目标

实现聊天前端页面，包含：
- 会话列表页 `/conversations`
- 聊天详情页 `/conversations/[conversationId]`
- 消息区（分页加载、实时追加）
- 输入框（幂等发送）
- 成员栏（在线状态）
- WebSocket 状态指示器
- 场景卡占位
- 不保存 token

## 实现文件

### 新增文件

1. **`apps/web/src/lib/conversations.ts`** — 会话 API 客户端
   - 类型定义与后端 schema 对齐（Conversation, Message, Participant 等）
   - API 函数：createPrivateConversation, createGroupConversation, listConversations, getConversation, listParticipants, addParticipant, removeParticipant, sendMessage, listMessages, deleteMessage
   - 所有写请求自动携带 X-CSRF-Token
   - 所有请求使用 `credentials: 'include'` 发送 HttpOnly Cookie

2. **`apps/web/src/lib/realtime.ts`** — WebSocket 实时客户端
   - `RealtimeClient` 类，实现 WEBSOCKET_CONTRACT.md v1.0 客户端状态机
   - 状态：IDLE → CONNECTING → OPEN → RECONNECTING → PAUSED/CLOSED/AUTH_FAILED/FORBIDDEN
   - 指数退避重连（§6.1）：0s, 1s, 2s, 4s, 8s, 16s, 30s max，±20% jitter
   - 自动重连白名单（§6.2）：1001, 1011, 1012, 4408, 4429 可重连；1000, 1008, 4403, 4406 禁止
   - 事件去重（§6.4）：`EventDedupCache` 有界缓存，最多 1000 个 event_id，FIFO 淘汰
   - HTTP 回补（§6.3）：重连后恢复订阅，触发分页回补 + message_id 去重
   - sequence 跳号检测（§6.3.8）：检测到 gap 时自动触发 HTTP 回补
   - 心跳：每 30 秒发送 ping，连续 2 次未收到 pong 主动关闭重连
   - 浏览器 online 事件监听：网络恢复时重置失败计数器并立即重连
   - 隐私：不存储 token、不读取 localStorage/sessionStorage
   - React Hook：`useRealtimeState()` 返回状态和重试函数

3. **`apps/web/src/app/conversations/page.tsx`** — 会话列表页
   - 会话列表展示（类型标签、标题、最后消息时间、参与者数量）
   - 新建私聊/群聊表单（类型切换）
   - 私聊创建（输入目标用户 ID）
   - 群聊创建（标题 + 参与者 ID 列表）
   - 空状态提示
   - 导航链接到目录和聊天详情

4. **`apps/web/src/app/conversations/[conversationId]/page.tsx`** — 聊天详情页
   - 消息区：分页加载、自动滚动、消息气泡（区分自己/他人/系统/场景卡）
   - 消息输入框：幂等发送（idempotency_key）、5000 字符限制
   - 成员栏：可折叠，显示在线状态和角色
   - WebSocket 状态指示器：9 种状态显示（颜色 + 标签 + 重试按钮）
   - 场景卡占位：SCENE_CARD 类型消息显示紫色虚线占位框
   - 实时消息追加：WebSocket `message.created` 事件即时追加
   - 消息删除：软删除，点击自己的消息可删除
   - 加载更多：分页加载历史消息
   - HTTP 回补：断线重连后自动分页拉取遗漏消息，message_id 去重
   - 自动滚动：新消息到达时平滑滚动到底部
   - 浏览器 online 事件：网络恢复时重置重连计数

## 设计决策

### 隐私保护
- 所有 API 调用使用 `credentials: 'include'`，不读取或存储 token
- WebSocket 认证完全依赖 HttpOnly Cookie，不使用 URL 参数
- 前端不保存任何 token、session 或私有偏好数据
- 删除的消息不显示正文内容

### WebSocket 客户端状态机
严格遵循 WEBSOCKET_CONTRACT.md §7 的状态机：
- `IDLE` → `CONNECTING` → `OPEN`（正常流程）
- `OPEN` → `RECONNECTING`（可重连关闭码）
- `RECONNECTING` → `PAUSED`（连续 10 次失败）
- `OPEN` → `CLOSED`（用户主动关闭）
- `OPEN` → `FORBIDDEN`（1008/4403 关闭码）

### 事件去重
- 传输层去重：`event_id`（EventDedupCache，最多 1000 条）
- 业务层去重：`message_id`（processedMessageIds Set）

### HTTP 回补
- 重连后恢复所有订阅
- 对当前会话执行分页回补
- 使用 message_id 去重，遇到已处理消息停止翻页
- 最多回补 20 页（1000 条）

## 验证结果

### TypeScript 类型检查
```
npx tsc --noEmit --project apps/web/tsconfig.json
→ 无错误
```

### ESLint
```
npx eslint src/lib/conversations.ts src/lib/realtime.ts src/app/conversations/page.tsx "src/app/conversations/[conversationId]/page.tsx"
→ 无错误
```

### 生产构建
```
corepack pnpm --filter @campus-agent/web build
→ ✓ Compiled successfully
→ ✓ Generating static pages (10/10)
→ /conversations (2.83 kB, 99.6 kB First Load JS)
→ /conversations/[conversationId] (6.25 kB, 103 kB First Load JS)
```

## 与契约对齐

| 契约要求 | 实现状态 |
|---------|---------|
| 指数退避重连（§6.1） | ✅ 0/1/2/4/8/16/30s + ±20% jitter |
| 自动重连白名单（§6.2） | ✅ 1001/1011/1012/4408/4429 可重连 |
| 禁止重连清单（§6.2） | ✅ 1000/1008/4403/4406 不重连 |
| HTTP 回补（§6.3） | ✅ 分页 + message_id 去重 + 20 页上限 |
| 事件去重（§6.4） | ✅ event_id 有界缓存 1000 条 FIFO |
| sequence 跳号检测（§6.3.8） | ✅ gap 检测触发 HTTP 回补 |
| 心跳（§7.2） | ✅ 30s ping + 2 次未响应关闭 |
| 不保存 token | ✅ 仅使用 HttpOnly Cookie |
| 场景卡占位 | ✅ SCENE_CARD 类型显示占位框 |
| WebSocket 状态显示 | ✅ 9 种状态 + 重试按钮 |
