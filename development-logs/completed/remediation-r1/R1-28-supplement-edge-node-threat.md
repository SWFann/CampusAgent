---
task_id: R1-28
status: completed
stage: R1
title: 补充边缘节点威胁
started_at: 2026-07-15
completed_at: 2026-07-15
estimated_hours: 2
actual_hours: 2.5
---

# R1-28：补充边缘节点威胁

## 任务目标

新增连续编号 T-09（边缘节点被入侵、冒充或返回恶意结果），更新威胁统计，补充边缘节点信任边界和 API 安全修订。

## 为什么旧版"不增加威胁"的结论失效

旧版 R1-28 日志认为边缘节点不属于 MVP，因此不增加威胁。该结论已失效，原因：

1. EdgeNode 已经是领域模型；
2. 节点密钥已列入核心资产（§1.1）；
3. Admin API 已包含 Node CRUD 和健康检查（EP-ADMIN-061～066）；
4. 模型网关路由明确优先使用本地边缘节点；
5. P7 明确包含模型网关和边缘节点实现；
6. "真实边缘硬件可以用 Mock 替代"只表示演示部署可选，不表示相关安全能力不属于 MVP。

## 为什么 T-08 不能完全覆盖

T-08（外发敏感数据）覆盖的是敏感数据被发送到外部模型 API 的风险，但不能覆盖：

- 恶意本地节点（合法注册但被入侵或恶意控制）；
- 节点身份冒充（凭据泄露后伪造合法节点）；
- 结果篡改（节点返回被操纵的结果）；
- 节点凭据泄露；
- 管理端 SSRF（节点 endpoint 被用于访问内部网络）。

## 为什么编号是 T-09 而不是 T-14

当前有效威胁编号为 T-01～T-08，新增威胁必须保持连续编号，因此只能使用 T-09。T-14 是旧版无定义引用，只能保留在带历史警告的日志中，禁止恢复。

## T-09 完整定义

- **名称**：边缘节点被入侵、冒充或返回恶意结果
- **受影响资产**：节点凭据、模型输入、模型输出、校园内网
- **威胁主体**：外部攻击者、被入侵的边缘节点、恶意或失陷的 SYSTEM_ADMIN、校园内网攻击者、节点供应链或镜像污染
- **攻击路径**：凭据泄露与身份冒充、管理端 SSRF、传输链路劫持、节点被入侵、结果完整性攻击、可用性和错误降级攻击
- **当前风险**：高
- **控制状态**：`planned`（计划在 P7 实现，P12 完成安全验证）
- **预计残余风险（计划控制完成并验证后）**：中

## 计划控制

1. 节点管理权限（只有 SYSTEM_ADMIN 可管理节点）
2. 节点身份认证（独立凭据、可轮换撤销）
3. 凭据保护（应用层加密、密钥密文分离）
4. 安全传输（生产 HTTPS、计划 mTLS）
5. SSRF 防护（地址 allowlist、禁止 loopback/link-local/metadata）
6. 网络隔离（节点不直接访问数据库/Redis）
7. 数据最小化（只接收最小化输入）
8. 输出验证（严格 Schema 验证、失败关闭）
9. 健康和异常处理（隔离、熔断、人工停用）
10. 供应链与运行环境（固定镜像、最小权限、限制出站）

## 数据流信任边界

在 DATA_FLOW.md 中新增"模型网关 → 边缘节点"信任边界，明确边缘节点是独立信任边界，校园内网不等于可信网络。

## API 安全修订

- 将生产节点示例从 HTTP 改为 HTTPS；
- 增加 endpoint 校验规则（SSRF 防护、DNS 校验、重定向禁止）；
- PATCH 端点不新增 endpoint 校验规则（PATCH 请求体无 endpoint 字段）；
- 模型网关路由规则明确连接失败不得降级为 HTTP；
- 不新增端点，MVP HTTP 仍为 68，internal 仍为 3，总文档化仍为 71；
- API_CONTRACT 继续保持 v1.0-frozen。

## 更新后的统计

- 威胁总数：9
- 严重：1（T-01）
- 高：6（T-02、T-03、T-04、T-06、T-08、T-09）
- 中：2（T-05、T-07）
- 低：0
- 严重/高合计：7
- planned：9
- implemented：0
- verified：0

## 测试边界

本任务只定义测试需求，不分配正式测试 ID。正式测试 ID 和威胁—控制—测试映射由 R1-29 完成。

## 未执行的任务范围

- R1-29（威胁—测试映射）：未执行
- R1-30（fail-closed 策略）：未执行
- R1-31（数据保留期限）：未执行

## 修改文件

