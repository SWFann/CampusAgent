# R1-23 任务日志：定义 WebSocket Token 过期、刷新、重连和重新订阅

> **任务编号**：R1-23
> **执行日期**：2026-07-15
> **执行人**：开发团队
> **状态**：等待 Codex 审计

## 核心成果

- Token临期提前60秒通知（`connection.expiring`）
- Token过期关闭码4401
- HTTP Refresh流程（携带CSRF）
- Single-flight Refresh机制
- 完整关闭码总表
- 心跳机制（30秒ping，10秒响应，4408关闭）
- 浏览器握手失败限制说明
- 重新订阅流程（权限重新验证）

## 修改文件

- `docs/api/WEBSOCKET_CONTRACT.md`：完整重写，补全所有审计遗漏
- `docs/project/P0_P1_REMEDIATION_PLAN.md`：R1-23完成摘要移至R1-C区域，R1-24保持`[ ]`
- 删除 `docs/api/WEBSOCKET_CONTRACT.md.backup`

## 逐项章节位置与自检结果

### 一、删除编辑器备份文件

- **操作**：删除 `docs/api/WEBSOCKET_CONTRACT.md.backup`
- **自检**：`git status --short` 不再出现 `.backup`/`.bak`/`.tmp` 文件
- **结果**：✅ 通过

### 二、浏览器握手失败恢复流程

- **章节位置**：WEBSOCKET_CONTRACT.md §1.8
- **内容**：
  1. ✅ 明确浏览器 WebSocket API 不向 JavaScript 暴露握手失败的 HTTP 401/403 详情
  2. ✅ 应用启动时先调用 `GET /api/v1/auth/me`
  3. ✅ `/me` 返回 200 后才建立 WebSocket
  4. ✅ `/me` 返回 401 时只尝试一次 single-flight `POST /api/v1/auth/refresh`
  5. ✅ WebSocket 建立前 `onerror` 时不直接推断 401/403，调 `/me` 检查认证状态，`/me` 401 执行一次 single-flight refresh，`/me` 200 按网络/Origin/服务异常处理
  6. ✅ 禁止握手失败导致无限 refresh 循环
- **自检**：`rg -n "onerror|GET /api/v1/auth/me|single-flight" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
- **结果**：✅ 通过

### 三、Refresh 后的连接迁移

- **章节位置**：WEBSOCKET_CONTRACT.md §7.4.3
- **内容**：
  1. ✅ `POST /api/v1/auth/refresh` 必须携带 `X-CSRF-Token`
  2. ✅ Refresh 成功后创建新 WebSocket
  3. ✅ 等待新连接 `connection.established`
  4. ✅ 在新连接逐项恢复订阅
  5. ✅ 等待每个 `conversation.subscribed` 确认
  6. ✅ 服务端重新校验每个订阅权限
  7. ✅ 必要订阅全部恢复后新连接成为活动连接
  8. ✅ 正常关闭旧连接
  9. ✅ 清理旧连接心跳、事件监听器和重连计时器
  10. ✅ Refresh 失败进入 `AUTH_FAILED`，不再连接
- **结果**：✅ 通过

### 四、完整状态机

- **章节位置**：WEBSOCKET_CONTRACT.md §7.5
- **定义的 10 个状态**：`DISCONNECTED`、`CONNECTING`、`OPEN`、`REFRESHING`、`RESTORING`、`RECONNECTING`、`AUTH_FAILED`、`FORBIDDEN`、`PAUSED`、`CLOSED`
- `RESTORING` 含义：新连接已建立，正在恢复订阅和执行必要 HTTP 回补，尚未成为活动连接
- **状态转换表列**：当前状态、触发条件、下一状态、是否自动重试、UI 行为
- **覆盖场景**：
  - ✅ 初次连接
  - ✅ 握手失败
  - ✅ Token 临期（`connection.expiring`）
  - ✅ 4401
  - ✅ 4403
  - ✅ 网络断开
  - ✅ 心跳超时
  - ✅ 服务重启（1012）
  - ✅ Refresh 成功（→ `RESTORING`，不再直接到 `OPEN`）
  - ✅ Refresh 失败
  - ✅ 用户注销
  - ✅ RESTORING 完成后进入 `OPEN`
  - ✅ RESTORING 中单个订阅无权限移除后继续恢复
  - ✅ RESTORING 中连接断开进入 `RECONNECTING`
  - ✅ RESTORING 中认证失败进入 `AUTH_FAILED`
- **状态机约束**：`RESTORING` 是 `REFRESHING`/`RECONNECTING` 到 `OPEN` 之间的必经中间状态
- **自检**：`rg -n "DISCONNECTED|CONNECTING|OPEN|REFRESHING|RECONNECTING|AUTH_FAILED|FORBIDDEN|PAUSED|CLOSED|RESTORING" docs/api/WEBSOCKET_CONTRACT.md` 全部匹配
- **结果**：✅ 通过

### 五、网络重连规则

- **章节位置**：WEBSOCKET_CONTRACT.md §6.1（退避）和 §6.2（白名单与禁止清单）
- **退避时间表**：
  - ✅ 第 1 次立即
  - ✅ 后续 1、2、4、8、16、30 秒
  - ✅ 最大 30 秒
  - ✅ ±20% jitter
  - ✅ 连续 10 次失败进入 PAUSED
  - ✅ PAUSED 允许手动重试
  - ✅ offline 变为 online 时重置计数并立即尝试一次
- **允许自动重连**：✅ 网络异常、1001、1011、1012、4408、4429（等待 `retry_after_ms`）
- **禁止自动重连**：✅ 1000、1008、4403、4406、用户注销、Refresh 失败、明确 Origin 配置错误
- **自检**：`rg -n "jitter|10次|offline|online" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
- **结果**：✅ 通过

