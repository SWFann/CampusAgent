# P13 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P13「Release Candidate、最终验收、演示交付与提交准备」完整执行指令。执行方必须在 `/root/CampusAgent` 中按顺序完成 P13-01 至 P13-14。P13 是当前路线的最后一个执行阶段。完成后不要提交、不要推送，写入 `docs/development/P13-COMPLETION-REPORT.md`，等待 Codex 进行最终审计、修 Bug、提交和推送。

## 0. 一句话目标

P13 的目标是把 P0-P12 的所有成果整理成一个可验收的 release candidate：一键启动说明、最终演示脚本、故障备用路径、验收证据包、release notes、最终风险清单和交给 Codex 的提交前检查材料。

## 1. 当前项目背景

项目路径固定为：

```bash
cd /root/CampusAgent
```

P13 默认 P12 已完成：

- 安全、隐私、性能、WebSocket、恢复演练已审计。
- 风险登记已建立。
- demo seed/reset 和主路径演示可复现。
- 前端产品闭环可演示。
- P0/P1 冻结契约仍保持权威。

P13 不应再引入大功能。P13 只做最后收口：

- 文档对齐。
- 启动流程验证。
- 演示流程验证。
- 证据整理。
- release candidate 标记。
- 等待 Codex 审计和提交。

## 2. 开始前检查

运行：

```bash
cd /root/CampusAgent
git status --short --branch
git log -1 --oneline
```

要求：

- 记录基准提交。
- 保留 P12 及以前未提交修改。
- 不使用破坏性 git 命令。
- 不提交，不推送。

## 3. 必读文件

必须阅读：

```text
docs/project/README.md
docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
docs/development/DEVELOPMENT_PLAN.md
docs/development/P11-DEMO-SCRIPT.md
docs/development/P12-COMPLETION-REPORT.md
docs/development/P12-RISK-REGISTER.md
docs/development/P12-RECOVERY-RUNBOOK.md
docs/api/API_CONTRACT.md
docs/api/WEBSOCKET_CONTRACT.md
docs/privacy/THREAT_MODEL.md
docs/privacy/PRIVACY_TEST_MATRIX.md
README.md
compose.yaml
Makefile
```

如果某个 P12 文件不存在，必须从 `development-logs/in-progress/` 找到对应日志，并在 P13 完成报告中说明。

## 4. P13 禁止事项

P13 禁止：

- 新增大业务功能。
- 重写前端页面。
- 重写认证、消息、场景、模型网关等核心模块。
- 修改 P0/P1 冻结契约语义。
- 引入真实密钥。
- 写入实验室 Kuboard 账号、密码、真实 endpoint、飞书 disposable token。
- 声称未执行的验证已通过。
- 提交或推送。

P13 允许：

- 修小文档错误。
- 修小 UI 文案或链接错误。
- 修启动脚本缺陷。
- 补 release 文档。
- 补验收证据。
- 补测试命令说明。

## 5. 建议文件规划

新增或修改：

```text
README.md
Makefile
.env.example
docs/development/DEVELOPMENT_PLAN.md
docs/development/P13-RC-CHECKLIST.md
docs/development/P13-DEMO-RUNBOOK.md
docs/development/P13-ACCEPTANCE-EVIDENCE.md
docs/development/P13-RELEASE-NOTES.md
docs/development/P13-COMPLETION-REPORT.md
development-logs/in-progress/P13-release-candidate.md
scripts/release/collect_evidence.py
scripts/release/check_release_candidate.py
```

如果已有 release 目录或脚本，复用现有结构。

## 6. P13-01 Release Candidate 范围确认

目标：明确本次 RC 包含什么，不包含什么。

输出文件：

```text
docs/development/P13-RC-CHECKLIST.md
```

必须包含：

```markdown
# P13 Release Candidate Checklist

## Included
- P0/P1 frozen contracts
- P2 infrastructure foundation
- P3 auth/user
- P4 organization/directory
- P5 conversation/message/WebSocket
- P6 agent/memory/privacy audit
- P7 model gateway/mock/provider routing
- P8 scene framework
- P9 dinner scenario
- P10 frontend product loop
- P11 demo data/E2E
- P12 hardening/security/performance

## Excluded
- Production deployment
- Real model credentials
- Real payment or billing
- Mobile native app
- Full multi-tenant enterprise admin
- Long-term backup system

## Release Candidate Rules
- No real secrets
- No unreviewed network credentials
- No P0/P1 contract drift
- All validation commands recorded
```

验收：

- 范围清楚。
- 不夸大能力。
- 未完成能力列入 excluded 或 known limitations。

## 7. P13-02 一键启动路径

目标：让新执行者能从 README 启动项目。

修改：

```text
README.md
Makefile
.env.example
```

README 必须包含：

- 项目简介。
- 环境要求。
- Conda 环境名：`CampusAgent`。
- Node/pnpm 要求。
- Docker 可用路径。
- Docker 不可用路径。
- API 测试命令。
- Web 构建命令。
- demo seed/reset 命令。
- 常见问题。