1. `docs/security/THREAT_MODEL.md` — 新增 T-09 矩阵行、详细分析、§4 控制计划、§6 风险接受标准；更新统计
2. `docs/architecture/DATA_FLOW.md` — 新增边缘节点信任边界；修正部署拓扑表述
3. `docs/api/API_CONTRACT.md` — HTTPS 示例替换；SSRF 校验规则；模型网关降级规则
4. `docs/project/P0_COMPLETION_SUMMARY.md` — 更新威胁统计为 9
5. `docs/project/P0_REVIEW_RECORD.md` — 更新威胁统计为 9
6. `docs/project/P0_P1_REMEDIATION_PLAN.md` — R1-28 标记 [x]；完成摘要；R1-25～R1-27 标注快照说明
7. `development-logs/in-progress/R1-28-supplement-edge-node-threat.md` — 本文件
8. `development-logs/completed/remediation-r1/R1-28-supplement-edge-node-threat-2026-07-14-historical.md` — 旧日志重命名+历史警告
9. `development-logs/completed/remediation-r1/R1-25-fix-threat-numbers.md` — 后续状态更新
10. `development-logs/completed/remediation-r1/R1-26-fix-threat-count.md` — 后续状态更新
11. `development-logs/completed/remediation-r1/R1-27-distinguish-control-status.md` — 后续状态更新

## Git 状态

- 未提交
- 未推送
- 等待 Codex 审计

## 自检记录

| 检查项 | 结果 |
|---|---|
| Matrix IDs | T-01～T-09 |
| Detail IDs | T-01～T-09 |
| 集合差异 | 0 |
| 未定义威胁引用 | 0 |
| 当前权威文档 T-14 | 0 |
| 严重 | 1 |
| 高 | 6 |
| 中 | 2 |
| 低 | 0 |
| 总计 | 9 |
| planned | 9 |
| implemented | 0 |
| verified | 0 |
| ST-09 | 0（已删除，正式测试 ID 由 R1-29 分配） |
| http://192.168.1.100 | 0 |
| http://edge-node | 0 |
| API 端点统计 | 68 MVP + 3 internal = 71 |
| R1-29～R1-31 | 均为 [ ] |
| git diff HEAD --check | 通过 |
| 代码和测试文件修改 | 无 |

## Codex 审计整改（2026-07-15）

Codex 审计发现以下问题，已做最小范围整改：

### 整改一：恢复 R1-26 和 R1-27 权威日志

- **问题**：R1-26 和 R1-27 的 canonical 日志被错误替换为 2026-07-14 的旧版内容。
- **处理**：从 HEAD（aedd8c2）完整恢复权威内容，只在末尾追加 R1-28 后续状态更新。
- **结果**：R1-26 恢复 started_at/completed_at: 2026-07-15、actual_hours: 0.5、严重 1/高 5 统计；R1-27 恢复 estimated_hours/actual_hours: 1.5、planned/implemented/verified 权威定义和 Codex 审计整改记录。

### 整改二：删除提前创建的正式测试 ID

- **问题**：§5.1 新增了 ST-09 测试 ID，但 R1-29 尚未执行。
- **处理**：删除 §5.1 中的 ST-09 行；变更记录改为“定义 T-09 测试需求，正式测试 ID 和映射由 R1-29 完成”。
- **结果**：THREAT_MODEL.md 中 ST-09 为 0 匹配。

### 整改三：修复 PATCH Node 契约

- **问题**：PATCH /api/v1/admin/nodes/{node_id} 错误新增了 endpoint 安全校验规则，但 PATCH 请求体没有 endpoint 字段。
- **处理**：恢复原始错误码（ADMIN_PERMISSION_DENIED、NODE_NOT_FOUND、PRECONDITION_FAILED）；删除 endpoint 安全校验规则。
- **结果**：POST 端点的 HTTPS/SSRF 校验规则保留；PATCH 端点不声称执行 endpoint 校验。

### 整改四：修正数据流方向

- **问题**：§7.2 图示容易被理解为 EdgeNode 单向调用 CampusAgent API。
- **处理**：改为双向调用图示，明确 Model Gateway 发起请求、EdgeNode 返回结果、双向流量均受安全约束。
- **结果**：明确 EdgeNode 不直接访问业务 API、数据库或 Redis。

### 整改范围

- R1-29～R1-31 仍未执行；
- 当前日志仍在 in-progress；
- 未提交、未推送；
- 等待 Codex 复审。

## Codex 复审通过记录（2026-07-15）

Codex 审计已通过 R1-28，确认以下事项：

- T-09 定义完整（资产、攻击路径、缓解措施、检测机制、残余风险）；
- 风险统计正确：严重 1、高 6、中 2、低 0，总计 9；
- 控制状态正确：planned=9，implemented=0，verified=0；
- ST-09 未提前创建（正式测试 ID 由 R1-29 分配）；
- PATCH Node 契约已恢复（不新增 endpoint 校验规则）；
- 数据流方向已修正（双向调用图示）；
- R1-26 和 R1-27 权威日志已恢复；
- 允许进入 R1-29。

R1-28 归档至 `development-logs/completed/remediation-r1/R1-28-supplement-edge-node-threat.md`。
