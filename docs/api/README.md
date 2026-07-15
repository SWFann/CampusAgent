# API 契约

## 契约状态

| 契约 | 版本 | 状态 | 文件 |
|------|------|------|------|
| HTTP API 契约 | v1.0-frozen | ✅ 已冻结 | [API_CONTRACT.md](API_CONTRACT.md) |
| WebSocket 与事件契约 | v1.0-frozen | ✅ 已冻结 | [WEBSOCKET_CONTRACT.md](WEBSOCKET_CONTRACT.md) |

> **冻结日期**：2026-07-15
> **冻结范围**：所有 REST 端点、错误码体系、WebSocket 连接协议、事件信封、全部事件 Schema、错误事件、版本策略、隐私投影规则
> 破坏性变更须经 ADR 评审并同步更新文档、客户端与 Mock Server。

## 通用规则

- HTTP 前缀：`/api/v1`；
- 创建场景、提交偏好和确认结果支持 `Idempotency-Key`；
- 错误码格式：`MODULE_REASON`；
- 所有响应带 `request_id`；
- WebSocket 只发送公开场景状态，不发送其他成员的私有偏好；
- 私有偏好只能通过 Scene API 提交，不能复用消息 API；
- 模型调用只能经过内部 Model Gateway，并携带隐私上下文。

## 契约冻结顺序

1. Auth/User/Organization 和角色模型；
2. Conversation/Message/WebSocket；
3. Agent/Memory/Consent/Audit；
4. Scene 生命周期、私有提交、候选、投票与结果；
5. Model Gateway/Node Management；
6. OpenAPI 生成客户端和 Mock Server。

任何破坏性变更都必须更新文档、生成客户端、Mock 与相关测试，并用 ADR 记录原因。