### 六、重新订阅

- **章节位置**：WEBSOCKET_CONTRACT.md §7.8
- **内容**：
  1. ✅ 客户端只保存 `conversation_id`，不保存事件正文
  2. ✅ 收到 `connection.established` 后才能重订阅
  3. ✅ 按顺序发送 `conversation.subscribe`
  4. ✅ 每项等待 `conversation.subscribed` 确认
  5. ✅ 服务端重新鉴权
  6. ✅ 无权限项从本地订阅集合移除
  7. ✅ 单项失败不关闭整个连接
  8. ✅ 全部完成后才切换活动连接
- **自检**：`rg -n "conversation.subscribed" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
- **结果**：✅ 通过

### 七、HTTP 回补

- **章节位置**：WEBSOCKET_CONTRACT.md §6.3
- **路径**：`GET /api/v1/conversations/{conversation_id}/messages?page=1&page_size=50`
- **内容**：
  1. ✅ 记录每个会话最后确认的 `message_id` 和 `created_at`
  2. ✅ 从第一页开始分页
  3. ✅ 使用 `message_id` 去重
  4. ✅ 遇到最后确认 `message_id` 时停止
  5. ✅ 达到安全页数上限时停止并提示刷新
  6. ✅ 会话元数据回源：`GET /api/v1/conversations/{conversation_id}`
  7. ✅ 场景状态回源：`GET /api/v1/scene-instances/{scene_instance_id}`
  8. ✅ `sequence` 跳号触发 HTTP 回源
  9. ✅ HTTP API 是最终事实来源
  10. ✅ 不新增 `since`、`cursor` 或 `last_event_id` 参数
- **自检**：
  - `rg -n "最后确认|安全页数|HTTP API是最终事实来源" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
  - `rg -n "\?since=|cursor=|last_event_id" docs/api/WEBSOCKET_CONTRACT.md` 无匹配（确认不新增参数）
  - `rg -n "\{id\}/messages" docs/api/WEBSOCKET_CONTRACT.md` 无匹配（旧路径已修正）
- **结果**：✅ 通过

### 八、事件去重

- **章节位置**：WEBSOCKET_CONTRACT.md §6.4
- **内容**：
  - ✅ 删除无限增长的 `processed_events = set()`
  - ✅ 最多 1000 个 `event_id`
  - ✅ 或保留 24 小时
  - ✅ 先达到者触发淘汰
  - ✅ `event_id` 用于传输去重
  - ✅ `message_id` 等业务 ID 用于业务幂等
  - ✅ `sequence` 只保证单连接或单订阅流内递增
  - ✅ 不保证跨连接全局连续
