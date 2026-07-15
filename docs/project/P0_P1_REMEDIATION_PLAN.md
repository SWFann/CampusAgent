# CampusAgent P0/P1 整改计划表

> 版本：v1.0
>
> 日期：2026-07-14
>
> 来源：P0/P1 独立审计结果
>
> 目标：在进入 P2 前，使 P0 契约真正冻结、P1 工程真正可安装、可运行、可测试、可构建、可追溯

## 1. 使用方式

状态约定：

- `[ ]` 未开始；
- `[~]` 进行中；
- `[x]` 已完成且验收通过；
- `[!]` 阻塞，必须记录原因；
- `[-]` 经明确决策取消。

执行规则：

1. 严格按照 R0 → R1 → R2 → R3 → R4 顺序整改；
2. 每次只处理一个任务编号，不进行大范围混合修改；
3. 修改契约前先判断是否需要 ADR；
4. 每个任务都必须同时完成修改、验证和证据记录；
5. 不允许只修改“完成总结”来掩盖实现缺口；
6. P0、P1 在 R4 验收前保持“整改中”，不得开始 P2；
7. 所有 Python 命令统一通过 Conda 环境 `CampusAgent` 执行；
8. 所有提交不得包含真实用户数据、密钥、`.env` 或测试数据库。

## 2. 整改批次总览

| 批次 | 目标 | 建议工时 | 前置条件 | 退出条件 |
|---|---|---:|---|---|
| R0 | 建立安全、可追溯的整改基线 | 1–2 小时 | 当前工作树 | 文件清单明确，进入整改分支 |
| R1 | 修复 P0 契约、角色和威胁模型 | 6–10 小时 | R0 | 所有 P0 文档一致且评审通过 |
| R2 | 修复 P1 Python/API/测试底座 | 6–10 小时 | R1 | API 可导入，后端检查全部通过 |
| R3 | 修复 Workspace、命令、CI 和文档 | 5–8 小时 | R2 | 前后端全套命令和 CI 通过 |
| R4 | 执行最终门禁和归档证据 | 2–4 小时 | R1–R3 | P0/P1 可正式重新标记完成 |

预计整改总量：约 **20–34 小时**。若测试暴露新的结构性问题，应增加任务，不要压缩验收步骤。

---

## R0：版本控制与整改基线

目标：避免当前大量未跟踪文件丢失或被错误混入提交，让后续每项整改都可审查、可回退。

| 状态 | ID | 整改内容 | 涉及位置 | 验收方式 |
|---|---|---|---|---|
| [ ] | R0-01 | 保存当前工作树清单 | 仓库根目录 | 将 `git status --short` 输出保存到整改日志 |
| [ ] | R0-02 | 创建整改分支 | Git | 分支建议 `fix/p0-p1-audit-remediation` |
| [ ] | R0-03 | 区分原始产物与整改产物 | P0/P1 文件 | 列出 Claude 已生成文件、已有文件和本次新增文件 |
| [ ] | R0-04 | 检查敏感信息 | 全仓库 | 扫描密钥、Token、真实学号、真实聊天和数据库文件 |
| [ ] | R0-05 | 确认换行与编码 | Markdown、YAML、Python、TS | 所有文本为 UTF-8，提交前 `git diff --check` 通过 |
| [ ] | R0-06 | 建立整改记录 | `development-logs/` | 每项整改记录任务、修改文件、命令结果和提交哈希 |
| [ ] | R0-07 | 提交原始 P0/P1 快照 | Git | 在不包含密钥的前提下形成可追溯基线提交 |

建议提交：

```text
chore(project): checkpoint initial P0 and P1 deliverables
```

R0 退出条件：当前 P0/P1 产物已进入 Git；工作内容不会因后续整改而失去原始对照；远端存在整改分支。

---

## R1：P0 契约整改

### R1-A：统一领域角色

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [ ] | R1-01 | 确认全局角色集合 | 在四角色和六角色方案中作出正式决定 | 只能存在一套 `GlobalRole` 枚举 |
| [ ] | R1-02 | 记录角色变更 ADR | 新增角色模型 ADR 或修订未接受 ADR | 解释 Counselor、OrganizationAdmin 属于全局角色还是组织授权能力 |
| [ ] | R1-03 | 同步角色文档 | 计划书、词汇表、权限矩阵、API 示例 | 所有文档角色名称完全一致 |
| [ ] | R1-04 | 清理待讨论术语 | `DOMAIN_VOCABULARY.md` | Consent、Capsule 等术语已确认或明确延期，不再处于未决状态 |
| [ ] | R1-05 | 建立枚举对照表 | 领域词汇表 | 中英文、数据库值、API 值一一对应 |

验收检查：

- 搜索 `GlobalRole`、`COUNSELOR`、`ORG_ADMIN` 和 `OrganizationAdmin`；
- 任意角色都能在权限矩阵中找到唯一含义；
- 角色变更有 ADR 依据。

### R1-B：补全 HTTP API 契约

