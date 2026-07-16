---
task_id: R1-30
status: completed
stage: R1
title: 检查隐私失败关闭
started_at: 2026-07-15T10:00:00+09:00
completed_at: 2026-07-16T10:00:00+08:00
estimated_hours: 1
actual_hours: 2
---

# R1-30：检查隐私失败关闭

## 完成状态

✅ **隐私失败关闭策略已系统性补全**

**完成时间**：2026-07-15T12:00:00+09:00

## 目标

系统性检查并补全文档中的"隐私失败关闭（Fail-Closed）"规则，确保在授权、解密、隔离、模型路由等关键依赖失败时，系统明确拒绝执行、不公开降级、不泄露敏感数据，并记录最小化审计日志。

**来自整改计划**：R1-30 - 检查隐私失败关闭
- **验收标准**：授权、加密、隔离失败场景 → 明确拒绝执行，不公开降级

**边界约束**：
- 不提交、不推送
- 不执行 R1-31
- 不修改业务代码

## 完成内容

### 1. 失败关闭场景矩阵（THREAT_MODEL.md §4.3）

重构 `docs/security/THREAT_MODEL.md` §4.3 为 R1-30 权威口径，建立 FC-001～FC-012 共 12 类失败关闭场景矩阵：

| FC ID | 场景 | 核心策略 |
|-------|------|---------|
| FC-001 | 授权失败关闭 | 拒绝执行，返回 `*_PERMISSION_DENIED` 或 `AUTH_*`；不返回 P2/P3/P4 正文 |
| FC-002 | 授权撤销失败关闭 | 拒绝继续处理；不使用缓存授权；不调用模型 |
| FC-003 | 数据解密失败关闭 | 停止处理；不返回密文；不返回部分明文 |
| FC-004 | 租户/组织/场景隔离失败关闭 | 拒绝跨边界访问；不跨租户查询 |
| FC-005 | privacy_context 缺失失败关闭 | 拒绝；不调用模型/节点/外部 Provider；只允许补更严格默认值 |
| FC-006 | 模型路由失败关闭 | P3/P4 数据必须失败关闭；不公开降级到外部模型；仅允许降级到同等隐私约束的 Mock/规则引擎 |
| FC-007 | Prompt/输出 Schema 校验失败关闭 | 拒绝或安全重建；不直接返回原始模型输出；不写入长期记忆 |
| FC-008 | WebSocket 认证/订阅失败关闭 | 握手失败返回明确错误码；不推送历史事件；不回补未授权消息 |
| FC-009 | 幂等/重放检测失败关闭 | 冲突必须拒绝；不产生二次副作用 |
| FC-010 | 边缘节点认证/网络/返回结果失败关闭 | 管理端拒绝非法 endpoint；节点认证失败不派发任务 |
| FC-011 | 审计日志写入失败关闭 | 高风险写操作失败关闭；只读拒绝类事件返回拒绝+告警 |
| FC-012 | 清理/保留策略执行失败关闭 | 不继续公开场景结果；不把清理失败当作成功；标记待重试 |

**同时更新 §5.1 威胁覆盖表**，将 FC-001～FC-012 映射到对应威胁 T-01～T-09。

### 2. 隐私测试矩阵（PRIVACY_TEST_MATRIX.md §12）

在 `docs/privacy/PRIVACY_TEST_MATRIX.md` 新增 §12，定义 12 个 FC 测试：

- FC-001～FC-012，每个测试包含：测试场景、预期行为、关联 FC 场景、隐私等级、定义状态（defined）、执行状态（not_run）
- 测试定义总数从 **78 增加到 90**（新增 12 个 FC 测试）
- 追踪矩阵从 §12 重新编号为 §13，执行要求从 §13 编号为 §14，相关文档从 §14 编号为 §15
- 双向追踪矩阵更新：T-01～T-09 的测试覆盖列均加入对应的 FC 测试 ID

### 3. HTTP API 契约（API_CONTRACT.md §1.6.4）

在 `docs/api/API_CONTRACT.md` §1.6.4 新增 point 5，明确 6 条失败关闭规则：

1. privacy_context 缺失或非法时失败关闭
2. 模型路由失败时 P3/P4 数据必须失败关闭
3. 解密失败时停止处理，不返回密文或明文
4. 租户/场景隔离失败时拒绝跨边界访问
5. 幂等冲突时拒绝，不产生重复副作用
6. 高风险写操作审计写入失败时失败关闭

**修正错误码拼写**：`MISSING_PRIVACY_CONTEXT` → `PRIVACY_CONTEXT_MISSING`（与错误码总表一致）

### 4. WebSocket 契约（WEBSOCKET_CONTRACT.md §9.3）

在 `docs/api/WEBSOCKET_CONTRACT.md` 新增 §9.3，明确 11 条 WebSocket 失败关闭规则：

- 握手失败不建连、返回明确 HTTP 状态码和错误码
- 订阅失败返回 error 事件，不推送历史事件
- 重连后不沿用旧订阅权限
- 回补期间发现权限已撤销时停止回补
- WebSocket 不承载业务写操作
- Origin 不匹配时拒绝连接
- access_token 过期时使用 4401 关闭码
- 权限拒绝时使用 4403 关闭码
- 与 THREAT_MODEL.md §4.3 FC-008 对齐

### 5. 数据流图（DATA_FLOW.md §9）

在 `docs/architecture/DATA_FLOW.md` 新增 §9，标注 8 个关键失败关闭点：