Makefile 建议提供：

```makefile
validate
validate-api
validate-web
demo-seed
demo-reset
demo-smoke
release-check
```

要求：

- Makefile 命令不能依赖不存在的工具而不提示。
- Docker 不可用时有清晰 fallback。
- `.env.example` 不包含真实密钥。

验收：

```bash
make validate-api
make validate-web
```

如果 Makefile 在当前项目已有不同风格，按现有风格补充。

## 8. P13-03 5 分钟演示 Runbook

目标：写给演示者，而不是开发者。

新增：

```text
docs/development/P13-DEMO-RUNBOOK.md
```

必须包含：

1. 演示前准备。
2. 启动命令。
3. demo 账号。
4. 5 分钟主线：
   - 登录。
   - 查看首页工作台。
   - 查看组织目录。
   - 进入消息。
   - 打开智能体/记忆说明。
   - 进入聚餐场景。
   - 提交或查看私有偏好。
   - 查看候选结果。
   - 投票/确认。
   - 打开管理后台 metadata。
5. 每一步讲什么价值。
6. 隐私保护怎么讲。
7. 模型不可用时怎么讲。
8. Docker 不可用时怎么讲。
9. 出错时如何恢复。

文案要求：

- 不写“万能 AI”。
- 不承诺真实生产能力。
- 强调隐私、协作、校园场景。

## 9. P13-04 故障备用路径

目标：比赛现场环境可能不稳定，需要准备备用路径。

在 `P13-DEMO-RUNBOOK.md` 或单独章节中写：

场景 A：Docker 不可用。

```bash
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm --filter @campus-agent/web build
```

场景 B：模型 mock 不可用。

- 展示 deterministic mock 结果。
- 说明真实模型接入在 P7 的 provider abstraction 后面。
- 不展示真实实验室地址或密钥。

场景 C：数据库不可用。

- 展示 `/health/ready` degraded。
- 展示 recovery runbook。
- 使用测试和截图证据说明功能。

场景 D：前端无法启动。

- 展示 build 成功记录。
- 展示 API tests 和 demo script 输出。
- 使用录屏或截图作为备用证据。

## 10. P13-05 验收证据收集脚本

目标：自动收集可贴给 Codex 审计的证据。

新增：

```text
scripts/release/collect_evidence.py
```

脚本输出建议目录：

```text
artifacts/release-evidence/
```

但注意 artifacts 如果被 gitignore，可只在报告中列出生成路径，不一定纳入 git。

脚本收集：

- `git status --short --branch`
- `git log -1 --oneline`
- `git diff HEAD --check`
- pytest 摘要。
- pnpm lint/typecheck/test/build 摘要。
- pip check 摘要。
- Docker/gitleaks 可用性。
- P12 risk register 摘要。

要求：

- 脚本不能吞掉失败。
- 每条命令记录 exit code。
- 输出 JSON 或 Markdown。

测试：

- 对脚本中 command runner 写单元测试，至少覆盖 success/failure/command missing。

## 11. P13-06 Release Candidate 检查脚本

目标：用机器检查“不要带着明显问题交给 Codex”。

新增：

```text
scripts/release/check_release_candidate.py
```

检查项：

- 必要文档存在：
  - `P13-RC-CHECKLIST.md`
  - `P13-DEMO-RUNBOOK.md`
  - `P13-ACCEPTANCE-EVIDENCE.md`
  - `P13-RELEASE-NOTES.md`
  - `P13-COMPLETION-REPORT.md`
- `.env.example` 不含明显真实密钥。
- docs 中不含 Kuboard 密码、飞书 disposable token。
- DEVELOPMENT_PLAN 不提前标记未来任务。
- P0/P1 冻结契约文件存在。
- P13 不新增 untracked 大二进制文件。

测试：

- 使用临时目录或 monkeypatch 测试 missing file。
- 测试 secret pattern 命中会失败。
- 测试正常路径返回 0。

## 12. P13-07 Release Notes

新增：

```text
docs/development/P13-RELEASE-NOTES.md
```

必须包含：

- 版本名称：CampusAgent MVP RC1。
- 日期。
- 包含阶段 P0-P13。
- 核心能力摘要。
- 安全和隐私摘要。
- 已知限制。
- 未接入真实模型密钥说明。
- Docker/gitleaks 执行状态。
- 如何回滚：交给 git，不写破坏性命令。

不要写：

- “生产可用”。
- “完全安全”。
- “所有模型已真实接入”。

## 13. P13-08 验收证据文档

新增：

```text
docs/development/P13-ACCEPTANCE-EVIDENCE.md
```

内容结构：

```markdown
# P13 Acceptance Evidence

## 1. Git Baseline

## 2. Validation Commands

## 3. Test Counts

## 4. Frontend Build Evidence

## 5. Demo Evidence

## 6. Security Evidence

## 7. Known Gaps

## 8. Files Changed Summary
```

必须粘贴关键命令的摘要输出，不要粘贴超长日志。

