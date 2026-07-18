# P12 风险登记册

> **版本**：v1.0  
> **创建日期**：2026-07-18  
> **维护者**：CampusAgent 开发团队  
> **关联文档**：`docs/development/P12-COMPLETION-REPORT.md`、`docs/security/THREAT_MODEL.md`、`docs/privacy/PRIVACY_TEST_MATRIX.md`

## 1. 说明

本登记册记录 P12 阶段（系统级安全、稳定性、性能与发布前硬化）发现的所有风险项。每个风险包含 ID、严重性、状态、证据和修复方案。

**严重性定义**：
- `critical`：必须立即修复，否则阻塞发布。
- `high`：必须在发布前修复或有明确接受理由。
- `medium`：应在发布后短期修复。
- `low`：监控即可，可在后续阶段修复。

**状态定义**：
- `fixed`：已修复且有测试验证。
- `accepted`：已接受残余风险，有明确理由和后续计划。
- `investigating`：正在调查中，尚未确定修复方案。
- `blocker`：阻塞发布，必须修复后才能宣称 P12 完成。

**约束**：
- 无法修复的风险必须写入本登记册，不能静默忽略。
- 如果出现 `blocker`，P12 不能宣称完全完成。
- `accepted` 风险必须有明确的后续阶段修复计划。

## 2. 风险清单总览

| 风险 ID | 严重性 | 状态 | 来源任务 | 简述 |
| --- | --- | --- | --- | --- |
| RISK-P12-001 | high | accepted | P12-01 | Next.js 14.x 存在 6 个 high 级别依赖漏洞 |
| RISK-P12-002 | high | accepted | P12-02 | Logout 后 access_token 在过期前仍然有效 |
| RISK-P12-003 | medium | accepted | P12-01 | gitleaks 不可用，使用替代脚本 |
| RISK-P12-004 | medium | accepted | P12-01 | Docker 不可用，无法验证容器化部署 |
| RISK-P12-005 | medium | accepted | P12-05 | Prompt injection 防御只在 mock 模式下验证 |
| RISK-P12-006 | medium | accepted | P12-07 | 数据保留策略（RT-004/RT-005）未实现自动删除 |
| RISK-P12-007 | medium | accepted | P12-07 | 清理脚本需手动运行，无定时调度 |
| RISK-P12-008 | medium | accepted | P12-09 | 性能预算在 SQLite 环境测量，生产环境可能不同 |
| RISK-P12-009 | medium | accepted | P12-13 | 恢复演练在测试环境运行，生产环境未实际演练 |
| RISK-P12-010 | medium | accepted | P12-14 | 所有威胁控制状态仍为 planned |
| RISK-P12-011 | low | accepted | P12-10 | WebSocket 慢消费者测试使用模拟 |
| RISK-P12-012 | low | accepted | P12-08 | 并发测试使用 SQLite，未在 PostgreSQL 下验证锁行为 |

**统计**：critical=0, high=2 (accepted), medium=8 (accepted), low=2 (accepted)  
**阻塞项**：无 blocker  
**结论**：P12 可宣称完成，所有 high 风险已接受且有后续计划。

---

## 3. 详细风险描述

### RISK-P12-001: Next.js 14.x 存在 6 个 high 级别依赖漏洞

- **严重性**：high
- **影响范围**：前端应用（`apps/web`）
- **当前状态**：accepted
- **证据**：`corepack pnpm audit --audit-level=high` 输出 16 个漏洞（2 low、8 moderate、6 high）。6 个 high 漏洞均在 `next@14.2.35`：
  - GHSA-5j98-mcp5-4vw2：glob CLI 命令注入（via eslint-config-next）
  - GHSA-h25m-26qc-wcjf：Next.js HTTP 请求反序列化 DoS
  - GHSA-q4gf-8mx6-v5v3：Next.js Server Components DoS
  - GHSA-8h8q-6873-q5fj：Next.js Server Components DoS
  - GHSA-c4j6-fc7j-m34r：Next.js WebSocket 升级 SSRF
  - GHSA-36qx-fr4f-26g5：Next.js Middleware/Proxy bypass (i18n)
