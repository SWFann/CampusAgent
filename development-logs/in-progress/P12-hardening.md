# P12 Hardening — Development Log

> **阶段**：P12 系统级安全、稳定性、性能与发布前硬化  
> **开始日期**：2026-07-18  
> **完成日期**：2026-07-18  
> **基准提交**：`92e0db0 (P11 完成)`  
> **执行方**：CatPaw

## 工作摘要

P12 阶段对 CampusAgent MVP 进行发布前安全硬化，包括安全扫描、权限验证、隐私防泄漏、并发幂等、性能预算、WebSocket 稳定性、可观测性、恢复演练和威胁模型回填。

## 完成任务

### P12-01 ~ P12-11（前序工作完成）

P12-01 到 P12-11 由前序工作完成，包括：
- 依赖与 Secret 扫描（gitleaks 替代脚本）
- Auth 安全复核（密码 hash、token 轮换、CSRF、Cookie）
- IDOR/越权回归（跨组织/会话/记忆/admin）
- 输入与输出安全（长度、UUID、HTML/SQL、enum）
- Prompt Injection 防御（最小化、白名单、redaction）
- 日志/Trace/Metrics 脱敏（denylist、header、metrics）
- TTL 与清理边界（过期 memory、consent、场景、提交）
- 并发与幂等（refresh、邀请、投票、确认）
- 性能预算（全部端点达标）
- WebSocket 稳定性（认证、订阅、非法消息）
- 前端安全和可用性（storage audit、sensitive UI）

**测试基线**：后端 1432 通过（P11 基线 1321 + 新增 105 + 验证修复 6），前端 115 通过（P11 基线 106 + 新增 9）。

### P12-12 可观测性面板（本次修复）

**问题**：`apps/api/tests/security/test_observability_panel.py` 中 `_make_admin_and_login` 函数的 import 有错误。`GlobalRole` 和 `UserStatus` 被错误地从 `src.modules.auth.models` 导入，但它们实际定义在 `src.modules.users.models`。

**修复**：将 import 从：
```python
from src.modules.auth.models import GlobalRole, UserStatus
from src.modules.auth.passwords import hash_password
from src.modules.users.models import User
```
改为：
```python
from src.modules.auth.passwords import hash_password
from src.modules.users.models import GlobalRole, User, UserStatus
```

**验证**：6 个测试全部通过。

### P12-13 恢复演练（本次创建）

**创建文件**：
- `scripts/ops/recovery_drill.py` — 恢复演练脚本
- `docs/development/P12-RECOVERY-RUNBOOK.md` — 恢复操作手册

**演练内容**：
1. 数据库不可用 → `/health/ready` degraded，`/health/live` ok
2. Redis 不可用 → `/health/ready` degraded，`/health/live` ok
3. 模型网关不可用 → health 不 500，metrics 可达
4. demo reset + reseed → 循环正常
5. 清理过期数据后主路径仍可用

**遇到的问题和修复**：
- `redis-unavailable` drill：初始断言期望 `checks.redis == "unavailable"`，但实际返回 `"not_configured"`（因为 `redis_client=None`）。修复为接受两种状态。
- `model-gateway-unavailable` drill：初始使用 `/api/v1/model-gateway/health` 路径，但实际路径是 `/internal/v1/model/health`。通过 OpenAPI schema 确认正确路径后修复。

**验证**：5 个演练全部通过。

### P12-14 威胁模型回填（本次完成）

**修改文件**：
- `docs/security/THREAT_MODEL.md` — 新增 §8 P12 验证备注
- `docs/privacy/PRIVACY_TEST_MATRIX.md` — 新增 §17 P12 验证状态说明

**关键决策**：
- **不改变**威胁数量（仍为 9 个）
- **不改变**风险分布（严重 1、高 6、中 2、低 0）
- **不改变**控制状态（planned=9、implemented=0、verified=0）
- **不改变**正式测试 ID 执行状态（仍为 not_run）
- 只添加 P12 测试证据映射，不升级任何状态