| 失败关闭点 | 数据流位置 | 对应 FC |
|-----------|-----------|---------|
| API → DB 解密失败 | API → Database | FC-003 |
| API → Model Gateway privacy_context 失败 | API → Model Gateway | FC-005 |
| Gateway → Edge Node 网络/认证失败 | Model Gateway → Edge Node | FC-010 |
| Gateway → External Provider 隐私拦截 | Model Gateway → External Provider | FC-006 |
| API/Gateway → Audit Log 写入失败 | API/Gateway → Audit Service | FC-011 |
| WebSocket → Client 认证/订阅失败 | WebSocket → Client | FC-008 |
| API → Tenant 隔离检查失败 | API → Repository | FC-004 |
| Scene 结束 → 清理任务失败 | Scene Service → Cleanup | FC-012 |

### 6. 数据清单（DATA_INVENTORY.md §12）

在 `docs/architecture/DATA_INVENTORY.md` 新增 §12，明确 P2/P3/P4 字段在 4 个维度的具体要求：

- **§12.1 失败时必须失败关闭的字段**：P2/P3/P4 所有关键字段
- **§12.2 不得日志记录的字段**：P3/P4 正文、P2 Memory 正文等
- **§12.3 不得外发的字段**：P2/P3/P4 所有字段
- **§12.4 清理失败阻止后续读取**：临时私有数据、私有胶囊、导出文件等

### 7. 项目进度文档同步

- `docs/project/P0_P1_REMEDIATION_PLAN.md`：R1-30 勾选为 `[x]`，添加完成摘要
- `docs/project/P0_REVIEW_RECORD.md`：测试定义总数更新为 90
- `docs/project/P0_COMPLETION_SUMMARY.md`：测试定义总数更新为 90，新增 FC 测试分类

## 修改的文件

### 修改文件（9 个）

| 文件 | 修改内容 |
|------|---------|
| `docs/security/THREAT_MODEL.md` | 重构 §4.3 为 12 场景矩阵；更新 §5.1 威胁覆盖表加入 FC 测试 |
| `docs/privacy/PRIVACY_TEST_MATRIX.md` | 新增 §12 定义 12 个 FC 测试；更新统计为 90；追踪矩阵重编号为 §13 |
| `docs/api/API_CONTRACT.md` | §1.6.4 新增 point 5（6 条规则）；修正 `PRIVACY_CONTEXT_MISSING` 拼写 |
| `docs/api/WEBSOCKET_CONTRACT.md` | 新增 §9.3（11 条 WebSocket 失败关闭规则） |
| `docs/architecture/DATA_FLOW.md` | 新增 §9（8 个关键失败关闭点） |
| `docs/architecture/DATA_INVENTORY.md` | 新增 §12（P2/P3/P4 失败关闭要求，4 个子节） |
| `docs/project/P0_P1_REMEDIATION_PLAN.md` | R1-30 勾选 `[x]`；添加完成摘要 |
| `docs/project/P0_REVIEW_RECORD.md` | 测试定义总数更新为 90 |
| `docs/project/P0_COMPLETION_SUMMARY.md` | 测试定义总数更新为 90 |

### 新增文件

- `development-logs/completed/remediation-r1/R1-30-check-privacy-fail-closed.md` - 本任务日志

### 删除文件

- （无）

## 验证结果

- [x] 12 类失败场景已定义（FC-001～FC-012）
- [x] 每个场景明确"拒绝执行、不公开降级"策略
- [x] 每个场景明确审计日志最小化要求
- [x] 每个场景映射到对应威胁 T-01～T-09
- [x] 12 个测试定义已加入隐私测试矩阵
- [x] 测试定义总数更新为 90（defined=90, not_run=90）
- [x] API 契约新增失败关闭规则
- [x] WebSocket 契约新增失败关闭规则
- [x] 数据流图标注关键失败关闭点
- [x] 数据清单明确 P2/P3/P4 失败关闭要求
- [x] 项目进度文档同步更新
- [x] 未修改业务代码
- [x] 未修改端点数量（MVP HTTP 68、internal 3、总文档化 71）
- [x] 未提交、未推送

## 问题与解决

| 问题 | 解决方案 | 耗时 |
|------|---------|------|
| `API_CONTRACT.md` 文件过大无法一次性读取 | 使用 `grep` 定位关键章节，配合 `read_file` 的 `offset`/`limit` 分段读取 | 10min |
| 错误码 `MISSING_PRIVACY_CONTEXT` 与总表不一致 | 统一修正为 `PRIVACY_CONTEXT_MISSING` | 5min |
| 旧版 R1-30 完成记录仅覆盖 4 个场景 | 保留旧版为历史记录，新建 in-progress 日志覆盖完整 12 场景 | 5min |

## 下一步

- **R1-31**：复核保留策略（原始提交、胶囊、评价、AgentRun、Audit、Memory）— 确保 TTL 一致
- **注意**：FC-012 中 TTL 数值细节留给 R1-31 确认

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
- 未提交、未推送，等待审计

## Codex 审计整改补充说明（2026-07-16）

- R1-30 原 FC-012 的 TTL 细节已由 R1-31 补齐（RT-001～RT-010 保留策略测试定义）
- 当前权威保留策略见 `DATA_INVENTORY.md §13` 数据保留策略矩阵（R1-31 权威口径）
- THREAT_MODEL.md 中引用 PRIVACY_TEST_MATRIX.md 追踪矩阵的章节已从 §13 修正为 §14（R1-31 章节重编号后的残留修正）