**返工说明（2026-07-14 审计后）**：
- ✅ R1-08～R1-10 已完成返工，任务日志位于 `development-logs/completed/remediation-r1/`
- ✅ R1-08～R1-10 的端点已添加稳定唯一编号（EP-CONV-024～028、EP-AGENT-033～038、EP-MEM-039～045）
- ✅ Agent API 隐私矛盾已修正：响应返回脱敏后的 `run_summary`，不暴露模型名、token_usage、reasoning_summary
- ✅ Memory API 已明确：share/revoke 端点移出 MVP，由 Agent permissions API 和 Scene consent API 替代
- ✅ Conversation API 已明确：hard_delete 仅适用于公共会话消息，不得作用于私域消息
- ✅ R1-11 已完成补全，任务日志位于 `development-logs/completed/remediation-r1/`
- ✅ R1-12 已完成补全，任务日志位于 `development-logs/completed/remediation-r1/`
- ✅ R1-13 已完成补全，任务日志位于 `development-logs/completed/remediation-r1/`，新增 11 个端点（EP-ADMIN-061～071），明确管理员隐私边界
- ✅ R1-14 已完成统一，路径变量与领域词汇表一致，资源命名无混用
- ✅ R1-15 已完成统一，建立 9 类错误分类体系、68+ 错误码主表、统一响应结构（含 retryable 字段），所有 R1-08～R1-13 端点已关联错误码
- ✅ R1-16 已完成统一，建立完整幂等规则（18 必支持 + 3 可选端点）、统一请求规则（分页/排序/过滤/时间/ID/空值）、统一响应模型（6 种）、统一校验规则，所有端点引用 Section 1.3～1.8
- ✅ R1-17 已完成冻结，`API_CONTRACT.md` v1.0-frozen（71 个端点），发现并修复 1 处端点方法不一致（EP-MODEL-059 embedding），WEBSOCKET_CONTRACT.md 仍为 DRAFT（有安全问题待 R1-22 处理）
- ✅ R1-14～R1-17 返工整改：MVP_SCOPE.md 路径变量已统一（{org_id}→{organization_id} 等）；MVP_ENDPOINT_TRACEABILITY.md 4 处"未文档化"修正为"已文档化"，统计区一致；错误码总表补入 USER_ALREADY_EXISTS、USER_PERMISSION_DENIED、DIRECTORY_ORG_NOT_FOUND、MESSAGE_NOT_FOUND、MESSAGE_PERMISSION_DENIED；幂等作用域明确为 actor_id + method + path + body_hash + key 复合键
- ✅ R1-18 已完成统一，Web 浏览器端主认证方式为 HttpOnly Secure SameSite Cookie + JWT，login/refresh/logout/me 端点 Cookie 行为一致，内部服务 Bearer Token 明确范围
- ✅ R1-19 已完成定义，CSRF 防护方案采用 Double-Submit Cookie 模式（非 HttpOnly `csrf_token` Cookie + `X-CSRF-Token` 请求头），明确 CSRF 仅强制用于 Cookie 已认证的浏览器写请求，login/register 未认证端点豁免，3 个 CSRF 错误码已加入 API_CONTRACT 错误码总表和端点错误码清单
- ✅ R1-20 已完成修正，登录响应不返回 access_token/refresh_token（仅返回用户元数据 + Set-Cookie），新增 csrf_token Cookie，错误码统一为 AUTH_INVALID_CREDENTIALS（防止账号枚举）
- ✅ R1-21 已完成修正，Refresh 流程采用 Token 轮换（每次刷新颁发新 refresh_token，旧 token 立即失效），新增 token family 机制和重放检测（重放时撤销整个 family），新增 AUTH_REFRESH_TOKEN_EXPIRED 错误码，Logout 清除 access_token/refresh_token/csrf_token 三个 Cookie 并撤销 token family
- ✅ R1-18～R1-21 认证链路复审：明确 CSRF bootstrap 流程（login/register 豁免，成功后签发 csrf_token），register 自动登录增加 Set-Cookie: csrf_token，统一 auth 端点 CSRF 豁免范围，CSRF_TOKEN_EXPIRED 降级为可选增强（P2 实现），API_CONTRACT.md 变更记录增加 R1-C 安全修订
- ✅ R1-22 已完成修正，WebSocket 鉴权从 URL Token 改为 HttpOnly access_token Cookie，路径为 /api/v1/ws，强制 Origin 白名单校验，禁止 URL Token/ticket/连接后发送 Token，不新增 HTTP 端点，MVP HTTP 端点仍为 68 个

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [ ] | R1-06 | 建立 68 端点对照清单 | `MVP_SCOPE.md` vs `API_CONTRACT.md` | 每个 MVP 端点都有契约章节和唯一编号 |
| [ ] | R1-07 | 补全 Directory API | search、tree、recommended | 请求、响应、权限、分页和隐私投影齐全 |
| [x] | R1-08 | 补全 Conversation API | 更新会话、参与者管理、消息列表和删除 | 成员权限和消息可见范围明确 |
| [x] | R1-09 | 补全 Agent API | chat、permissions 查询/修改、runs | 授权、代理等级和运行元数据明确 |
| [x] | R1-10 | 补全 Memory API | detail、update、access-log、export | owner、purpose、consent 和导出范围明确 |
| [x] | R1-11 | 补全 Scene API | 场景定义查询、实例查询、参与者 | 所有状态相关响应与状态机一致 |
| [x] | R1-12 | 补全 Model Gateway | 新增 2.8 章节，3 个内部端点（EP-MODEL-058～060），定义隐私上下文结构、超时规则、降级策略、失败关闭行为和审计元数据 | `privacy_context` 包含 purpose/data_classification/retention/consent_scope/allowed_outputs；超时 30s 可配置；降级策略不绕过隐私；审计仅记录 call_id、model、tokens、latency、status、hash |
| [x] | R1-13 | 补全 Admin API | 确认 Admin API 属于 MVP（P7阶段，P1优先级），新增 2.9 章节，11 个端点（EP-ADMIN-061～071），明确 Node/Model/Deployment CRUD 和健康检查契约，定义管理员隐私边界（只能访问结构化元数据，不能访问 P2/P3/P4 数据正文） | Admin API 属于 MVP 有明确结论；所有 11 个端点都有完整定义；隐私边界清楚（❌ 不能读取私有偏好、记忆正文、智能体推理、聊天明文、私有提交）；健康检查 API 可见信息边界明确（仅状态、检查项、时间戳）；MVP_SCOPE.md 与 API_CONTRACT.md 一致 |
| [x] | R1-14 | 统一路径变量 | 统一路径变量命名：`{org_id}` → `{organization_id}`、`{conv_id}` → `{conversation_id}`、`{instance_id}` → `{scene_instance_id}`；统一资源命名：organizations/conversations/memories/scenes/agents 无混用；所有路径使用 `/api/v1/` 前缀 | 路径变量与领域词汇表一致；同一资源只有一套路径命名；无 org/organization、chat/conversation、memo/memory 混用 |
| [x] | R1-15 | 补全错误码 | 统一错误响应结构（code/message/details/request_id/retryable）；9 类错误分类（authentication/authorization/privacy_violation/validation_error/not_found/conflict/state_transition_error/idempotency_conflict/model_gateway_error）；68+ 错误码主表；隐私失败显式化规则；R1-08～R1-13 所有端点关联错误码 | 不依赖自由文本判断错误；隐私和权限失败不混淆；每类关键失败有稳定错误码 |
| [x] | R1-16 | 统一幂等规则、请求响应模型和校验规则 | 统一幂等规则（18 个必支持端点、3 个可选端点、Key 格式/作用域/过期/冲突处理）；统一请求规则（分页/排序/过滤/时间格式/ID 格式/空值/布尔/枚举）；统一响应模型（列表/详情/创建/更新/异步/删除）；统一校验规则（字段校验/错误映射/内容类型）；所有 R1-08～R1-13 端点引用统一规则 | 不再每个模块各写一套请求响应风格；幂等规则覆盖关键写操作；前后端可基于统一模型生成类型或 Mock |
| [x] | R1-17 | 冻结 API 文档状态 | `API_CONTRACT.md` v1.0-frozen（71 个端点，路径变量统一，错误码、幂等规则、请求/响应模型、校验规则均已统一）；`WEBSOCKET_CONTRACT.md` 仍为 DRAFT | 状态从”草稿”改为”已评审/已冻结”必须有评审记录；WEBSOCKET 安全问题待 R1-22 处理 |