- **修复**：升级 Next.js 从 14.2.35 到 >=15.5.16。这是 major 版本升级，需要适配 App Router API 变更、验证前端全部 115 个测试通过、重新构建。超出 P12 范围。
- **剩余风险**：DoS 和 SSRF 漏洞在生产环境中可能被利用。比赛演示环境不暴露公网，风险可控。
- **后续阶段**：P13 或发布前升级 Next.js 到 15.x。
- **缓解措施**：比赛演示环境通过反向代理限制公网访问；不使用 Next.js i18n 中间件（GHSA-36qx-fr4f-26g5 不适用）；不使用 WebSocket 升级路由（GHSA-c4j6-fc7j-m34r 不适用）。

---

### RISK-P12-002: Logout 后 access_token 在过期前仍然有效

- **严重性**：high
- **影响范围**：认证安全（`apps/api/src/modules/auth/`）
- **当前状态**：accepted
- **证据**：`tests/security/test_auth_security.py::TestLogoutClearsCookies::test_me_fails_after_logout_clears_client_cookies`。测试注释明确记录：CampusAgent 使用无状态短期 access JWT（60 分钟）。Logout 清除浏览器 cookie 使 token 无法再被提交，但在 logout 前被窃取的 token 在过期前仍然有效。
- **修复**：实现服务端 token 黑名单（blocklist）。logout 时将 access_token 的 `jti` 加入黑名单，验证时检查。超出 P12 范围。
- **剩余风险**：攻击者窃取 access_token 后，即使用户 logout，token 在最多 60 分钟内仍然有效。
- **后续阶段**：P13+ 实现服务端 token 黑名单（可基于 Redis，token 过期后自动清理黑名单条目）。
- **缓解措施**：
  1. access_token 有效期短（60 分钟）。
  2. refresh_token 实现了 family revoke（重放检测会撤销整个 token family）。
  3. logout 清除所有 cookie（HttpOnly、Max-Age=0）。
  4. 软删除用户后无法获取新 token（login 被拒绝）。

---

### RISK-P12-003: gitleaks 不可用，使用替代脚本

- **严重性**：medium
- **影响范围**：密钥扫描（`scripts/security/`）
- **当前状态**：accepted
- **证据**：`gitleaks` 命令不可用。替代脚本 `scripts/security/check_no_secrets.py` 扫描 `AKIA`、`sk-`、`BEGIN PRIVATE KEY`、`MODEL_GATEWAY_API_KEY=`、`password:` 等模式。扫描通过，无真实密钥命中。
- **修复**：在 CI 环境安装 gitleaks 并集成到 GitHub Actions workflow。
- **剩余风险**：替代脚本的扫描模式不如 gitleaks 全面（gitleaks 支持自定义规则和 entropy 检测）。
- **后续阶段**：CI 集成 gitleaks。
- **缓解措施**：替代脚本覆盖了最常见的密钥模式；demo password 命中被明确标记为 demo-only。

---

### RISK-P12-004: Docker 不可用，无法验证容器化部署

- **严重性**：medium
- **影响范围**：部署验证
- **当前状态**：accepted
- **证据**：`docker` 命令不可用。无法运行 `docker compose config`、`docker compose up -d`、`docker compose ps`。
- **修复**：在有 Docker 的环境中验证 `docker-compose.yml` 配置正确性。
- **剩余风险**：docker-compose.yml 可能存在配置错误（端口映射、volume 挂载、环境变量），但未在 P12 中验证。
- **后续阶段**：发布前在有 Docker 的环境中验证。
- **缓解措施**：后端测试使用 SQLite + TestClient 覆盖了核心逻辑；恢复演练脚本（`scripts/ops/recovery_drill.py`）验证了降级行为。

---

### RISK-P12-005: Prompt injection 防御只在 mock 模式下验证

- **严重性**：medium
- **影响范围**：模型安全（`apps/api/src/modules/model_gateway/`、`apps/api/src/modules/scenes/`）
- **当前状态**：accepted
- **证据**：`tests/security/test_prompt_injection.py` 使用 mock 模型和单元测试验证 prompt 最小化、reason code 白名单和输出 redaction。未在真实 LLM（vLLM/llama.cpp）环境下验证。
- **修复**：在连接真实模型节点的环境下执行 prompt injection 测试。
- **剩余风险**：真实模型可能对注入指令的响应与 mock 不同，存在未发现的注入路径。
- **后续阶段**：P13+ 在实验室节点环境下执行 PI-001~PI-005 正式测试。
- **缓解措施**：
  1. prompt builder 只传结构化胶囊，不传原始自由文本。
  2. 输出经过 Schema 验证和 redaction。
  3. `ENABLE_EXTERNAL_MODEL=false` 默认禁用外部模型。