## 14. P13-09 最终文档链接检查

目标：避免最后交付文档内部链接断掉。

可以复用之前 R1-32 的链接检查方法，或新增脚本。

检查范围：

```text
README.md
docs/**/*.md
development-logs/**/*.md
```

要求：

- 外部链接可跳过。
- 相对路径必须存在。
- anchor 如检查困难，至少检查文件路径。
- historical 历史记录可保留，但报告中说明。

验收：

- 当前权威文档无失效内部链接。
- 若历史日志中存在旧链接，明确列为 historical exception。

## 15. P13-10 最终安全扫尾

目标：P13 不把敏感实验室信息或 token 写进仓库。

必须扫描：

- Kuboard 平台地址。
- 用户提供的账号。
- 用户提供的密码。
- 飞书 disposable token。
- `MODEL_GATEWAY_API_KEY` 明文。
- `APP_SECRET` 真实值。
- 私钥。

如果发现这些信息在 docs 或代码中，立即删除或改成占位符：

```text
<LAB_MODEL_PLATFORM_URL>
<LAB_MODEL_USERNAME>
<LAB_MODEL_PASSWORD>
<MODEL_GATEWAY_API_KEY>
```

注意：可以保留“实验室模型通过 k8s 平台统一部署，vLLM/llama.cpp 以 Ingress/NodePort 暴露”这种非敏感架构描述。

## 16. P13-11 最终演练

目标：按 P13 demo runbook 实际走一遍。

至少执行：

```bash
make validate-api
make validate-web
```

如果 demo seed/reset 可用：

```bash
make demo-reset
make demo-seed
make demo-smoke
```

如果没有 Makefile target，则运行等价命令并补充 target 或在报告中说明。

人工演练记录：

- 登录是否成功。
- 首页是否可用。
- 组织页是否可用。
- 消息页是否可用。
- 聚餐结果是否可用。
- 管理后台是否只展示 metadata。
- 私有偏好是否未泄露。

## 17. P13-12 DEVELOPMENT_PLAN 最终对齐

修改：

```text
docs/development/DEVELOPMENT_PLAN.md
```

要求：

- P13 标记为完成或 RC ready。
- P0-P12 状态与报告一致。
- 不新增没有计划的阶段。
- 如果后续还有生产部署阶段，只写为 future work，不标记完成。

## 18. P13-13 完成报告

新增：

```text
development-logs/in-progress/P13-release-candidate.md
docs/development/P13-COMPLETION-REPORT.md
```

完成报告模板：

```markdown
# P13 Completion Report

## 1. 基准信息
- 项目路径：
- 当前分支：
- 基准提交：
- 开始前工作树：

## 2. 完成任务
- P13-01：
- ...
- P13-14：

## 3. Release Candidate 范围

## 4. 启动与演示路径

## 5. 验收证据摘要

## 6. 安全扫尾结果

## 7. 文档链接检查结果

## 8. 修改文件列表

## 9. 验证命令结果

## 10. 未执行项与原因

## 11. 已知限制

## 12. 交给 Codex 的审计提示

## 13. 边界声明
- 未提交、未推送
- 未引入真实密钥
- 未修改 P0/P1 冻结契约语义
- 未声称生产部署完成
```

## 19. P13-14 最终自检命令

必须运行：

```bash
cd /root/CampusAgent
git diff HEAD --check
conda run -n CampusAgent pip check
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
```

运行 release 脚本：

```bash
python scripts/release/check_release_candidate.py
python scripts/release/collect_evidence.py
```

如果 Docker 可用：

```bash
docker compose config
docker compose up -d postgres redis mock-model
docker compose ps
docker compose down
```

如果 gitleaks 可用：

```bash
gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner
```

如果某条命令失败：

- 先判断是否是 P13 引入。
- 小问题直接修。
- 大问题记录 blocker。
- 不要在报告中写“全部通过”。

## 20. 最终交付给 Codex 的摘要格式

P13 完成后，向用户输出类似：

```markdown
P13 完成报告摘要

1. 基准
- 路径：
- 分支：
- 基准提交：

2. 完成任务
- P13-01 至 P13-14：

3. 核心交付物
- RC checklist：
- Demo runbook：
- Acceptance evidence：
- Release notes：
- Release scripts：

4. 验证结果
- ruff：
- mypy：
- pytest：
- pnpm lint/typecheck/test/build：
- pip check：
- docker：
- gitleaks：

5. 已知限制

6. 声明
- 未提交、未推送
- 未引入真实密钥
- 未修改冻结契约语义
- 等待 Codex 最终审计、修 Bug、提交、推送
```

## 21. Codex 最终审计提醒

P13 执行方不要提交。最终提交由 Codex 做：

1. Codex 审计 git diff。
2. Codex 运行全量验证。
3. Codex 修小问题。
4. Codex 检查敏感信息。
5. Codex commit。
6. Codex push。
7. Codex 观察远端 CI。

执行方只负责把 RC 状态准备好。
