# P13 Release Candidate Checklist

> **版本**：CampusAgent MVP RC1
>
> **基线提交**：`7f90393` (P12 完成)
>
> **创建日期**：2026-07-18
>
> **关联文档**：`docs/development/DEVELOPMENT_PLAN.md`、`docs/development/P13-RELEASE-NOTES.md`、`docs/development/P13-COMPLETION-REPORT.md`

## 1. Included（本次 RC 包含）

以下阶段及其核心产物已实现并通过验证，构成本次 Release Candidate 的能力范围。

| 阶段 | 核心能力 | 测试基线 |
| --- | --- | --- |
| P0 | 冻结契约：API `v1.0-frozen`（71 端点 = 68 MVP + 3 internal）、WebSocket `v1.0-frozen`、威胁模型（9 威胁）、隐私测试矩阵（100 测试 ID） | 契约文件存在且冻结 |
| P1 | Monorepo 工程底座：Web (Next.js) + API (FastAPI)、统一命令、CI 基线、Conda 环境 `CampusAgent` | lint/typecheck/test/build 基线通过 |
| P2 | 基础设施：Compose、配置对象、PostgreSQL/Alembic、Redis、API Envelope、请求上下文、敏感日志过滤、事件总线、Repository/UoW、OpenAPI、可观测性 | P2 全部任务完成 |
| P3 | 身份与用户：注册、登录、刷新、注销、资料读写、账号禁用、Auth 限流、登录注册页面 | 324 API 测试 |
| P4 | 组织与目录：Organization、Membership、RBAC、目录搜索、组织树、领域事件、前端页面 | 454 API 测试 |
| P5 | 会话与实时：私聊/群聊/组织群聊、消息分页、WebSocket 鉴权、PubSub、事件信封、重连回补 | 96 单元 + 20 集成测试 |
| P6 | 智能体与记忆：Agent 模型、自动创建个人 Agent、MemoryItem 加密、Consent、授权服务、审计、AgentRun、TTL 清理 | 150 P6 测试（共 710） |
| P7 | 模型网关：Mock/Rule/OpenAI Provider、隐私路由、结构化校验、Model/Node/Deployment、熔断器、管理 API、指标 | 160 P7 测试（共 841） |
| P8 | 场景核心：ScenePlugin Protocol、注册表、状态机、私有提交加密、执行协调器、投票确认、清理编排 | 130 P8 测试 |
| P9 | 聚餐闭环：输入 Schema、偏好胶囊、10 家餐厅、候选生成、私有评价、确定性聚合、安全理由、场景 API、群聊场景卡、记忆二次确认、场景清理 | 247 P9 测试（共 1247） |
| P10 | 前端闭环：API Client、App Shell、首页工作台、消息页、组织页、智能体页、记忆页、场景中心、私有偏好页、聚餐结果页、管理后台 | 80 前端测试（7 suites） |
| P11 | 演示数据：5 demo 用户、2 组织、幂等 seed、fail-closed reset、CLI/API 入口、demo 账号切换、主路径 smoke（11 步）、隐私/清理/失败 E2E、离线无 Docker 路径 | 77 后端 demo + 26 前端 demo 测试 |
| P12 | 加固：安全扫描、Auth 复核、IDOR 回归、输入输出验证、Prompt 注入防御、日志脱敏、TTL 清理、并发幂等、性能预算、WebSocket 稳定性、可观测性、恢复演练（5 场景）、威胁模型回填、风险登记 | 1432 后端 + 115 前端测试；2 high 风险已接受，无 blocker |
| P13 | 发布候选：一键启动、演示 Runbook、故障备用路径、验收证据、release notes、release 检查脚本 | 本文档及关联产物 |

## 2. Excluded（本次 RC 不包含）

以下能力明确不在本次 RC 范围内，不应在演示中声称已具备。

| 排除项 | 说明 |
| --- | --- |
| 生产部署 | 本 RC 面向比赛演示，不包含生产环境部署、负载均衡、TLS 终止或正式域名配置 |
| 真实模型密钥 | 不接入真实 vLLM/llama.cpp 节点；`MODEL_GATEWAY_API_KEY` 留空，使用 Mock/Rule Provider |
| 真实支付或报名 | MVP 不做支付、报名等高风险不可逆操作（见产品边界） |
| 移动原生应用 | 仅提供 Web 前端，不包含 iOS/Android 原生客户端 |
| 完整多租户企业管理 | 组织树支持学校—学院—班级结构，但不包含企业级多租户隔离和复杂审批流 |
| 长期备份系统 | 不包含自动备份、异地容灾或 PITR（时间点恢复） |
| Next.js 15 升级 | 受 RISK-P12-001 影响，Next.js 保持 14.x，6 个 high 漏洞已接受（演示环境不暴露公网） |
| 服务端 Token 黑名单 | 受 RISK-P12-002 影响，logout 后 access_token 在过期前仍有效（60 分钟），已接受 |
| Prometheus/Grafana 真实部署 | 仅保留 `/metrics` 端点和轻量指标，不部署完整监控栈 |
| MinIO 对象存储 | 列为可选，本次 RC 不部署 |