API 契约逐端点最低字段：

- 方法和路径；
- 用途；
- 调用主体；
- 权限和资源所有权；
- 请求 Schema；
- 成功响应；
- 错误码；
- 幂等要求；
- 数据分类；
- 审计要求；
- 隐私失败行为。

### R1-C：统一认证和 WebSocket 契约

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R1-18 | 冻结浏览器认证方式 | 依据 ADR-003 统一为 HttpOnly Secure SameSite Cookie + JWT；Web 浏览器端主认证方式为 Cookie，不返回 access_token/refresh_token 到响应体；内部服务 Bearer Token 明确范围（Model Gateway/Admin）；login/refresh/logout/me 端点 Cookie 行为一致 | HTTP 契约与 ADR 一致；前端不存储 Token 到 localStorage/sessionStorage |
| [x] | R1-19 | 定义 CSRF 方案 | Token 来源、Header、轮换和失败响应 | 所有 Cookie 写请求具有明确 CSRF 防护 |
| [x] | R1-20 | 修正登录响应 | 不再同时声称只用 Cookie又返回持久化 Token | 前端无须把 Token 写入浏览器存储 |
| [x] | R1-21 | 修正 Refresh 流程 | Cookie、轮换、重放检测、注销撤销 | ADR 与 API 契约完全一致 |
| [x] | R1-22 | 修正 WebSocket 鉴权 | 禁止长期 Token 出现在 URL 查询参数 | 采用 HttpOnly access_token Cookie，路径 /api/v1/ws，强制 Origin 白名单 |
| [x] | R1-23 | 定义 WebSocket Token 过期 | 关闭码、刷新、重连和重新订阅 | 客户端行为可确定实现 |
| [x] | R1-24 | 冻结事件 Schema | 所有事件字段和版本策略 | 公共事件不包含 P2–P4 数据 |

**R1-23 完成摘要（2026-07-15）**：

