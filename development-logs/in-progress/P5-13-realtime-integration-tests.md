# P5-13: 实时集成测试

> 任务 ID: P5-13
> 开始时间: 2026-07-17
> 状态: 已完成

## 目标

覆盖 P5 端到端集成测试：
- 私聊端到端流程
- 群聊端到端流程
- WebSocket message.created 事件信封验证
- 非成员订阅失败
- 断线后 HTTP 回补
- duplicate event 去重

## 实现文件

### 新增文件

1. **`apps/api/tests/integration/test_conversation_flow.py`** — 会话端到端流程
   - `TestPrivateChatFlow`（3 个测试）：
     - `test_full_private_chat_flow`: 创建私聊 → 发消息 → 列表 → 删除 → 验证隐藏
     - `test_private_chat_idempotent_reuse`: 双向创建返回同一会话
     - `test_non_member_cannot_read_private_chat`: 非成员 403
   - `TestGroupChatFlow`（2 个测试）：
     - `test_full_group_chat_flow`: 创建群 → 添加/移除成员 → 权限验证
     - `test_non_owner_cannot_add_participant`: 非 OWNER 403
   - `TestMessagePaginationFlow`（2 个测试）：
     - `test_message_pagination_multi_page`: 55 条消息分两页
     - `test_conversation_list_pagination`: 5 个会话分页

2. **`apps/api/tests/integration/test_realtime_flow.py`** — 实时 WebSocket 集成测试
   - `TestRealtimeConnectionFlow`（3 个测试）：
     - `test_connection_established_sequence`: 首个事件验证
     - `test_ping_pong_flow`: ping/pong + request_id 回显
     - `test_subscribe_unsubscribe_flow`: 订阅 → 取消订阅完整流程
   - `TestRealtimePermissionFlow`（5 个测试）：
     - `test_non_member_subscribe_denied`: 非成员订阅 → error
     - `test_subscribe_to_nonexistent_conversation`: 不存在 → error
     - `test_invalid_json_returns_error`: 非法 JSON → WS_INVALID_MESSAGE
     - `test_missing_event_returns_error`: 缺少 event → WS_MISSING_EVENT
     - `test_unknown_event_returns_error`: 未知事件 → WS_UNKNOWN_EVENT
   - `TestRealtimeBackfillFlow`（2 个测试）：
     - `test_http_backfill_after_disconnect`: 模拟断线后 HTTP 回补
     - `test_event_dedup_in_backfill_scenario`: event_id 去重 + message_id 去重
   - `TestRealtimeEnvelopeFlow`（3 个测试）：
     - `test_message_created_envelope_shape`: 验证 §4.3.1 信封结构
     - `test_error_envelope_shape`: 验证 §4.7.1 error 信封
     - `test_connection_established_envelope`: 验证 §4.1.1 信封

## 覆盖矩阵

| P5-13 要求 | 测试文件 | 测试方法 |
|-----------|---------|---------|
| 私聊端到端 | test_conversation_flow.py | TestPrivateChatFlow.test_full_private_chat_flow |
| 群聊端到端 | test_conversation_flow.py | TestGroupChatFlow.test_full_group_chat_flow |
| WebSocket message.created | test_realtime_flow.py | TestRealtimeEnvelopeFlow.test_message_created_envelope_shape |
| 非成员订阅失败 | test_realtime_flow.py | TestRealtimePermissionFlow.test_non_member_subscribe_denied |
| 断线后回补 | test_realtime_flow.py | TestRealtimeBackfillFlow.test_http_backfill_after_disconnect |
| duplicate event 去重 | test_realtime_flow.py | TestRealtimeBackfillFlow.test_event_dedup_in_backfill_scenario |

## 验证结果

```
20 passed, 1 warning in 10.89s
```

所有测试均通过。覆盖了私聊、群聊、权限、WebSocket 鉴权、事件信封、回补、去重全部场景。