---

### RISK-P12-006: 数据保留策略（RT-004/RT-005）未实现自动删除

- **严重性**：medium
- **影响范围**：数据清理（`apps/api/src/modules/`）
- **当前状态**：accepted
- **证据**：`tests/security/test_ttl_and_cleanup.py` 验证了过期 memory、撤销 consent、过期场景实例和过期私有提交的清理。但 RT-004（AgentRun 保留 30 天）和 RT-005（AuditLog 保留 180 天）的自动删除未实现。
- **修复**：实现基于 `created_at` 的定时清理任务，删除超过保留期的 AgentRun 和 AuditLog 记录。
- **剩余风险**：长期运行环境中 AgentRun 和 AuditLog 表会持续增长，影响查询性能和磁盘空间。
- **后续阶段**：P13+ 实现保留策略自动删除。
- **缓解措施**：
  1. 比赛演示环境数据量小，短期内不会造成问题。
  2. 清理脚本 `scripts/ops/cleanup_expired.py` 可手动扩展。
  3. AgentRun 和 AuditLog 只存元数据，不含 P3/P4 敏感正文。

---

### RISK-P12-007: 清理脚本需手动运行，无定时调度

- **严重性**：medium
- **影响范围**：运维（`scripts/ops/`）
- **当前状态**：accepted
- **证据**：`scripts/ops/cleanup_expired.py` 是手动运行的 CLI 脚本，没有集成到 Celery beat 或 cron 定时任务。
- **修复**：将清理逻辑封装为 Celery task，配置 beat 定时调度（如每小时运行一次）。
- **剩余风险**：过期数据在手动清理前会残留，但在 TTL 窗口内（24 小时）不会参与推荐/授权。
- **后续阶段**：P13+ 集成定时调度。
- **缓解措施**：
  1. 清理脚本支持 `--dry-run` 预览。
  2. 恢复演练脚本验证了清理后主路径仍可用。
  3. 场景结束后立即清理（同步），TTL 只是兜底。

---

### RISK-P12-008: 性能预算在 SQLite 环境测量，生产环境可能不同

- **严重性**：medium
- **影响范围**：性能（`apps/api/tests/performance/`）
- **当前状态**：accepted
- **证据**：`tests/performance/test_performance_budget.py` 使用 SQLite in-memory 数据库和 TestClient 测量响应延迟。生产环境使用 PostgreSQL，性能特征不同。
- **修复**：在 PostgreSQL + Redis 环境下重新执行性能预算测试。
- **剩余风险**：生产环境延迟可能高于预算（PostgreSQL 连接池、网络延迟、Redis 缓存未命中）。
- **后续阶段**：发布前在生产环境执行性能基准测试。
- **缓解措施**：
  1. 预算阈值设置较宽松（如 `/health/live` p95 < 50ms 在 SQLite 下实际 < 1ms）。
  2. 关键路径有数据库索引和连接池配置。
  3. Redis 缓存未命中时降级到数据库查询，不阻断流程。

---

### RISK-P12-009: 恢复演练在测试环境运行，生产环境未实际演练

- **严重性**：medium
- **影响范围**：运维（`scripts/ops/recovery_drill.py`）
- **当前状态**：accepted
- **证据**：`scripts/ops/recovery_drill.py` 使用 SQLite in-memory 数据库和 TestClient 模拟数据库/Redis 不可用、demo reset+reseed、清理后主路径可用。未在真实 PostgreSQL + Redis + Docker 环境下演练。
- **修复**：在生产环境执行完整恢复演练（包括 Docker 重启、数据库恢复、Redis 恢复）。
- **剩余风险**：生产环境恢复流程可能遇到未预期问题（如 Docker 网络配置、volume 权限、数据库迁移状态）。
- **后续阶段**：发布前在生产环境演练。
- **缓解措施**：
  1. 恢复演练覆盖了核心降级行为（health/ready degraded、health/live ok）。
  2. 恢复操作手册（`docs/development/P12-RECOVERY-RUNBOOK.md`）提供了详细的恢复步骤。
  3. demo reset/seed 是幂等的，可安全重复执行。