- ✅ 浏览器握手失败恢复流程（WEBSOCKET_CONTRACT.md §1.8）：明确浏览器 WebSocket API 不暴露 401/403 详情，应用启动先调 `/me`，握手前 `onerror` 调 `/me` 检查认证状态，禁止无限 refresh 循环
- ✅ 事件信封 `sequence` 字段（§2.1）：单连接/单订阅流内递增，不保证跨连接全局连续，跳号触发 HTTP 回补
- ✅ 连接事件定义（§4.1）：`connection.established`（含 `connection_id`、`server_time`、`access_token_expires_at`）和 `connection.expiring`
- ✅ 网络重连退避（§6.1）：第 1 次立即，后续 1/2/4/8/16/30 秒，最大 30 秒，±20% jitter，连续 10 次进入 PAUSED，offline→online 重置计数并立即重试
- ✅ 自动重连白名单与禁止清单（§6.2）：允许 1001/1011/1012/4408/4429/网络异常；禁止 1000/1008/4403/4406/用户注销/Refresh 失败/Origin 配置错误
- ✅ HTTP 回补完整规则（§6.3）：路径 `GET /api/v1/conversations/{conversation_id}/messages?page=1&page_size=50`，记录最后确认 `message_id`，分页去重，安全页数上限 20 页，会话元数据和场景状态回源，sequence 跳号触发回补，HTTP API 为最终事实来源，不新增 since/cursor/last_event_id 参数
- ✅ 事件去重有界缓存（§6.4）：最多 1000 个 event_id 或 24 小时，先到者触发淘汰，删除无限增长 `set()`，区分传输去重/业务幂等/序列检测三层
- ✅ Refresh 连接迁移 10 步（§7.4.3）：POST refresh 携带 X-CSRF-Token，创建新 WebSocket，等待 connection.established，逐项恢复订阅，等待 subscribed 确认，服务端重新鉴权，全部恢复后切换活动连接，关闭旧连接，清理旧连接计时器/监听器，Refresh 失败进入 AUTH_FAILED
- ✅ 连接状态机 10 状态（§7.5）：DISCONNECTED/CONNECTING/OPEN/REFRESHING/RESTORING/RECONNECTING/AUTH_FAILED/FORBIDDEN/PAUSED/CLOSED，状态转换表覆盖初次连接、握手失败、Token 临期、4401、4403、网络断开、心跳超时、服务重启、Refresh 成功/失败、用户注销；RESTORING 为恢复订阅和 HTTP 回补的必经中间状态
- ✅ 关闭码补全（§7.6）：4401=Token过期/认证上下文失效（两个 reason：access_token_expired / authentication_context_invalid）、4403=权限拒绝/账号禁用、4406=协议主版本不支持、4408=心跳超时、4429=遵守 retry_after_ms（来源为 error 事件，默认 30000ms，范围 1000-300000ms），所有 close reason 为固定机器可读字符串，用户注销不重连
- ✅ 心跳计时器清理规则（§7.7）：断线、Refresh、旧连接替换、页面销毁、终态转换时清理
- ✅ 重新订阅 8 条规则（§7.8）：只保存 conversation_id、收到 connection.established 后重订阅、按顺序发送、等待 subscribed 确认、服务端重新鉴权、无权限项移除、单项失败不关闭连接、全部完成后切换活动连接
- ✅ 删除编辑器备份文件 `docs/api/WEBSOCKET_CONTRACT.md.backup`
- ✅ connection.expiring 字段修正：删除 grace_seconds，统一为 expires_at/refresh_required/reconnect_required（§4.1）
- ✅ connection.expired 事件定义（§4.1）：access_token 过期后发送，发送后立即 4401 关闭，客户端不能依赖收到该事件
- ✅ RESTORING 状态（§7.5）：新连接建立后恢复订阅和 HTTP 回补的中间状态，完成后才进入 OPEN
- ✅ 4401 两个 reason（§7.6）：access_token_expired（自然过期）/ authentication_context_invalid（撤销或失效）
- ✅ 4429 retry_after_ms 来源（§7.6）：error 事件传递，默认 30000ms，范围 1000-300000ms
**R1-24 完成摘要（2026-07-15，R1-24-C 审计整改后）**：

- ✅ WEBSOCKET_CONTRACT.md 版本为 `v1.0-frozen`，状态标记为「已评审/已冻结」
- ✅ 统一事件信封（§2）：客户端命令信封含 `event`/`data`/`version`/`request_id`/`timestamp`，服务端事件信封含 `event`/`data`/`version`/`event_id`/`sequence`/`timestamp`/`request_id`
- ✅ `request_id` 统一为 UUID v4（§2-§4）：客户端命令必填 UUID v4，直接响应回显同一 UUID v4，主动推送为 `null`，无法解析请求的 `error` 为 `null`
- ✅ 时间字段标准化（§2.4）：所有 `timestamp` 使用 UTC RFC 3339 秒精度（如 `2026-07-15T10:30:00Z`），`expires_at` 同格式
- ✅ 全部事件 Schema 冻结（§3–§4）：每个事件含方向、触发条件、JSON 示例、data 字段表、隐私分级、授权要求、客户端处理、request_id 关联
- ✅ message.created 使用授权会话投影（§4.3.1）：字段与 HTTP Message 模型建立明确映射（`message_id`→`Message.id` 等），使用扁平 `sender_type`/`sender_user_id`/`sender_agent_id`，删除嵌套 `sender` 和 `display_name`，`message_type` 使用 `DOMAIN_VOCABULARY.md` 完整 v1 枚举（10 值）
- ✅ scene.updated 使用 `state` 字段名（§4.5.1）：与 `SCENE_STATE_MACHINE.md` 生命周期状态一致，12 个封闭枚举（含 `CANDIDATES_READY`/`FAILED`/`EXPIRED`）
- ✅ scene.result.generated 使用 `state=CANDIDATES_READY`（§4.5.2）：触发时机为 `PROCESSING`→`CANDIDATES_READY`，不等于 `COMPLETED`
- ✅ notification.created `type` 为 WebSocket v1 开放枚举（§4.6.1）：当前已知值 `SCENE_INVITE`，不引用不存在的 HTTP Notification 模型，不无依据声明 `MESSAGE_MENTION`
- ✅ 错误事件冻结（§4.7）：`error.data` 含 `code`/`message`/`details`/`retryable`/`retry_after_ms`，定义 7 个应用层 WS 错误码
- ✅ 错误码同步到 API_CONTRACT.md §1.6：分类表和总表均包含全部 8 个 WS_* 错误码，`WS_RATE_LIMITED` 只属于 websocket 分类不映射 HTTP 429，`rate_limit` 分类明确排除 `WS_RATE_LIMITED`
- ✅ 版本兼容策略冻结（§8）：`version` 字段固定为 `v1`，同版本向后兼容，破坏性变更须升版本号
- ✅ 隐私投影规则冻结（§9）：`visibility=PRIVATE`/`HIDDEN`、Agent 私域消息、P3/P4 数据、记忆正文和智能体内部推理均不得通过 WebSocket 推送；`content` 可以是 P1/P2 的授权会话可见内容但不能是 P3/P4；WebSocket Schema 中不存在 `metadata` 字段
- ✅ 事件清单冻结（§10）：按方向（C→S / S→C）分类列出全部事件，含版本和简述
- ✅ README.md 更新：标记 API 和 WebSocket 合约均为 `v1.0-frozen`