- **自检**：`rg -n "processed_events = set" docs/api/WEBSOCKET_CONTRACT.md` 无匹配（已删除）
- **结果**：✅ 通过

### 九、关闭码和心跳

- **章节位置**：WEBSOCKET_CONTRACT.md §7.6（关闭码）和 §7.7（心跳）
- **关闭码**：
  - ✅ 4401：Token 过期或认证上下文失效（两个 reason：`access_token_expired` / `authentication_context_invalid`）
  - ✅ 4403：权限拒绝或账号禁用
  - ✅ 4406：协议主版本不支持
  - ✅ 4408：心跳超时
  - ✅ 4429：遵守 `retry_after_ms`（来源为 error 事件，默认 30000ms，范围 1000-300000ms）
  - ✅ 所有 close reason 为固定机器可读字符串
  - ✅ 用户注销不重连
- **心跳计时器清理**：
  - ✅ 断线时清理
  - ✅ Refresh 时清理
  - ✅ 旧连接替换时清理
  - ✅ 页面销毁时清理
- **结果**：✅ 通过

### 九-B、复审整改项

- **章节位置**：WEBSOCKET_CONTRACT.md §4.1、§7.5、§7.6
- **内容**：
  1. ✅ 修正 `connection.expiring` 字段：删除 `grace_seconds`，统一为 `expires_at`/`refresh_required`/`reconnect_required`（§4.1）
  2. ✅ 新增 `connection.expired` 事件定义并加入 §9.1 事件清单
  3. ✅ 新增 `RESTORING` 状态，修复状态转换表：`REFRESHING`/`RECONNECTING` + `connection.established` → `RESTORING`（不再直接到 `OPEN`）
  4. ✅ 区分 4401 两个 reason：`access_token_expired`（自然过期）/ `authentication_context_invalid`（撤销或失效）
  5. ✅ 定义 4429 `retry_after_ms` 来源：error 事件传递，默认 30000ms，范围 1000-300000ms
  6. ✅ §7.4.3 连接迁移流程更新为经过 `RESTORING` 状态
  7. ✅ §7.4.5 更新为两个 reason 描述
  8. ✅ 变更记录增加复审整改条目
- **结果**：✅ 通过

### 十、计划和日志整理

- **P0_P1_REMEDIATION_PLAN.md**：
  - ✅ R1-23 完成摘要已移至 R1-C 表格之后（R1 阶段完成摘要区域）
  - ✅ 文件底部不再有 R1-23 摘要
  - ✅ R1-24 保持 `[ ]`
  - ✅ WEBSOCKET_CONTRACT.md 仍为 DRAFT
- **R1-23 任务日志**：本文件已逐项扩充，记录实际章节位置和自检结果

### 十一、自检命令

待执行的自检命令：

```bash
git diff --check

rg -n "onerror|GET /api/v1/auth/me|single-flight|DISCONNECTED|CONNECTING|OPEN|REFRESHING|RECONNECTING|AUTH_FAILED|FORBIDDEN|PAUSED|CLOSED" docs/api/WEBSOCKET_CONTRACT.md

rg -n "jitter|10次|offline|online|conversation.subscribed|最后确认|安全页数|HTTP API是最终事实来源" docs/api/WEBSOCKET_CONTRACT.md

rg -n "processed_events = set|\?since=|cursor=|last_event_id|\{id\}/messages" docs/api/WEBSOCKET_CONTRACT.md

git status --short
```

预期结果：
- `git diff --check` 通过（无空白错误）
- 第一条 rg 命令有大量匹配（状态机、握手恢复等关键词存在）
- 第二条 rg 命令有匹配（jitter、offline、conversation.subscribed 等关键词存在）
- 第三条 rg 命令无匹配（processed_events=set、since=、cursor=、last_event_id、{id}/messages 均不存在）
- `git status --short` 不再出现 `.backup` 文件

## 待审计要求

- 22 项验收标准全部满足
- 不新增 HTTP 端点，68 个 MVP 端点数量不变
- WEBSOCKET_CONTRACT 保持 DRAFT 状态
- R1-24 仍未开始
- 不提交 Git，不推送，等待 Codex 复审
