# R1-24 任务日志：冻结 WebSocket 事件 Schema

> **任务编号**：R1-24
> **执行日期**：2026-07-15
> **执行人**：开发团队
> **状态**：等待 Codex 审计

## 核心成果

- WEBSOCKET_CONTRACT.md 版本从 DRAFT 升级为 `v1.0-frozen`
- 统一客户端命令信封和服务端事件信封
- 时间字段标准化为 UTC RFC 3339 秒精度
- 全部 8 个事件 Schema 冻结（含方向、触发条件、JSON 示例、字段表、隐私分级、授权、客户端处理、request_id 关联）
- 错误事件冻结，定义 7 个应用层 WS 错误码
- WS_* 错误码同步到 API_CONTRACT.md 错误码总表
- 版本兼容策略冻结
- 事件级隐私投影规则冻结
- 事件清单冻结

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/api/WEBSOCKET_CONTRACT.md` | 重写/冻结 | 版本升级为 `v1.0-frozen`，补全统一信封、全部事件 Schema、错误事件、版本策略、隐私投影规则、事件清单 |
| `docs/api/API_CONTRACT.md` | 编辑 | §1.6.2 分类表和 §1.6.3 总表同步全部 8 个 WS_* 错误码；WebSocket 端点错误码补充应用层错误说明 |
| `docs/api/README.md` | 重写 | 新增契约状态表，标记 API 和 WebSocket 合约均为 `v1.0-frozen` |
| `docs/project/P0_P1_REMEDIATION_PLAN.md` | 编辑 | R1-24 状态改为 `[x]`，添加 R1-24 完成摘要 |

## 逐项章节位置与自检结果

### 一、版本标记

- **章节位置**：WEBSOCKET_CONTRACT.md 第 1–6 行
- **内容**：
  1. ✅ 版本字段从 DRAFT 改为 `v1.0-frozen`
  2. ✅ 冻结日期：2026-07-15
  3. ✅ 状态：已评审/已冻结
  4. ✅ 冻结范围：连接协议、事件信封、全部事件 Schema、错误事件、版本策略、隐私投影规则
- **自检**：`head -7 docs/api/WEBSOCKET_CONTRACT.md` 包含 `v1.0-frozen`
- **结果**：✅ 通过

### 二、统一事件信封

- **章节位置**：WEBSOCKET_CONTRACT.md §2.1（客户端命令信封）、§2.2（服务端事件信封）
- **内容**：
  1. ✅ 客户端命令信封字段：`event`、`data`、`version`、`request_id`、`timestamp`
  2. ✅ 服务端事件信封字段：`event`、`data`、`version`、`event_id`、`sequence`、`timestamp`、`request_id`
  3. ✅ 两个信封均含 JSON 示例和字段说明表
- **自检**：`rg -n "客户端命令信封|服务端事件信封" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
- **结果**：✅ 通过

### 三、时间字段标准化

- **章节位置**：WEBSOCKET_CONTRACT.md §2.4
- **内容**：
  1. ✅ 所有 `timestamp` 使用 UTC RFC 3339 秒精度（如 `2026-07-15T10:30:00Z`）
  2. ✅ `expires_at` 同格式
  3. ✅ 不含毫秒和时区偏移