### R1-D：修正威胁模型和隐私测试

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R1-25 | 修正威胁编号 | T-01～T-N 连续编号 | 不再引用不存在的 T-14 |
| [x] | R1-26 | 修正威胁数量 | 完成总结与正文一致 | 威胁数量、严重级别数量可自动核对 |
| [x] | R1-27 | 区分控制状态 | `planned / implemented / verified` | P0 阶段不能把未开发控制写成"已实施" |
| [x] | R1-28 | 补充边缘节点威胁 | 如果保留 T-14，则补完整资产、攻击路径和缓解措施 | 每个残余风险都有正文定义 |
| [x] | R1-29 | 映射威胁到测试 | T-01～T-09 每个威胁至少一个测试 ID；建立威胁—控制—测试双向追踪矩阵 | 威胁—控制—测试可以双向追踪 |
| [ ] | R1-30 | 检查隐私失败关闭 | 授权、加密、隔离失败场景 | 明确拒绝执行，不公开降级 |
| [ ] | R1-31 | 复核保留策略 | 原始提交、胶囊、评价、AgentRun、Audit、Memory | 所有文档 TTL 一致 |

**R1-25 完成摘要（2026-07-15）**（任务完成时快照，当前统计已由 R1-28 更新）：

- ✅ 当前威胁集合为 T-01～T-08（共 8 个），威胁矩阵（§2.1）和详细分析章节（§3）的 ID 集合完全相同
- ✅ 编号连续（T-01→T-08），无跳号
- ✅ 当前有效威胁正文中没有未定义的 T-* 引用；缓解计划（§4）、安全测试表（§5）、残余风险（§6）中引用的所有 T-* 均存在于威胁矩阵中
- ✅ T-14 只出现在任务说明、条件规划（R1-28）或明确标注的历史记录中，不在当前有效威胁正文中
- ✅ 未修改风险等级、可能性、影响和控制状态（planned/implemented/verified 矛盾属于 R1-27）
- ✅ 未修改测试映射（属于 R1-29）、威胁数量统计（属于 R1-26）、边缘节点威胁（属于 R1-28）
- ✅ R1-26～R1-31 均未执行
- ✅ 当前审计日志：`development-logs/completed/remediation-r1/R1-25-fix-threat-numbers.md`

**R1-26 完成摘要（2026-07-15）**（任务完成时快照，当前统计已由 R1-28 更新）：

- ✅ 当前有效威胁总数：8（T-01～T-08）
- ✅ 严重（Critical）：1（T-01）
- ✅ 高（High）：5（T-02、T-03、T-04、T-06、T-08）
- ✅ 中（Medium）：2（T-05、T-07）
- ✅ 低（Low）：0
- ✅ 严重/高合计：6
- ✅ 统计来源：THREAT_MODEL.md 当前威胁矩阵（§2.1）风险等级列
- ✅ THREAT_MODEL.md 新增 §2.2 威胁数量统计（R1-26 权威口径）
- ✅ 未修改控制状态（planned/implemented/verified 矛盾属于 R1-27）
- ✅ 未新增或删除威胁
- ✅ 未修改风险等级、可能性和影响
- ✅ R1-27～R1-31 均未执行
- ✅ 当前审计日志：`development-logs/completed/remediation-r1/R1-26-fix-threat-count.md`

**R1-27 完成摘要（2026-07-15）**（任务完成时快照，当前统计已由 R1-28 更新）：

- ✅ T-01～T-08 全部为 `planned`
- ✅ planned：8
- ✅ implemented：0
- ✅ verified：0
- ✅ 已清除"所有威胁均已缓解"的错误当前结论
- ✅ 计划缓解措施不再使用完成标识（✅）
- ✅ 残余风险改为预计残余风险（计划控制完成并验证后）
- ✅ 未修改风险等级
- ✅ 未修改测试映射（属于 R1-29）
- ✅ 未修改代码
- ✅ 当前日志位于 `development-logs/completed/remediation-r1/R1-27-distinguish-control-status.md`

**R1-28 完成摘要（2026-07-15）**：

- ✅ 新增连续编号 T-09（边缘节点被入侵、冒充或返回恶意结果），未恢复 T-14
- ✅ T-09 风险等级为高，控制状态为 planned
- ✅ 当前威胁总数：9（T-01～T-09）
- ✅ 风险分布：严重 1、高 6、中 2、低 0
- ✅ 严重/高合计：7
- ✅ planned：9，implemented：0，verified：0
- ✅ 补充 EdgeNode 信任边界（DATA_FLOW.md）
- ✅ 修正节点 HTTPS 和 SSRF 契约（API_CONTRACT.md）
- ✅ 未新增 HTTP 端点（MVP 仍为 68，internal 仍为 3，总文档化仍为 71）
- ✅ 未提前执行 R1-29
- ✅ 当前日志位于 `development-logs/completed/remediation-r1/R1-28-supplement-edge-node-threat.md`（已归档）

**R1-29 完成摘要（2026-07-15）**：