## 3. Known Limitations（已知限制）

| 限制 | 影响 | 缓解 | 关联风险 |
| --- | --- | --- | --- |
| Docker 不可用（当前执行环境） | 无法验证容器化部署 | SQLite in-memory 全路径验证；恢复演练脚本覆盖降级行为 | RISK-P12-004 |
| gitleaks 不可用 | 密钥扫描使用替代脚本 | `scripts/security/check_no_secrets.py` 覆盖常见模式 | RISK-P12-003 |
| 性能预算在 SQLite 测量 | 生产 PostgreSQL 延迟可能不同 | 预算阈值宽松；关键路径有索引和连接池 | RISK-P12-008 |
| Prompt 注入仅 mock 验证 | 真实 LLM 可能存在未发现路径 | prompt 只传结构化胶囊；输出经 redaction | RISK-P12-005 |
| 威胁控制状态仍为 planned | 不能声称威胁已充分缓解 | P12 新增 105 后端 + 9 前端回归测试覆盖核心控制 | RISK-P12-010 |
| 数据保留 RT-004/RT-005 未自动删除 | AgentRun/AuditLog 表持续增长 | 比赛环境数据量小；手动清理脚本可用 | RISK-P12-006 |
| 清理脚本无定时调度 | 过期数据在手动清理前残留 | 场景结束同步清理；TTL 24h 兜底 | RISK-P12-007 |
| WebSocket 慢消费者使用模拟 | 真实高并发可能阻塞 | 连接上限和超时机制已实现 | RISK-P12-011 |
| 并发测试使用 SQLite | PostgreSQL 锁行为可能不同 | 幂等性靠唯一约束和应用检查 | RISK-P12-012 |

## 4. Release Candidate Rules

本次 RC 遵循以下规则，违反任一规则不得标记为 RC ready：

1. **No real secrets** — 仓库中不含真实实验室 Kuboard 地址、账号、密码、飞书 token、`MODEL_GATEWAY_API_KEY` 明文或私钥。
2. **No unreviewed network credentials** — 所有网络凭据使用占位符（`<LAB_MODEL_PLATFORM_URL>`、`<MODEL_GATEWAY_API_KEY>` 等）。
3. **No P0/P1 contract drift** — API `v1.0-frozen` 和 WebSocket `v1.0-frozen` 契约语义保持不变。
4. **All validation commands recorded** — `git diff --check`、`pip check`、`ruff`、`mypy`、`pytest`、`pnpm lint/typecheck/test/build` 结果均记录在 `P13-ACCEPTANCE-EVIDENCE.md`。
5. **No unverified claims** — 不声称未执行的验证已通过；未执行项在限制清单中明确列出。
6. **No new large features** — P13 只做文档对齐、启动验证、演示验证、证据整理。
7. **No commit / no push** — P13 执行方只准备 RC 状态，最终提交由 Codex 做。

## 5. RC 验收门禁

| 门禁 | 检查方法 | 通过标准 |
| --- | --- | --- |
| 文档完整性 | `conda run -n CampusAgent python scripts/release/check_release_candidate.py` | 退出码 0 |
| 密钥扫描 | `conda run -n CampusAgent python scripts/security/check_no_secrets.py` | 退出码 0 |
| 后端质量 | `ruff check` + `mypy` + `pytest` | 全部通过 |
| 前端质量 | `pnpm lint` + `typecheck` + `test` + `build` | 全部通过 |
| 依赖一致性 | `pip check` | 无冲突 |
| 演示可复现 | `conda run -n CampusAgent python scripts/demo/run_demo_smoke.py` | 11 步全部 PASS |
| 恢复演练 | `conda run -n CampusAgent python scripts/ops/recovery_drill.py` | 5 场景全部 PASS |

> Codex 审计后，RC 检查脚本的 required docs 已扩展为 P5-P13 全部完成报告以及 P12/P13 关键交付文档，共 15 个文档。
| 无 blocker | `docs/development/P12-RISK-REGISTER.md` | critical=0, blocker=0 |

## 6. 冻结时间点

- **RC 冻结基准**：`7f90393`（P12 完成提交）
- **RC 标记时间**：2026-07-18
- **冻结后规则**：冻结后不得新增功能，只允许修小文档错误、修启动脚本缺陷、补验收证据。任何语义变更必须经 Codex 审计。

---

**最后更新**：2026-07-18
**审批状态**：待 Codex 最终审计
