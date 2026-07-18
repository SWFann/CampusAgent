# CampusAgent MVP RC1 Release Notes

> **版本名称**：CampusAgent MVP RC1
>
> **发布日期**：2026-07-18
>
> **基线提交**：`7f90393` (P12 完成)
>
> **包含阶段**：P0–P13（全部完成）

## 1. 概述

CampusAgent MVP RC1 是一个隐私优先的智能体原生校园通讯与协作平台的首个发布候选版本。RC1 包含从契约冻结到完整聚餐协商场景闭环的全部能力，可在无公网环境下完成 5 分钟主线演示。

**核心命题**：不暴露个人真实偏好，也能提高校园集体决策效率。

## 2. 核心能力摘要

| 能力域 | 说明 |
|---|---|
| 身份与用户 | 注册、登录、刷新、注销、资料读写、账号禁用、Auth 限流 |
| 组织与目录 | 多级组织树（学校—学院—班级/宿舍）、成员生命周期、RBAC、目录搜索 |
| 会话与实时 | 私聊/群聊/组织群聊、消息分页、WebSocket 鉴权、PubSub、事件信封、重连回补 |
| 智能体与记忆 | 个人智能体（L0-L3）、MemoryItem 字段加密、Consent 授权、审计日志、TTL 清理 |
| 模型网关 | Mock/Rule/OpenAI Provider、隐私路由、结构化校验、节点熔断、管理 API |
| 场景框架 | ScenePlugin Protocol、状态机、私有提交加密、执行协调器、投票确认、清理编排 |
| 聚餐协商 | 输入 Schema、偏好胶囊、10 家餐厅、确定性聚合、安全理由、场景 API、群聊场景卡 |
| 前端闭环 | 首页工作台、消息页、组织页、智能体页、记忆页、场景中心、私有偏好页、管理后台 |
| 演示数据 | 5 demo 用户、2 组织、幂等 seed、fail-closed reset、demo 账号切换、主路径 smoke |
| 安全加固 | IDOR 回归、Prompt 注入防御、日志脱敏、并发幂等、性能预算、WebSocket 稳定性 |

## 3. 冻结契约

| 契约 | 版本 | 端点数 | 文件 |
|---|---|---|---|
| HTTP API | `v1.0-frozen` | 71（68 MVP + 3 internal） | `docs/api/API_CONTRACT.md` |
| WebSocket | `v1.0-frozen` | — | `docs/api/WEBSOCKET_CONTRACT.md` |

P13 未修改冻结契约语义。

## 4. 测试基线

| 测试层 | 数量 | 状态 |
|---|---|---|
| 后端 API 测试 | 1473 | 全部通过（含 P13 新增 41 个 release 脚本测试） |
| 前端测试 | 115 | 全部通过 |
| Demo smoke | 11 步 | 全部通过 |
| 恢复演练 | 5 场景 | 全部通过 |

## 5. 安全和隐私摘要

| 检查项 | 结果 |
|---|---|
| 密钥扫描（`check_no_secrets.py`） | 无真实密钥 |
| 日志脱敏（denylist 16+ 字段） | 无泄露 |
| 前端存储审计 | localStorage/sessionStorage 无 token/正文 |
| Admin 不泄露偏好 | 审计日志只有 metadata |
| `DEMO_PRIVATE_PHRASE` 不泄露 | 不出现在结果/目录/状态 |
| 场景清理 | 原始提交、胶囊、评价全部清理 |
| 失败关闭 | 加密/授权故障时拒绝请求 |

威胁模型包含 9 个威胁，控制状态仍为 `planned`（P12 回归测试提供了部分验证证据，但按保守聚合规则未升级状态）。

## 6. 已知限制