- ✅ T-01～T-09 每个威胁均映射正式测试 ID（9/9 威胁有测试）
- ✅ 严重/高风险 7/7 均有拒绝、失败关闭或泄露检测测试
- ✅ 新增 27 个正式测试定义（PI-001～005、RP-001～005、MR-001～005、EN-001～012）
- ✅ 总定义 78（原有 51 + 新增 27）
- ✅ defined=78，not_run=78
- ✅ 未定义引用=0，重复定义=0
- ✅ planned=9，implemented=0，verified=0
- ✅ 删除 THREAT_MODEL.md 中 ST-01～ST-08，不恢复 ST-09
- ✅ 修正 PT-203（ORG_ADMIN 边界）、PT-305（SCHOOL_ADMIN 脱敏指标边界）、LG 表（defined/not_run）
- ✅ 修正 PERMISSION_MATRIX.md Node 权限（SCHOOL_ADMIN 只读，SYSTEM_ADMIN 写操作）
- ✅ 建立权威双向追踪矩阵（正向 + 反向）
- ✅ 当前日志位于 `development-logs/in-progress/R1-29-map-threat-to-test.md`

### R1-E：P0 文档一致性收尾

| 状态 | ID | 整改内容 | 涉及位置 | 完成标准 |
|---|---|---|---|---|
| [ ] | R1-32 | 修复全部内部链接 | P0 文档和开发日志 | 链接检查结果为 0 个失效链接 |
| [ ] | R1-33 | 修正 P0 完成总结 | `P0_COMPLETION_SUMMARY.md` | 不再虚报 62 个契约、14 个威胁或已实施控制 |
| [ ] | R1-34 | 更新 P0 进度表 | `DEVELOPMENT_PLAN.md` | 任务状态、阶段状态、日期和提交哈希一致 |
| [ ] | R1-35 | 进行 P0 人工评审 | 全部 P0 文档 | 记录评审人、日期、决议和未决项 |
| [ ] | R1-36 | 形成 P0 冻结提交 | Git | 一个或多个聚焦提交，CI 文档检查通过 |

建议提交：

```text
docs(domain): reconcile global and organization roles
docs(api): complete and freeze MVP API contract
docs(auth): align HTTP and WebSocket authentication
docs(security): correct threat model and control states
docs(project): close P0 remediation findings
```

R1 退出条件：P0 没有互相冲突的角色、认证、状态和保留规则；68 个端点全部可追踪；API/WebSocket 不再是待评审草稿；威胁模型与测试矩阵一致。

---

## R2：P1 后端与测试整改

### R2-A：Conda 和 Python 依赖基线

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R2-01 | 验证 Conda 环境 | `conda run -n CampusAgent python --version` | 输出 Python 3.11.x，优先 3.11.15 |
| [x] | R2-02 | 统一依赖事实来源 | 在 `pyproject.toml` 与 `requirements*.txt` 中选择主来源 | 不再维护两份容易漂移的运行依赖 |
| [x] | R2-03 | 补全开发依赖 | pytest、pytest-asyncio、httpx、ruff、mypy | 全部在 CampusAgent 环境内可执行 |
| [x] | R2-04 | 建立可复现锁定策略 | lock/constraints 文件 | CI 与本机安装同一依赖版本集合 |
| [x] | R2-05 | 修正 Python 版本文档 | Windows 本地路径和 Linux 示例分开 | 不再把 `/root/miniconda3` 写成当前 Windows 环境路径 |
| [ ] | R2-06 | 验证全新安装 | 删除临时测试环境后重建或使用干净环境演练 | 单条文档命令可完成安装 |

推荐统一命令形式：

```powershell
conda run -n CampusAgent python -m pip install <项目定义的开发依赖入口>
conda run -n CampusAgent python -m pytest apps/api/tests -q
conda run -n CampusAgent ruff check apps/api
conda run -n CampusAgent mypy apps/api/src apps/api/tests
```

### R2-B：修复 API 工程结构

| 状态 | ID | 整改内容 | 涉及位置 | 完成标准 |
|---|---|---|---|---|
| [x] | R2-07 | 修复 `src` 包结构 | `apps/api/src/` | 包导入路径唯一，mypy 不再识别为重复模块 |
| [x] | R2-08 | 修复 middleware 导入 | `src/main.py` | `import src.main` 成功 |
| [x] | R2-09 | 修复 Settings 类型导入 | `src/dependencies.py` | strict mypy 不报未定义类型 |
| [x] | R2-10 | 合并重复配置入口 | `src/config.py` 与 `src/modules/core/config.py` | 只有一个公开 Settings 事实来源 |
| [x] | R2-11 | 明确环境校验时机 | 应用工厂/lifespan | 导入模块不调用 `sys.exit`，错误可测试 |
| [x] | R2-12 | 修复环境变量命名 | APP_ENV、APP_SECRET 等 | `.env.example`、Settings、测试、CI 完全一致 |
| [x] | R2-13 | 修复健康检查 | live 与 ready | live 只检查进程，ready 不得在依赖未就绪时返回 ready |
| [x] | R2-14 | 补全应用工厂测试 | `create_app()` | 可创建多个隔离测试实例 |

### R2-C：修复模块骨架

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R2-15 | 冻结模块模板 | api/schema/model/repository/service/permissions/events/exceptions/tests | 与架构规范一致 |
| [x] | R2-16 | 补齐缺失文件 | 所有业务模块 | 不再缺少 permissions、events、exceptions |
| [x] | R2-17 | 处理零字节文件 | 增加模块说明或有意义的最小接口 | 不以大量零字节文件冒充完成产物 |
| [x] | R2-18 | 移除错误的 core 业务模块模板 | `modules/core` | core 只保留公共内核职责 |
| [ ] | R2-19 | 增加边界说明 | 每个模块 README 或公开 `__init__` | 明确公开接口和禁止依赖 |
| [x] | R2-20 | 增加边界自动检查 | 脚本或测试 | 能发现跨模块 ORM 导入 |

