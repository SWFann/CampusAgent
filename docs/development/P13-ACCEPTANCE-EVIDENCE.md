# P13 Acceptance Evidence

> **版本**：CampusAgent MVP RC1
>
> **证据收集日期**：2026-07-18
>
> **基线提交**：`7f90393` (P12 完成)
>
> **关联文档**：`docs/development/P13-RC-CHECKLIST.md`、`docs/development/P13-RELEASE-NOTES.md`、`docs/development/P13-COMPLETION-REPORT.md`

## 1. Git Baseline

```
## main...origin/main
7f90393 feat(p12): complete system hardening - security, stability, performance, recovery drills
92e0db0 feat(demo): complete P11 demo data, E2E smoke, and frontend demo account switching
2579eb6 feat(web): complete P10 frontend product loop and admin dashboard
```

- **分支**：`main`
- **基准提交**：`7f90393`
- **工作树状态**：开始时干净，P13 执行后包含 P13 文档和脚本改动
- **git diff HEAD --check**：✅ 无空白错误

## 2. Validation Commands

### 2.1 后端验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `git diff HEAD --check` | ✅ PASS | 无空白错误 |
| `ruff check apps/api --no-cache` | ✅ PASS | `All checks passed!` |
| `mypy apps/api/src apps/api/tests --no-incremental` | ✅ PASS | `Success: no issues found in 321 source files` |
| `pip check` | ✅ PASS | `No broken requirements found.` |
| `pytest apps/api/tests -q -p no:cacheprovider` | ✅ PASS | `1473 passed, 1 warning in 145.52s` |

**pytest 摘要**：
```
1473 passed, 1 warning in 145.52s (0:02:25)
```

**唯一警告**（预存，非 P13 引入）：
```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

### 2.2 前端验证

| 命令 | 结果 | 证据 |
|---|---|---|
| `corepack pnpm lint` | ✅ PASS | `All checks passed!` |
| `corepack pnpm typecheck` | ✅ PASS | `Success: no issues found` |
| `corepack pnpm test` | ✅ PASS | 1473 API + 115 前端测试通过 |
| `corepack pnpm --filter @campus-agent/web build` | ✅ PASS | 构建成功，静态页面生成完成 |

**前端构建摘要**：
```
○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
+ First Load JS shared by all: 87.3 kB
```

## 3. Test Counts

| 测试层 | 数量 | 状态 |
|---|---|---|
| 后端 API 测试 | 1473 | ✅ 全部通过 |
| 前端测试 | 115 | ✅ 全部通过 |
| Demo smoke（11 步） | 11 | ✅ 全部通过 |
| 恢复演练（5 场景） | 5 | ✅ 全部通过 |
| **总计** | **1604** | **✅ 全部通过** |

### 3.1 Demo Smoke 详细结果

```
============================================================
CampusAgent Demo Smoke Test
============================================================
  [PASS] build_app — in-memory SQLite + FastAPI app created
  [PASS] seed_demo — users_created=5, scenes_created=1
  [PASS] admin_login — status=200
  [PASS] directory_tree — status=200
  [PASS] list_conversations — status=200
  [PASS] list_scenes — status=200
  [PASS] demo_status — users_present=5, scenes_present=1
  [PASS] privacy_no_leak — DEMO_PRIVATE_PHRASE not found in responses
  [PASS] deleted_user_blocked — status=401
  [PASS] non_admin_blocked — status=403
  [PASS] logout — status=204