| 限制 | 严重性 | 状态 | 关联风险 |
|---|---|---|---|
| Next.js 14.x 存在 6 个 high 漏洞 | high | accepted | RISK-P12-001 |
| Logout 后 access_token 60 分钟内仍有效 | high | accepted | RISK-P12-002 |
| Docker 不可用，未验证容器化部署 | medium | accepted | RISK-P12-004 |
| gitleaks 不可用，使用替代脚本 | medium | accepted | RISK-P12-003 |
| 性能预算在 SQLite 测量 | medium | accepted | RISK-P12-008 |
| Prompt 注入仅 mock 验证 | medium | accepted | RISK-P12-005 |
| 威胁控制状态仍为 planned | medium | accepted | RISK-P12-010 |
| 数据保留 RT-004/RT-005 未自动删除 | medium | accepted | RISK-P12-006 |
| 清理脚本无定时调度 | medium | accepted | RISK-P12-007 |
| 恢复演练在测试环境运行 | medium | accepted | RISK-P12-009 |
| WebSocket 慢消费者使用模拟 | low | accepted | RISK-P12-011 |
| 并发测试使用 SQLite | low | accepted | RISK-P12-012 |

**无 critical 风险，无 blocker。**

## 7. 未接入真实模型密钥说明

本 RC **不包含**任何真实模型密钥。所有模型调用使用 Mock Provider 或 Rule Provider：

- `MODEL_GATEWAY_API_KEY` 在 `.env.example` 中为空。
- `ENABLE_EXTERNAL_MODEL=false` 默认禁用外部模型。
- 实验室模型平台地址、Kuboard 凭据、飞书 token 均未写入仓库。
- 聚餐场景使用确定性规则引擎，不依赖任何真实模型即可完整运行。

如需接入真实模型，在 `.env` 中配置 `MODEL_GATEWAY_API_KEY` 和 `MODEL_GATEWAY_BASE_URL`，并设置 `ENABLE_EXTERNAL_MODEL=true`。真实模型凭据**不得**提交到仓库。

## 8. Docker / gitleaks 执行状态

| 工具 | 状态 | 替代方案 |
|---|---|---|
| Docker | 不可用（当前执行环境） | SQLite in-memory 全路径验证；恢复演练脚本覆盖降级行为 |
| gitleaks | 不可用 | `scripts/security/check_no_secrets.py` 替代脚本扫描常见密钥模式 |

在有 Docker 和 gitleaks 的环境中应执行：
```bash
docker compose config
docker compose up -d postgres redis mock-model
gitleaks detect --source . --redact --verbose --no-banner
```

## 9. 如何回滚

RC1 的回滚完全依赖 git 版本控制，不使用破坏性命令：

```bash
# 查看提交历史
git log --oneline -10

# 回滚到指定提交（需审批，不自动推送）
git revert <commit-hash>
```

数据库迁移回滚：
```bash
cd apps/api
conda run -n CampusAgent alembic downgrade -1
conda run -n CampusAgent alembic current
```

> 迁移回滚有数据丢失风险，必须先备份。demo 环境可直接 `reset_demo` + `seed_demo` 重建。

## 10. 交付物清单

| 类别 | 文件 |
|---|---|
| RC 清单 | `docs/development/P13-RC-CHECKLIST.md` |
| 演示 Runbook | `docs/development/P13-DEMO-RUNBOOK.md` |
| Release Notes | `docs/development/P13-RELEASE-NOTES.md`（本文件） |
| 验收证据 | `docs/development/P13-ACCEPTANCE-EVIDENCE.md` |
| 完成报告 | `docs/development/P13-COMPLETION-REPORT.md` |
| 证据收集脚本 | `scripts/release/collect_evidence.py` |
| RC 检查脚本 | `scripts/release/check_release_candidate.py` |
| 恢复操作手册 | `docs/development/P12-RECOVERY-RUNBOOK.md` |
| 风险登记册 | `docs/development/P12-RISK-REGISTER.md` |

## 11. 声明

- 本 RC 面向**比赛演示**，不是生产可用版本。
- 未接入真实模型密钥，不声称"所有模型已真实接入"。
- 未声称"完全安全"或"生产可用"。
- 所有 high 风险已接受且有后续计划，无 blocker。
- P13 执行方未提交、未推送，等待 Codex 最终审计、修 Bug、提交、推送。

---

**最后更新**：2026-07-18
**审批状态**：待 Codex 最终审计