### R2-D：修复后端测试

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R2-21 | 修复重复测试模块名 | 改名或增加正确包结构 | pytest 收集无 import mismatch |
| [x] | R2-22 | 配置 pytest-asyncio | pyproject/pytest 配置 | 不出现 UnknownMark 或 async skipped |
| [x] | R2-23 | 修正测试环境变量 | `conftest.py` | 测试走真实 Settings 字段 |
| [x] | R2-24 | 修正 AsyncClient fixture | 生命周期和异步 fixture | 健康检查测试真正执行而不是跳过 |
| [x] | R2-25 | 删除无意义单测 | `assert 1 + 1 == 2` | 改为配置、错误格式或应用工厂测试 |
| [x] | R2-26 | 删除伪 E2E | `assert True` | 改为可观察的健康流程，或明确留到 P11 并不计为通过 |
| [x] | R2-27 | 增加环境校验测试 | 缺失、生产弱密钥、测试默认值 | 不使用 `sys.exit` 终止 pytest 进程 |
| [x] | R2-28 | 后端全量测试 | CampusAgent 环境 | 0 failed、0 collection error、0 unexpected skipped |
| [x] | R2-29 | 后端 lint/typecheck | Ruff、mypy | 均以退出码 0 结束 |

R2 必须通过：

```powershell
conda run -n CampusAgent python -c "import sys; sys.path.insert(0, 'apps/api'); import src.main; print('API_IMPORT_OK')"
conda run -n CampusAgent python -m pytest apps/api/tests -q
conda run -n CampusAgent ruff check apps/api
conda run -n CampusAgent mypy apps/api/src apps/api/tests
```

---

## R3：P1 Workspace、命令、CI 与文档整改

### R3-A：前端 Workspace 和锁文件

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R3-01 | 安装约定版本 pnpm | 使用 Corepack 或明确安装步骤 | `pnpm --version` 与 packageManager 一致 |
| [x] | R3-02 | 生成并提交锁文件 | `pnpm-lock.yaml` | P1 总结声称的锁文件真实存在 |
| [ ] | R3-03 | 验证 frozen install | `pnpm install --frozen-lockfile` | 全新检出可重复安装 |
| [x] | R3-04 | 检查 Workspace 包 | apps/packages | 每个参与递归命令的包都有相应 script |
| [x] | R3-05 | 执行前端 lint | web | 退出码 0 |
| [x] | R3-06 | 执行前端 typecheck | web | 退出码 0 |
| [x] | R3-07 | 执行前端单测 | Jest | 测试真实执行并通过 |
| [x] | R3-08 | 执行前端构建 | Next.js | production build 通过 |
| [x] | R3-09 | 执行 Playwright 基线 | Chromium | 不是空测试，能验证首页和健康页 |

### R3-B：统一跨平台命令

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R3-10 | 选择统一命令入口 | package scripts、Taskfile、跨平台脚本或 Make | Windows PowerShell 和 CI Linux 均可运行 |
| [ ] | R3-11 | 修复 install | 同时安装 Node 和 CampusAgent Python 依赖 | 不再只安装前端 |
| [x] | R3-12 | 修复 dev | 可控地启动/停止 Web 和 API | 不使用无法管理的后台 `&` 进程 |
| [x] | R3-13 | 修复 test | 同时执行前后端真实测试 | 任一侧失败整体退出非零 |
| [x] | R3-14 | 修复 lint/typecheck/build | 同时覆盖前后端 | 命令与 CI 使用相同入口 |
| [x] | R3-15 | 增加 seed 占位策略 | P1-08 要求的 seed 命令 | 若 P11 前不实现，应明确安全 no-op 或调整计划并记录 |
| [ ] | R3-16 | 延后 P2 命令 | Docker/Alembic 尚未存在 | 不在 P1 README 中声称当前可用 |

### R3-C：修复 CI

| 状态 | ID | 整改内容 | 具体操作 | 完成标准 |
|---|---|---|---|---|
| [x] | R3-17 | 使用锁文件安装前端 | CI `--frozen-lockfile` | 不允许 CI 自动漂移依赖 |
| [x] | R3-18 | 安装后端依赖 | Python 3.11 + dev dependencies | Ruff、mypy、pytest 命令存在 |
| [x] | R3-19 | 统一 CI 环境变量 | APP_ENV、APP_SECRET 等 | 与 Settings 和测试一致 |
| [x] | R3-20 | 修复后端检查 | lint/typecheck/test | 三项真实执行并阻断失败 |
| [x] | R3-21 | 修复前端检查 | lint/typecheck/test/build | 四项真实执行并阻断失败 |
| [x] | R3-22 | 修复 E2E 服务 | 启动 E2E 实际依赖的服务 | 不只启动 Web 却声称全系统 E2E |
| [x] | R3-23 | 强制 Secret Scan | 移除无理由的 continue-on-error | 检测到密钥时 CI 失败 |
| [x] | R3-24 | 检查 CI YAML 和 Actions | workflow | 语法正确、权限最小、版本明确 |
| [ ] | R3-25 | 推送并观察 CI | GitHub | 所有 required jobs 为绿色 |

### R3-D：文档和法律一致性