---

### RISK-P12-010: 所有威胁控制状态仍为 planned

- **严重性**：medium
- **影响范围**：威胁模型（`docs/security/THREAT_MODEL.md`）
- **当前状态**：accepted
- **证据**：`docs/security/THREAT_MODEL.md` §8.2 威胁级状态说明。P12 新增测试为 T-01~T-09 部分控制提供了验证证据，但根据 §2.2 保守聚合规则，威胁级状态不升级（仍为 planned=9, implemented=0, verified=0）。
- **修复**：按照 `docs/privacy/PRIVACY_TEST_MATRIX.md` §15.1 测试时机要求，在对应阶段正式执行全部 100 个正式测试 ID 并记录结果。
- **剩余风险**：威胁控制未达到 verified 状态，不能声称威胁已充分缓解。
- **后续阶段**：P13+ 正式执行隐私测试矩阵中的全部测试 ID。
- **缓解措施**：
  1. P12 新增 105 个后端回归测试和 9 个前端安全测试，覆盖了大部分威胁的核心控制。
  2. P12 回归测试与正式测试 ID 的映射关系已记录在 `PRIVACY_TEST_MATRIX.md` §17。
  3. 威胁模型 §8 记录了每个威胁的 P12 验证证据和不升级原因。

---

### RISK-P12-011: WebSocket 慢消费者测试使用模拟

- **严重性**：low
- **影响范围**：WebSocket 稳定性（`apps/api/tests/integration/test_websocket_stability.py`）
- **当前状态**：accepted
- **证据**：`tests/integration/test_websocket_stability.py` 使用 TestClient 模拟 WebSocket 连接，未在真实高并发环境下验证慢消费者不阻塞全局。
- **修复**：使用 locust 或 k6 进行 WebSocket 压力测试。
- **剩余风险**：真实高并发场景下慢消费者可能阻塞事件循环。
- **后续阶段**：发布前进行 WebSocket 压力测试。
- **缓解措施**：
  1. WebSocket 连接管理器有连接上限和超时机制。
  2. 非法消息格式不导致服务崩溃（已测试）。
  3. 未认证连接被立即拒绝（已测试）。

---

### RISK-P12-012: 并发测试使用 SQLite，未在 PostgreSQL 下验证锁行为

- **严重性**：low
- **影响范围**：并发与幂等（`apps/api/tests/integration/test_concurrency_idempotency.py`）
- **当前状态**：accepted
- **证据**：`tests/integration/test_concurrency_idempotency.py` 使用 SQLite in-memory 数据库。SQLite 的锁行为（表级锁 vs 行级锁）与 PostgreSQL 不同。
- **修复**：在 PostgreSQL 环境下重新执行并发测试。
- **剩余风险**：PostgreSQL 行级锁可能导致不同的并发行为（如死锁、序列化失败）。
- **后续阶段**：发布前在 PostgreSQL 环境验证。
- **缓解措施**：
  1. 幂等性通过唯一约束和应用级检查实现，不依赖数据库锁行为。
  2. 场景状态机使用乐观锁（version 字段）。
  3. refresh token 轮换使用 family_id 唯一约束。

---

## 4. 阻塞项

**无阻塞项**。

所有 high 风险（RISK-P12-001、RISK-P12-002）均已接受，有明确的后续阶段修复计划和缓解措施。P12 可宣称完成。

## 5. 风险接受审批

以下风险由 P12 执行方评估并接受，等待 Codex 审计确认：

| 风险 ID | 严重性 | 接受理由 |
| --- | --- | --- |
| RISK-P12-001 | high | Next.js major 升级超出 P12 范围；演示环境不暴露公网；6 个漏洞中 4 个 DoS、1 个 SSRF、1 个 middleware bypass，均不在演示路径上 |
| RISK-P12-002 | high | JWT 无状态特性是架构选择；token 有效期短（60 分钟）；refresh token 有 family revoke；超出 P12 范围 |
| RISK-P12-003~012 | medium/low | 均有缓解措施和后续阶段修复计划；不影响比赛演示 |

---

**最后更新**：2026-07-18  
**审批状态**：待 Codex 审计