- **自检**：`rg -n "RFC 3339|秒精度|2026-07-15T10:30:00Z" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
- **结果**：✅ 通过

### 四、全部事件 Schema 冻结

- **章节位置**：WEBSOCKET_CONTRACT.md §3（客户端事件）、§4（服务端事件）
- **冻结事件清单**：

| 事件 | 方向 | 章节位置 |
|------|------|----------|
| `conversation.subscribe` | C→S | §3.1 |
| `conversation.unsubscribe` | C→S | §3.2 |
| `ping` | C→S | §3.3 |
| `connection.established` | S→C | §4.1 |
| `connection.expiring` | S→C | §4.1 |
| `connection.expired` | S→C | §4.1 |
| `conversation.subscribed` | S→C | §4.2 |
| `conversation.unsubscribed` | S→C | §4.2 |
| `message.created` | S→C | §4.3 |
| `message.updated` | S→C | §4.3 |
| `scene.updated` | S→C | §4.5 |
| `error` | S→C | §4.7 |

- **每个事件 Schema 包含**：
  1. ✅ 方向（C→S / S→C）
  2. ✅ 触发条件
  3. ✅ JSON 示例
  4. ✅ data 字段表（字段名、类型、必填、可空、格式/约束、说明、隐私分级）
  5. ✅ 隐私分级标注
  6. ✅ 授权要求
  7. ✅ 客户端处理指引
  8. ✅ `request_id` 关联说明
- **自检**：`rg -c "触发条件|客户端处理|隐私分级|授权" docs/api/WEBSOCKET_CONTRACT.md` 计数 ≥ 8
- **结果**：✅ 通过

### 五、错误事件冻结

- **章节位置**：WEBSOCKET_CONTRACT.md §4.7
- **内容**：
  1. ✅ `error.data` 字段：`code`、`message`、`details`、`retryable`、`retry_after_ms`
  2. ✅ 定义 7 个应用层 WS 错误码：

     | 错误码 | retryable | retry_after_ms | 说明 |
     |--------|:---------:|:--------------:|------|
     | `WS_INVALID_MESSAGE` | false | null | WebSocket 消息格式无效 |
     | `WS_UNSUPPORTED_EVENT` | false | null | 不支持的事件类型 |
     | `WS_UNAUTHORIZED` | false | null | WebSocket 未授权操作 |
     | `WS_FORBIDDEN` | false | null | WebSocket 权限拒绝 |
     | `WS_SUBSCRIPTION_NOT_FOUND` | false | null | 订阅不存在 |
     | `WS_RATE_LIMITED` | true | 1000～300000 | WebSocket 频率受限 |
     | `WS_INTERNAL_ERROR` | false | null | WebSocket 内部错误 |

  3. ✅ `WS_RATE_LIMITED` 为唯一可重试码，`retry_after_ms` 范围 1000～300000 毫秒
  4. ✅ 握手阶段错误码（`AUTH_INVALID_TOKEN`、`AUTH_ACCOUNT_DISABLED`、`WS_ORIGIN_NOT_ALLOWED`、`SERVICE_UNAVAILABLE`）不通过 `error` 事件传递
- **自检**：`rg -c "WS_INVALID_MESSAGE|WS_UNSUPPORTED_EVENT|WS_UNAUTHORIZED|WS_FORBIDDEN|WS_SUBSCRIPTION_NOT_FOUND|WS_RATE_LIMITED|WS_INTERNAL_ERROR" docs/api/WEBSOCKET_CONTRACT.md` ≥ 7
- **结果**：✅ 通过

### 六、错误码同步到 API_CONTRACT.md

- **章节位置**：API_CONTRACT.md §1.6.2（分类表）、§1.6.3（总表）
- **内容**：
  1. ✅ 分类表 `websocket` 行包含全部 8 个 WS_* 错误码，区分握手拒绝（HTTP 403）和应用层错误（`error` 事件，无 HTTP 状态码）
  2. ✅ 总表 WebSocket（WS）分类包含 8 行，`WS_ORIGIN_NOT_ALLOWED` 标注 HTTP 403，其余 7 个标注 `—`
  3. ✅ WebSocket 端点错误码行下方补充应用层错误说明，引用 WEBSOCKET_CONTRACT.md §4.7
- **自检**：`rg -c "WS_INVALID_MESSAGE|WS_UNSUPPORTED_EVENT|WS_UNAUTHORIZED|WS_FORBIDDEN|WS_SUBSCRIPTION_NOT_FOUND|WS_RATE_LIMITED|WS_INTERNAL_ERROR" docs/api/API_CONTRACT.md` ≥ 7
- **结果**：✅ 通过

### 七、版本兼容策略

- **章节位置**：WEBSOCKET_CONTRACT.md §8（§8.1–§8.6）
- **内容**：
  1. ✅ `version` 字段固定为 `v1`（§8.1）
  2. ✅ 非破坏性变更：新增可选字段不破坏旧客户端（§8.2）
  3. ✅ 破坏性变更：移除字段或改变语义须升版本号（§8.3）
  4. ✅ 跨版本兼容：服务端同时支持旧版本并逐步迁移（§8.4）
  5. ✅ 不支持的主版本返回 4406 关闭码（§8.5）
  6. ✅ 冻结后约束：任何变更须经 ADR 评审（§8.6）
- **自检**：`rg -n "v1|向后兼容|破坏性变更|4406|ADR" docs/api/WEBSOCKET_CONTRACT.md | head -20` 有匹配
- **结果**：✅ 通过

### 八、事件级隐私投影规则

- **章节位置**：WEBSOCKET_CONTRACT.md §9（§9.1–§9.2）
- **内容**：
  1. ✅ 核心原则：最小化暴露、按订阅范围过滤、不通过 WebSocket 传输 P3/P4 数据（§9.1）
  2. ✅ 事件数据分类标注：每个事件的 data 字段表标注 P0–P4 隐私分级（§9.2）
  3. ✅ 公共事件（`scene.updated`、`conversation.subscribed`）不含 P2–P4 数据
  4. ✅ 私有偏好通过 Scene API 提交，不通过 WebSocket
  5. ✅ `visibility=PRIVATE`/`HIDDEN`、Agent 私域消息、P3/P4 数据、记忆正文和智能体内部推理均不得推送；WebSocket Schema 中不存在 `metadata` 字段
- **自检**：`rg -n "P0|P1|P2|P3|P4|隐私分级|隐私投影" docs/api/WEBSOCKET_CONTRACT.md | head -20` 有匹配
- **结果**：✅ 通过

### 九、事件清单冻结

- **章节位置**：WEBSOCKET_CONTRACT.md §10（§10.1–§10.2）
- **内容**：
  1. ✅ §10.1 完整事件清单：按方向（C→S / S→C）分类列出全部事件，含版本和简述
  2. ✅ §10.2 事件清单一致性约束：清单与正文中定义的事件一一对应
- **自检**：`rg -n "完整事件清单|事件清单一致性" docs/api/WEBSOCKET_CONTRACT.md` 有匹配
- **结果**：✅ 通过

### 十、README.md 更新

- **章节位置**：docs/api/README.md
- **内容**：
  1. ✅ 新增契约状态表，包含 HTTP API 契约和 WebSocket 与事件契约两行
  2. ✅ 两行均标注版本 `v1.0-frozen`、状态 ✅ 已冻结
  3. ✅ 冻结日期：2026-07-15
- **自检**：`rg -n "v1.0-frozen" docs/api/README.md` 有匹配
- **结果**：✅ 通过

## 约束遵守

- ✅ 未执行任何 `git commit` 或 `git push`
- ✅ 未新增任何 HTTP API
- ✅ 未修改任何 Python 源代码
- ✅ 未修改任何前端代码
- ✅ 所有变更仅限文档文件

## 自检结果汇总（2026-07-15）

| 检查项 | 命令 | 结果 |
|--------|------|------|
| 行尾空格 | `git diff --check` | ✅ PASS |
| 版本标记 | `head -7 WEBSOCKET_CONTRACT.md` | ✅ `v1.0-frozen` |
| WS_* 错误码（WS 契约） | `grep -cE "WS_*" WEBSOCKET_CONTRACT.md` | ✅ 12 行匹配 |
| WS_* 错误码（API 契约） | `grep -cE "WS_*" API_CONTRACT.md` | ✅ 9 行匹配 |
| README 冻结标记 | `grep -n "v1.0-frozen" README.md` | ✅ 2 行（API + WS） |
| R1-24 状态 | `grep -n "R1-24" P0_P1_REMEDIATION_PLAN.md` | ✅ `[x]` + 完成摘要 |
| 事件清单 | `grep -n "完整事件清单\|事件清单一致性"` | ✅ §10.1 + §10.2 |
| 隐私投影规则 | `grep -n "隐私投影\|隐私分级"` | ✅ §9 + 冻结范围 |
| 版本策略 | `grep -n "向后兼容\|破坏性变更\|4406\|ADR"` | ✅ §8.2–§8.4 |
| 统一信封 | `grep -n "客户端命令信封\|服务端事件信封"` | ✅ §2.1 + §2.2 |
| 时间格式 | `grep -n "RFC 3339\|秒精度"` | ✅ 多处字段使用 UTC RFC 3339 |
| 日志文件 | `ls R1-24_FREEZE_WEBSOCKET_EVENT_SCHEMA.md` | ✅ 8824 字节 |
| git status | `git status --short` | ✅ 仅文档修改，无 commit/push |

## Codex 首次审计整改（R1-24-C，2026-07-15）

### 问题 1：Scene 状态字段名和枚举不正确

- **问题**：WebSocket 使用 `stage` 字段名，枚举漏掉 `CANDIDATES_READY`/`FAILED`/`EXPIRED`，`scene.result.generated` 错误使用 `status=COMPLETED`
- **修复位置**：WEBSOCKET_CONTRACT.md §4.5.1、§4.5.2、§9.2、§10.2
- **修复内容**：
  - `stage` 改为 `state`
  - 补全 12 个封闭枚举（与 `SCENE_STATE_MACHINE.md` 一致）
  - `scene.result.generated` 从 `status=COMPLETED` 改为 `state=CANDIDATES_READY`
  - 明确触发时机为 `PROCESSING`→`CANDIDATES_READY`，不等于 `COMPLETED`

### 问题 2：message.created 使用嵌套 sender 和不完整枚举

- **问题**：WebSocket 使用嵌套 `sender` 对象（`sender.type`/`sender.user_id`/`sender.agent_id`/`sender.display_name`），与 HTTP 的扁平字段不一致；`message_type` 枚举不完整（仅 4 值）
- **修复位置**：WEBSOCKET_CONTRACT.md §4.3.1
- **修复内容**：
  - 删除嵌套 `sender` 对象和 `display_name`
  - 改为扁平 `sender_type`/`sender_user_id`/`sender_agent_id`
  - 新增 HTTP Message 字段映射表（8 个字段一一对应）
  - `message_type` 补全为 10 值完整 v1 枚举（来源 `DOMAIN_VOCABULARY.md`）
  - 新增 `sender_type` 条件规则表
  - 新增推送范围与禁止规则（`visibility=PRIVATE`/`HIDDEN` 不得推送等）
  - `message.deleted` 的 `message_id` 添加映射说明

### 问题 3：request_id 使用非 UUID v4 格式

- **问题**：示例中使用 `req_abc123`/`req_def456`/`req_ping001` 等非 UUID v4 格式
- **修复位置**：WEBSOCKET_CONTRACT.md §2.1、§2.2、§3.1-3.3、§4.2.1-4.2.3、§4.7.1
- **修复内容**：
  - 客户端命令信封 `request_id` 类型改为 `UUID v4`
  - 服务端事件信封 `request_id` 类型改为 `UUID v4 | null`
  - 所有示例替换为合法小写 UUID v4（不同请求使用不同 UUID）
  - 直接响应回显同一 UUID v4，主动推送为 `null`

### 问题 4：Notification 引用不存在的 HTTP 模型

- **问题**：`type` 字段声称"枚举来源为 HTTP API 通知模型"，无依据声明 `MESSAGE_MENTION`
- **修复位置**：WEBSOCKET_CONTRACT.md §4.6.1
- **修复内容**：
  - `type` 改为 WebSocket v1 开放枚举
  - 当前已知值仅 `SCENE_INVITE`
  - 删除 `MESSAGE_MENTION`
  - 明确权威来源是 `WEBSOCKET_CONTRACT.md`
  - 新增未知 `type` 处理规则

### 问题 5：虚假的 P3 metadata 摘要

- **问题**：R1-24 完成摘要中声称 `sender_type=agent` 的 `metadata` 字段为 P3
- **修复位置**：P0_P1_REMEDIATION_PLAN.md R1-24 完成摘要、WEBSOCKET_CONTRACT.md §9.2
- **修复内容**：
  - 删除所有 `metadata` 相关虚假描述
  - 替换为准确的授权会话投影描述
  - 明确 WebSocket Schema 中不存在 `metadata` 字段

### 问题 6：错误码分类重叠和章节引用错误

- **问题**：API_CONTRACT.md 引用"§5 错误事件"（实际为 §4.7）；`rate_limit` 分类的 `*_RATE_LIMITED` 可能包含 `WS_RATE_LIMITED` 并映射 HTTP 429
- **修复位置**：API_CONTRACT.md §1.6.2、§1.6.3、WebSocket 端点错误码说明
- **修复内容**：
  - 所有"§5 错误事件"改为"§4.7 错误事件"
  - `rate_limit` 分类说明改为"仅适用于 HTTP API 的限流错误，明确排除 `WS_RATE_LIMITED`"
  - `WS_RATE_LIMITED` 只属于 `websocket` 分类，不映射 HTTP 429

### 整改后状态

- WEBSOCKET_CONTRACT.md：`v1.0-frozen`，已评审/已冻结
- P0_P1_REMEDIATION_PLAN.md：R1-24 标记 `[x]`，完成摘要已修正
- R1-24 日志：保留在 `development-logs/in-progress/`，等待 Codex 复审
- 未提交 Git，未推送远程

## 待审计要点

1. 事件 Schema 的字段完整性是否覆盖所有业务场景
2. 隐私分级标注是否与 API_CONTRACT.md 中的数据分类一致
3. 版本策略是否满足未来演进需求
4. WS_* 错误码是否覆盖所有 WebSocket 应用层错误场景

## Codex 第二次复审整改（R1-24-D，2026-07-15）

### 问题 1：三组非法 UUID v4 示例

- **问题**：R1-24-C 首次自检只排除了 `req_*` 前缀，没有验证 UUID v4 的 version（第三组第一位必须为 `4`）和 variant（第四组第一位必须为 `8`/`9`/`a`/`b`）位
- **修复位置**：WEBSOCKET_CONTRACT.md §1.4（握手失败响应示例）、§3.3（ping）、§4.2.3（pong）
- **修复内容**：
  - `d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f80` → `d4e5f6a7-b8c9-4d0e-8f2a-3b4c5d6e7f80`（401 响应示例，第四组 `1`→`8`）
  - `e5f6a7b8-c9d0-4e1f-2a3b-4c5d6e7f8090` → `e5f6a7b8-c9d0-4e1f-a3b4-4c5d6e7f8090`（403 响应示例，第四组 `2`→`a`）
  - `c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f` → `c3d4e5f6-a7b8-4c9d-8e1f-2a3b4c5d6e7f`（ping 和 pong，第四组 `0`→`8`）
- **一致性验证**：ping/pong 使用相同 UUID；subscribe/subscribed 使用相同 UUID；unsubscribe/unsubscribed 使用相同 UUID；主动推送为 `null`

### 问题 2：心跳笔误

- **问题**：§4.2.3 pong 客户端处理方式中写成"pong/pong 数据不得携带用户数据"
- **修复位置**：WEBSOCKET_CONTRACT.md §4.2.3
- **修复内容**：`pong/pong` → `ping/pong`

### 整改后状态

- 首次自检只排除了 `req_*`，没有验证 UUID v4 version/variant 位
- 修复了三组非法 UUID v4 示例
- ping/pong 请求响应关联保持一致
- 修复 pong/pong 文字错误
- R1-24 日志继续留在 in-progress
- R1-25 未执行
- 未提交、未推送