------------------------------------------------------------
Result: 11 passed, 0 failed -> ALL PASSED
```

### 3.2 恢复演练详细结果

```
Summary: 5 passed, 0 failed, 0 skipped
```

| 演练 | 验证内容 | 结果 |
|---|---|---|
| database-unavailable | DB 不可用时 /health/ready degraded | PASS |
| redis-unavailable | Redis 未配置时 degraded，/health/live ok | PASS |
| model-gateway-unavailable | 模型网关无 provider 时不 500 | PASS |
| demo-reset-reseed | seed→reset→reseed 循环正常 | PASS |
| cleanup-then-read | 清理后主路径仍 200 | PASS |

## 4. Frontend Build Evidence

前端构建成功，生成以下路由：

| 路由 | 大小 | 类型 |
|---|---|---|
| `/` (首页) | — | ƒ (Dynamic) |
| `/login` | — | ○ (Static) |
| `/register` | 2.52 kB | ○ (Static) |
| `/directory` | — | ○ (Static) |
| `/messages` | — | ○ (Static) |
| `/agents` | — | ○ (Static) |
| `/memories` | — | ○ (Static) |
| `/memory` | — | ○ (Static) |
| `/scenes` | 1.28 kB | ○ (Static) |
| `/scenes/dinner` | 3.42 kB | ○ (Static) |
| `/scenes/dinner/result` | 3.95 kB | ○ (Static) |
| `/preferences/private` | 4.08 kB | ○ (Static) |
| `/admin/audit` | — | ○ (Static) |
| `/admin/models` | — | ○ (Static) |
| `/organizations/[organizationId]` | 2.75 kB | ƒ (Dynamic) |
| `/conversations/[conversationId]` | — | ƒ (Dynamic) |
| `/health` | — | ○ (Static) |

**共享 JS**: 87.3 kB

## 5. Demo Evidence

### 5.1 Demo 数据

| 数据类型 | 数量 | 说明 |
|---|---|---|
| Demo 用户 | 5 | admin, alice, bob, carol, deleted |
| 组织 | 2 | JNU Campus Demo Lab, Demo Dorm 301 |
| 会话 | 1 | 群聊 |
| 消息 | 3 | 含场景卡 |
| 场景实例 | 1 | 聚餐协商（已完成全生命周期） |
| 投票 | 2 | |
| 私有偏好 | 3 | 含 DEMO_PRIVATE_PHRASE 标记 |

### 5.2 隐私验证

| 检查项 | 结果 |
|---|---|
| `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/scenes` 响应 | ✅ |
| `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/directory/tree` 响应 | ✅ |
| `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/auth/me` 响应 | ✅ |
| `DEMO_PRIVATE_PHRASE` 不出现在 `/api/v1/conversations` 响应 | ✅ |
| 软删除用户登录被拒绝（401） | ✅ |
| 非管理员访问 demo reset 被拒绝（403） | ✅ |

## 6. Security Evidence

### 6.1 密钥扫描

| 工具 | 结果 |
|---|---|
| `scripts/security/check_no_secrets.py` | ✅ scanned 710 files, no real secrets detected |
| `scripts/release/check_release_candidate.py` | ✅ required docs 15 present; scanned 701 files, no real secrets |

### 6.2 敏感信息检查

| 检查项 | 结果 |
|---|---|
| `.env.example` 无真实密钥 | ✅ APP_SECRET=dev-secret-key-change-in-production, MODEL_GATEWAY_API_KEY=空 |
| 无 Kuboard 平台地址 | ✅ 仅有策略性提及（"不得写入"） |
| 无飞书 disposable token | ✅ 仅有策略性提及 |
| 无 PEM 私钥 | ✅ |
| 无实验室私有 IP 地址 | ✅ |
| 无 `MODEL_GATEWAY_API_KEY` 明文值 | ✅ 测试文件中使用 `some-api-key` 占位值 |

### 6.3 RC 检查脚本结果

```
============================================================
P13 Release Candidate Check
============================================================
  [PASS] required_docs: all 8 docs present
  [PASS] frozen_contracts: API & WebSocket contracts present
  [PASS] no_real_secrets: scanned 698 files, no real secrets
  [PASS] env_example: no real secrets in .env.example
  [PASS] dev_plan: P13 progress recorded in DEVELOPMENT_PLAN
  [PASS] large_untracked: no large untracked files
------------------------------------------------------------
6 passed, 0 failed
```

### 6.4 文档链接检查结果

| 检查项 | 结果 |
|---|---|
| 扫描文件数 | 247 |
| 总链接数 | 172 |
| 有效链接 | 167 |
| 断链 | 0 |
| 外部链接（跳过） | 5 |
| 锚点链接 | 26 |

## 7. Known Gaps

| 差距 | 原因 | 影响 | 关联风险 |
|---|---|---|---|
| Docker 不可用 | 当前执行环境无 Docker | 无法验证容器化部署 | RISK-P12-004 |
| gitleaks 不可用 | 当前执行环境无 gitleaks | 使用替代脚本 | RISK-P12-003 |
| 性能预算在 SQLite 测量 | 测试环境使用 SQLite | 生产 PostgreSQL 延迟可能不同 | RISK-P12-008 |
| 真实模型未接入 | 本 RC 不接入真实模型 | 使用 Mock/Rule Provider | — |
| 生产环境未演练 | 本 RC 面向比赛演示 | 恢复演练在测试环境运行 | RISK-P12-009 |

## 8. Files Changed Summary

### 新增文件

| 文件路径 | 说明 |
|---|---|
| `docs/development/P13-RC-CHECKLIST.md` | RC 范围清单 |
| `docs/development/P13-DEMO-RUNBOOK.md` | 5 分钟演示 Runbook + 故障备用路径 |
| `docs/development/P13-RELEASE-NOTES.md` | Release Notes RC1 |
| `docs/development/P13-ACCEPTANCE-EVIDENCE.md` | 验收证据（本文件） |
| `docs/development/P13-COMPLETION-REPORT.md` | P13 完成报告 |
| `development-logs/in-progress/P13-release-candidate.md` | P13 开发日志 |
| `scripts/release/collect_evidence.py` | 验收证据收集脚本 |
| `scripts/release/check_release_candidate.py` | RC 检查脚本 |
| `scripts/release/check_doc_links.py` | 文档链接检查脚本 |
| `apps/api/tests/unit/test_release_scripts.py` | release 脚本单元测试（41 个测试） |

### 修改文件

| 文件路径 | 修改内容 |
|---|---|
| `README.md` | 更新状态为 RC1；添加环境要求、快速开始、验证命令、演示数据章节 |
| `Makefile` | 添加 validate/validate-api/validate-web/demo-seed/demo-reset/demo-smoke/release-check/release-evidence targets |
| `docs/development/DEVELOPMENT_PLAN.md` | P13 任务标记完成，P0-P12 状态确认一致 |

---

**最后更新**：2026-07-18
**审批状态**：待 Codex 最终审计