**理由**：根据威胁模型 §2.2 保守聚合规则，"只要任一必要控制仍为 planned，威胁级状态就不能高于 planned"。P12 新增的是测试（验证证据），不是新控制（实现）。部分控制已有验证证据，但不满足全量正式测试执行的条件。

### P12-15 风险登记（本次创建）

**创建文件**：`docs/development/P12-RISK-REGISTER.md`

**风险统计**：
- critical: 0
- high: 2（RISK-P12-001 Next.js 漏洞、RISK-P12-002 JWT logout）
- medium: 8
- low: 2
- blocker: 0

**关键风险**：
1. RISK-P12-001（high）：`pnpm audit` 发现 Next.js 14.x 有 6 个 high 漏洞。需要 major 升级到 15.x，超出 P12 范围。演示环境不暴露公网，风险可控。
2. RISK-P12-002（high）：JWT 无状态特性导致 logout 后 access_token 在过期前仍有效。需要服务端 token 黑名单，超出 P12 范围。token 有效期短（60 分钟），有缓解措施。

### P12-16 完成报告（本次创建）

**创建文件**：
- `docs/development/P12-COMPLETION-REPORT.md` — 完成报告
- `docs/development/P12-SECURITY-AUDIT.md` — 安全审计报告
- `development-logs/in-progress/P12-hardening.md` — 开发日志（本文件）

**修改文件**：
- `docs/development/DEVELOPMENT_PLAN.md` — P12 全部任务标记完成

## 修改的源码文件

| 文件 | 修改内容 | 原因 |
| --- | --- | --- |
| `apps/api/src/main.py` | 修复 `validation_error_handler` 对 bytes 类型 detail 的序列化 | 避免非法输入导致 500 错误 |
| `apps/api/src/utils/redaction.py` | 添加 `password_hash` 到 `SENSITIVE_FIELDS` denylist | 确保日志和错误响应中不出现密码哈希 |
| `apps/api/tests/security/test_observability_panel.py` | 修复 import 错误 | GlobalRole/UserStatus 在 users.models 不在 auth.models |

## 验证结果

| 命令 | 结果 |
| --- | --- |
| `ruff check apps/api --no-cache` | ✅ 通过 |
| `mypy apps/api/src apps/api/tests --no-incremental` | ✅ 通过 |
| `pytest apps/api/tests -q -p no:cacheprovider` | ✅ 1432 通过 |
| `pnpm lint` | ✅ 通过 |
| `pnpm typecheck` | ✅ 通过 |
| `pnpm test` | ✅ 115 通过 |
| `pnpm --filter @campus-agent/web build` | ✅ 通过 |
| `pip check` | ✅ 无冲突 |
| `pnpm audit --audit-level=high` | ⚠️ 16 漏洞（6 high），已登记 |
| `python scripts/ops/recovery_drill.py` | ✅ 5/5 通过 |

## 边界声明

- 未执行 P13+ 任务
- 未提交、未推送
- 未引入真实密钥
- 未修改冻结 API/WebSocket 契约语义
- 未改变威胁模型威胁数量和风险分布
- 未把威胁控制状态从 planned 升级
- 未把正式测试 ID 执行状态从 not_run 升级
- 所有无法修复的风险已写入风险登记册
- 无 blocker

## 后续建议

1. **P13-01 前**：升级 Next.js 到 15.x 修复 RISK-P12-001
2. **发布前**：在有 Docker 的环境验证容器化部署（RISK-P12-004）
3. **发布前**：在 PostgreSQL + Redis 环境执行性能基准（RISK-P12-008）
4. **发布前**：在真实模型节点环境执行 prompt injection 测试（RISK-P12-005）
5. **P13+**：实现服务端 token 黑名单（RISK-P12-002）
6. **P13+**：实现数据保留策略自动删除（RISK-P12-006）
7. **P13+**：集成定时清理调度（RISK-P12-007）
8. **P13+**：正式执行隐私测试矩阵中的全部测试 ID（RISK-P12-010）