| 状态 | ID | 整改内容 | 涉及位置 | 完成标准 |
|---|---|---|---|---|
| [x] | R3-26 | 修正 README 状态 | README | 准确描述 P0/P1 已完成内容和未完成能力 |
| [x] | R3-27 | 修正启动指南 | QUICK_START | 每条命令在目标 Windows 环境验证 |
| [ ] | R3-28 | 修复内部链接 | QUICK_START、TOOLING、开发日志 | 失效链接数量为 0 |
| [x] | R3-29 | 修正工具版本记录 | TOOLING 和 P1-01 日志 | 不把其他容器版本写成本机版本 |
| [x] | R3-30 | 统一许可证 | README、pyproject、LICENSE | 未选择许可证则删除 MIT 声明；选择后增加正式 LICENSE |
| [x] | R3-31 | 修正 P1 完成总结 | P1 summary | 锁文件、测试、CI 和工具状态均有真实证据 |
| [ ] | R3-32 | 更新开发计划进度 | DEVELOPMENT_PLAN | P0/P1 状态、日期、提交/PR 一致 |

R3 必须通过：

```powershell
pnpm install --frozen-lockfile
pnpm --filter @campus-agent/web lint
pnpm --filter @campus-agent/web typecheck
pnpm --filter @campus-agent/web test -- --runInBand
pnpm --filter @campus-agent/web build
pnpm --filter @campus-agent/web test:e2e
```

---

## R4：最终阶段门禁

### R4-A：P0 最终验收

| 状态 | ID | 验收项 | 证据 |
|---|---|---|---|
| [ ] | R4-01 | MVP/非 MVP 无歧义 | MVP Scope 评审记录 |
| [ ] | R4-02 | 角色模型唯一且有 ADR | 角色 ADR + 全仓搜索结果 |
| [ ] | R4-03 | 68 个 MVP 端点均有完整契约 | 端点对照表 |
| [ ] | R4-04 | HTTP、Cookie、CSRF、WebSocket 认证一致 | ADR + API/WS 契约 |
| [ ] | R4-05 | 状态机无未定义转换 | 状态转换矩阵评审 |
| [ ] | R4-06 | 数据分类和保留期限一致 | 数据清单对照结果 |
| [ ] | R4-07 | 威胁—控制—测试完整映射 | 可追踪矩阵 |
| [ ] | R4-08 | P0 文档链接无失效 | 链接检查日志 |
| [ ] | R4-09 | P0 所有未决项已处理 | 未决清单为空或有明确延期决议 |
| [ ] | R4-10 | P0 评审通过 | 评审人、日期、提交哈希 |

### R4-B：P1 最终验收

| 状态 | ID | 验收项 | 证据 |
|---|---|---|---|
| [ ] | R4-11 | CampusAgent Conda 环境可重建 | Python/依赖版本输出 |
| [x] | R4-12 | pnpm 锁文件存在且 frozen install 通过 | 安装日志 |
| [x] | R4-13 | API 可导入和启动 | import + health 响应 |
| [x] | R4-14 | 后端 pytest 真实执行 | 0 failed、0 error、0 unexpected skipped |
| [x] | R4-15 | Ruff 和 mypy 通过 | 命令日志 |
| [x] | R4-16 | 前端 lint/typecheck/test/build 通过 | 命令日志 |
| [x] | R4-17 | Playwright 基线通过 | 报告 |
| [x] | R4-18 | 统一命令在 Windows 可运行 | PowerShell 验证记录 |
| [ ] | R4-19 | CI 全部 required jobs 通过 | GitHub Actions 链接 |
| [x] | R4-20 | Secret Scan 为强制门禁 | CI 配置和运行结果 |
| [ ] | R4-21 | 快速开始从干净环境验证 | 操作记录 |
| [ ] | R4-22 | 所有 P0/P1 文件已提交 | `git status` 干净 |
| [ ] | R4-23 | P1 评审通过 | 评审人、日期、提交哈希 |

## 3. 最终一键验收命令清单

以下命令必须在项目根目录执行并保存输出：

```powershell
# 环境
conda run -n CampusAgent python --version
conda run -n CampusAgent python -m pip check

# 后端
conda run -n CampusAgent python -c "import sys; sys.path.insert(0, 'apps/api'); import src.main; print('API_IMPORT_OK')"
conda run -n CampusAgent ruff check apps/api
conda run -n CampusAgent mypy apps/api/src apps/api/tests
conda run -n CampusAgent python -m pytest apps/api/tests -q

# 前端
pnpm install --frozen-lockfile
pnpm --filter @campus-agent/web lint
pnpm --filter @campus-agent/web typecheck
pnpm --filter @campus-agent/web test -- --runInBand
pnpm --filter @campus-agent/web build
pnpm --filter @campus-agent/web test:e2e

# 仓库
git diff --check
git status --short
```

预期结果：所有命令退出码为 0；pytest 没有收集错误和意外跳过；Git 工作树干净；远端 CI 全绿。

## 4. 建议提交顺序

```text
chore(project): checkpoint initial P0 and P1 deliverables
docs(domain): reconcile role model and vocabulary
docs(api): complete MVP HTTP contract
docs(auth): align HTTP and websocket authentication
docs(security): correct threat and privacy traceability
fix(api): repair package imports and settings validation
test(api): establish executable async test baseline
chore(api): make dependencies reproducible
chore(web): add lockfile and verify quality scripts
ci: install and verify frontend and backend dependencies
docs(project): close P0 and P1 audit findings
```

每个提交后运行对应的最小测试；R4 前再执行全量验收。

## 5. 整改完成记录

| 批次 | 状态 | 开始时间 | 完成时间 | 提交/PR | 审核结果 |
|---|---|---|---|---|---|
| R0 | 未开始 |  |  |  |  |
| R1 | 未开始 |  |  |  |  |
| R2 | 未开始 |  |  |  |  |
| R3 | 未开始 |  |  |  |  |
| R4 | 未开始 |  |  |  |  |

P0、P1 只有在 R4-A 和 R4-B 全部通过后，才可以重新标记为完成并进入 P2。
