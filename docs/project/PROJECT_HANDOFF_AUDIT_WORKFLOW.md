# CampusAgent 任务交接与审计工作流

> 适用场景：用户中断当前对话、切换到新对话、切换执行工具（Claude / CatPaw / GLM / Codex）时，用本文快速恢复项目背景、任务状态、执行指令模板和审计方式。

## 1. 项目基本信息

**项目名称**：CampusAgent

**项目定位**：隐私优先、智能体原生的校园平台。系统面向校园组织、师生、社团、活动与多智能体协作场景，核心能力包括 Conversation、Agent、Memory、Scene、Model Gateway、Admin、Edge Node、WebSocket 实时事件和隐私测试矩阵。

**核心原则**：

- 契约先行：先冻结 API / WebSocket / 威胁模型 / 隐私测试矩阵，再进入实现。
- 隐私优先：按 P0 / P1 / P2 / P3 / P4 数据分级设计。
- 失败关闭：授权、解密、租户隔离、模型路由、日志、清理失败时不得公开降级。
- 测试定义与测试执行分离：`defined` 不等于 `passed`，`not_run` 不等于已验证。
- 控制状态保守：P0/P1 阶段控制状态保持 `planned`，不得误称为 `implemented` 或 `verified`。

**本地路径（Windows）**：

```text
F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent
```

**主工作区路径（WSL / root 用户）**：

```text
/root/CampusAgent
```

**历史来源路径（Windows 挂载盘，避免继续用于 npm/Next/Playwright 重任务）**：

```text
/mnt/f/工作盘/实习经历汇总/星星之火-创业/模型互联网比赛/CampusAgent
```

**远程仓库**：

```text
git@github.com:SWFann/CampusAgent.git
```

**当前主分支**：

```text
main
```

**当前推荐 Conda 环境**：

```text
CampusAgent
```

**SSH / WSL 连接别名**：

```text
Ubuntu2-Codex
```

已验证连接方式：

```powershell
ssh Ubuntu2-Codex
```

该别名解析到：

```text
HostName 127.0.0.1
Port 2222
User root
IdentityFile C:/Users/10481/.ssh/codex_wsl
```

如连接失败，优先检查本机 `127.0.0.1:2222` 是否监听，以及 WSL/Ubuntu SSH 服务是否启动。

## 2. 当前执行状态快照

截至 2026-07-16 本地冻结状态：

```text
最新已推送提交：3f2ee03 docs(security): define fail-closed and retention tests
上一基准提交：0451e82 docs(security): map threats to privacy tests
最新本地冻结提交：由 R1-36 本地 commit 生成，以 git log -1 为准
```

R1-D 已完成并推送到 GitHub：

- R1-25：修复威胁编号
- R1-26：修正威胁数量
- R1-27：区分控制状态
- R1-28：补充边缘节点威胁
- R1-29：建立威胁—控制—测试双向映射
- R1-30：检查隐私失败关闭
- R1-31：复核保留策略

R1-E 本地收口状态：

| 状态 | 任务 | 名称 | 目标 |
|---|---|---|---|
| `[x]` | R1-32 | 修复全部内部链接 | 文档与日志链接检查结果为 0 个失效链接 |
| `[x]` | R1-33 | 修正 P0 完成总结 | P0 总结与当前权威口径一致 |
| `[x]` | R1-34 | 更新 P0 进度表 | 进度状态与实际任务完成情况一致 |
| `[x]` | R1-35 | 进行 P0 人工评审 | 形成本地复审结论 |
| `[x]` | R1-36 | 形成 P0 冻结提交 | P0/P1 本地冻结提交由 Codex 形成 |

远端边界：

- 本地冻结提交不等于已推送。
- `R3-25` / `R4-19` 的远端 GitHub Actions 观察必须在用户授权 `git push` 后完成。
- 后续 P2 交给 Claude 执行前，应先确认 `git log -1 --oneline`、`git status --short` 和是否已推送。

### 2.1 已完成任务总览

以下列表用于新对话快速判断“哪些任务不应重复执行”。

| 阶段 | 任务 | 状态 | 说明 |
|---|---|---|---|
| 初始化 | 项目目录与 README | 已完成 | 已初始化项目结构、README、远程仓库 |
| P0/P1 | 初始审计 | 已完成 | Claude 完成 P0/P1 后由 Codex 审计 |
| R1-A/B/C | R1-08～R1-13 | 已完成 | Conversation / Agent / Memory / Scene / Model Gateway / Admin API |
| R1-C | R1-14～R1-17 | 已完成 | 路径、错误码、幂等、API 冻结 |
| R1-C | R1-18～R1-21 | 已完成 | 浏览器认证、CSRF、Cookie、权限相关契约 |
| R1-C | R1-22 | 已完成 | WebSocket 鉴权改为 HttpOnly Cookie + Origin 校验 |
| R1-C | R1-23 | 已完成 | WebSocket Token 过期、重连、回补、状态机 |
| R1-C | R1-24 | 已完成 | WebSocket 事件 Schema 冻结 |
| R1-D | R1-25 | 已完成 | 威胁编号修正，T-01～T-08 统一 |
| R1-D | R1-26 | 已完成 | 威胁数量修正：严重 1 / 高 5 / 中 2 / 低 0 |
| R1-D | R1-27 | 已完成 | 控制状态统一为 planned / implemented / verified |
| R1-D | R1-28 | 已完成 | 增加边缘节点威胁 T-09，风险分布变为 1 / 6 / 2 / 0 |
| R1-D | R1-29 | 已完成 | 建立威胁—控制—测试双向映射，测试定义 78 |
| R1-D | R1-30 | 已完成 | 新增 FC-001～FC-012，测试定义 90 |
| R1-D | R1-31 | 已完成 | 新增 RT-001～RT-010，测试定义 100，AuditLog 180 天 |
| R1-E | R1-32 | 已完成 | 内部链接检查结果为 0 个失效链接 |
| R1-E | R1-33 | 已完成 | P0 完成总结对齐 71 端点、9 威胁、planned 控制状态 |
| R1-E | R1-34 | 已完成 | 开发计划进度表对齐当前状态 |
| R1-E | R1-35 | 已完成 | P0 本地复审通过，准许进入冻结提交 |
| R1-E | R1-36 | 已完成 | 本地冻结提交由 Codex 形成；未推送 |

### 2.2 最近提交记录

新对话恢复时应先确认：

```powershell
git log --oneline -5
git status --short
```

预期最近提交包含：

```text
3f2ee03 docs(security): define fail-closed and retention tests
0451e82 docs(security): map threats to privacy tests
```

如果最新提交不是 R1-36 本地冻结提交，或工作区不干净，应先暂停，让用户确认当前状态。

### 2.3 当前不应重复做的事

不要重复执行：

- R1-25～R1-31 的内容；
- WebSocket 鉴权、事件 Schema、Token 过期与重连契约；
- API 端点补全文档；
- 威胁编号、威胁数量、控制状态、T-09、测试矩阵新增；
- AuditLog 180 天保留策略修正。

除非用户明确要求“复审”或“回滚/重做”，否则不要重复执行 R1-32～R1-36。

## 3. 当前权威口径

### 3.1 API 契约

- MVP HTTP 端点：68
- internal 端点：3
- 总文档化端点：71
- 权威文档：`docs/api/API_CONTRACT.md`
- 不得在 R1-E 中新增端点、修改错误码或修改 API 契约语义，除非任务明确要求。

### 3.2 WebSocket 契约

- 当前路径：`/api/v1/ws`
- 认证方式：HttpOnly `access_token` Cookie
- 禁止 URL Token
- Origin 白名单强制校验
- 状态：`v1.0-frozen`
- 权威文档：`docs/api/WEBSOCKET_CONTRACT.md`

### 3.3 威胁模型

- 当前威胁：T-01～T-09，共 9 个
- 风险分布：
  - 严重 Critical：1
  - 高 High：6
  - 中 Medium：2
  - 低 Low：0
- 控制状态：
  - `planned`：9
  - `implemented`：0
  - `verified`：0
- 权威文档：`docs/security/THREAT_MODEL.md`

### 3.4 隐私测试矩阵

- 当前正式测试定义总数：100
- 定义状态：`defined=100`
- 执行状态：`not_run=100`
- 测试尚未执行，不代表通过。

分类统计：

| 前缀 | 数量 |
|---|---:|
| PT | 25 |
| ST | 5 |
| CL | 5 |
| LG | 9 |
| REV | 4 |
| EXP | 3 |
| PI | 5 |
| RP | 5 |
| MR | 5 |
| EN | 12 |
| FC | 12 |
| RT | 10 |
| 总计 | 100 |

权威章节：

- `docs/privacy/PRIVACY_TEST_MATRIX.md §12`：隐私失败关闭测试 FC-001～FC-012
- `docs/privacy/PRIVACY_TEST_MATRIX.md §13`：保留策略测试 RT-001～RT-010
- `docs/privacy/PRIVACY_TEST_MATRIX.md §14`：威胁—控制—测试追踪矩阵
- `docs/privacy/PRIVACY_TEST_MATRIX.md §15`：测试执行要求
- `docs/privacy/PRIVACY_TEST_MATRIX.md §16`：相关文档

### 3.5 数据保留策略

权威文档：`docs/architecture/DATA_INVENTORY.md §13`

关键口径：

- AuditLog metadata：180 天
- AgentRun / ModelCall metadata：30 天
- Scene 临时私有数据：结束后立即删除，TTL 兜底 24h
- Export 文件：1 小时
- WebSocket 去重缓存：最多 1000 条或 24 小时

## 4. 协作分工

常见协作模式：

1. 用户向 Claude / CatPaw / GLM 发送详细执行指令。
2. 执行工具修改文档或代码，并给出完成报告。
3. Codex 本地审计，不只看报告，必须运行检查命令核验。
4. 审计不通过：Codex 给出明确整改指令，不提交。
5. 审计通过：用户要求后，Codex 提交并推送 GitHub。
6. 进入下一个任务。

原则：

- 执行任务和审计任务分离。
- 每个任务编号是最小工作单元。
- 文档契约类任务不应混入业务代码实现。
- 未经审计通过，不提交。
- 未经用户明确要求，不主动推送。

### 4.1 推荐协作节奏

推荐采用“一次执行一个任务，一次审计一个任务”的节奏。

适合一次执行一个任务的情况：

- 会修改权威契约；
- 会影响统计数字；
- 会移动日志；
- 会改变任务状态；
- 会影响后续任务边界。

可考虑合并执行的情况：

- 任务很小；
- 修改范围完全相同；
- 后一个任务天然依赖前一个任务；
- 审计成本大于修改成本。

本项目当前阶段建议：

- R1-32～R1-36 已由 2026-07-16 本地收口完成；
- 之后若进入 P2，应先确认本地冻结提交是否已推送、远端 CI 是否绿色；
- 未经用户明确授权，不主动推送。

### 4.2 执行工具选择建议

| 工具 | 适合任务 | 注意事项 |
|---|---|---|
| Claude | 长文档整改、结构化总结 | 指令必须极细，容易遗漏边界 |
| CatPaw / GLM | 大批量文档机械修改 | 要求给出明确自检命令和禁止项 |
| Codex | 审计、提交、推送、本地验证 | 不应在未授权时替代执行方大改 |

执行工具完成后，应要求它输出：

1. 修改文件列表；
2. 每个文件的修改点；
3. 自检命令；
4. 自检结果；
5. 未提交、未推送声明。

Codex 审计时应重新跑自检，不直接采信报告。

## 5. 新对话启动模板

新开对话时，可以直接发送：

```text
请读取并遵循：
docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
docs/project/P0_P1_REMEDIATION_PLAN.md

当前项目路径：
F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent

当前远程仓库：
git@github.com:SWFann/CampusAgent.git

请先确认当前 git 状态、最新提交、R1-36 本地冻结提交是否存在，以及是否已推送观察 CI。
如果准备进入 P2，请先给出 P2 执行计划；不要自动推送。
```

如果是让执行工具继续任务，可以发送：

```text
你现在负责 CampusAgent 项目的 R1-XX：<任务名称>。

请先阅读：
1. docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
2. docs/project/P0_P1_REMEDIATION_PLAN.md
3. 与本任务直接相关的权威文档

执行约束：
- 不提交，不推送；
- 不修改任务范围外文件；
- 不修改业务代码，除非任务明确要求；
- 每项变更必须记录到 development-logs/in-progress/R1-XX-*.md；
- 完成后按指定格式报告，等待 Codex 审计。
```

### 5.1 新对话给 Codex 的完整启动 Prompt

如果新对话由 Codex 继续审计或安排任务，建议直接复制：

```text
你现在接手 CampusAgent 项目。

项目路径：
F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent

远程仓库：
git@github.com:SWFann/CampusAgent.git

请首先读取：
1. docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
2. docs/project/P0_P1_REMEDIATION_PLAN.md
3. docs/project/P0_REVIEW_RECORD.md

当前已完成并推送到 main 的最新任务是 R1-31；R1-32～R1-36 已在本地由 Codex 收口并形成冻结提交，是否已推送需通过 git 状态确认。

请先执行：
git status --short
git log -1 --oneline

然后根据 PROJECT_HANDOFF_AUDIT_WORKFLOW.md 确认是否可以进入 P2，或是否需要先推送并观察 CI。
不要自动推送。
```

### 5.2 新对话给 Claude / CatPaw 的完整启动 Prompt

如果新对话让执行工具接手 P2，建议复制：

```text
你现在负责 CampusAgent 项目的 P2：基础设施与后端公共内核。

项目路径：
F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent

必须先阅读：
1. docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
2. docs/project/P0_P1_REMEDIATION_PLAN.md
3. docs/project/README.md

当前状态：
- R1-32～R1-36 已由 Codex 在本地完成收口并形成冻结提交；
- 最新已推送提交可能仍是 3f2ee03，是否已推送 R1-36 需先执行 git status / git log 确认；
- 远端 CI 是否绿色需在用户授权推送后观察；
- P2 执行前不得修改 P0/P1 冻结口径，除非先记录新审计问题。

任务目标：
按 `docs/development/DEVELOPMENT_PLAN.md` 中 P2 任务顺序，先从 Docker Compose、配置对象、PostgreSQL、Alembic、Redis 和 API Envelope 基线开始。

禁止：
- 不提交；
- 不推送；
- 未经批准不修改 P0/P1 冻结契约；
- 不修改 API 端点数量、WebSocket Schema、威胁数量、测试定义数量；
- 不新增测试 ID；
- 不把 `planned` 控制状态写成 `implemented` 或 `verified`。

完成后输出完整报告，等待 Codex 审计。
```

## 6. 任务执行指令模板

将下面模板复制给 Claude / CatPaw / GLM，并替换任务编号和内容。

```text
你现在负责 CampusAgent 项目的：

R1-XX：<任务名称>

项目目录：
F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent

前置条件：
1. <上一任务> 已通过 Codex 审计；
2. 当前权威状态以 docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md 为准；
3. 不提交，不推送，等待 Codex 审计。

==================================================
一、任务目标
==================================================

<说明本任务要达成什么结果>

验收要求：
1. <验收项 1>
2. <验收项 2>
3. <验收项 3>

==================================================
二、必须阅读
==================================================

请完整阅读：
1. docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
2. docs/project/P0_P1_REMEDIATION_PLAN.md
3. <本任务相关文档 1>
4. <本任务相关文档 2>

==================================================
三、执行范围
==================================================

允许修改：
- <文件或目录>

禁止修改：
- 业务代码，除非明确要求；
- API 端点数量，除非明确要求；
- WebSocket Schema，除非明确要求；
- 威胁数量、风险等级、控制状态，除非明确要求；
- 测试定义数量，除非明确要求。

==================================================
四、具体步骤
==================================================

1. <步骤 1>
2. <步骤 2>
3. <步骤 3>

==================================================
五、日志要求
==================================================

创建或更新：
development-logs/in-progress/R1-XX-<short-name>.md

front matter：
---
task_id: R1-XX
status: in_progress
stage: R1
title: <任务名称>
started_at: 2026-07-16TXX:XX:XX+08:00
completed_at:
estimated_hours: <估算小时>
actual_hours:
---

日志必须记录：
1. 修改文件；
2. 修改原因；
3. 自检命令；
4. 自检结果；
5. 未提交、未推送；
6. 等待 Codex 审计。

==================================================
六、自检要求
==================================================

必须执行：

git status --short
git diff HEAD --name-status
git diff HEAD --stat
git diff HEAD --check

根据任务额外执行：
rg -n "<关键字>" docs/ development-logs/

==================================================
七、完成报告格式
==================================================

请按以下格式报告：

1. 修改文件列表
2. 核心修改内容
3. 与权威文档的一致性
4. 自检命令和结果
5. 未修改范围说明
6. 后续任务是否保持未执行
7. git diff HEAD --check 结果
8. git status --short 摘要
9. 明确：未提交、未推送，等待 Codex 审计
```

## 7. Codex 审计模板

Codex 审计时，不要只相信执行工具报告。必须本地核验。

```text
请审计 R1-XX 的整改结果。

审计要求：
1. 先读取 docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md；
2. 读取 docs/project/P0_P1_REMEDIATION_PLAN.md；
3. 查看 git status 和 diff；
4. 根据任务目标核验关键统计、章节引用、路径引用、契约数量；
5. 检查是否越权修改业务代码或冻结契约；
6. 给出明确结论：
   - 审计通过，可以提交；
   - 或审计不通过，给出整改指令。

如果通过，请不要自动提交，等我明确说提交。
```

通用审计命令：

```powershell
git status --short
git diff HEAD --name-status
git diff HEAD --stat
git diff HEAD --check
```

常用搜索：

```powershell
rg -n "待补充|测试通过|已执行|已验证|0 个缺陷|完全覆盖|完全安全|verified|implemented" docs/ development-logs/
rg -n "PRIVACY_TEST_MATRIX.md §13|§13（追踪矩阵|§13（追踪矩阵，R1-30" docs/ development-logs/
rg -n "DATA_INVENTORY.md §13|数据保留策略矩阵" docs/ development-logs/
rg -n "68 MVP|3 internal|71" docs/api docs/project
```

审计判断：

- 当前有效正文不能把 `PRIVACY_TEST_MATRIX.md §13` 说成追踪矩阵；追踪矩阵是 §14。
- 历史变更记录可以保留当时的章节迁移描述，但不能作为当前权威口径。
- AuditLog metadata 必须是 180 天。
- 测试 `defined` 不代表已执行。
- 控制 `planned` 不代表已实现或已验证。
- R1-E 阶段若只修文档链接，不应修改业务代码。

### 7.1 标准审计流程

每次审计按以下顺序执行。

1. 确认 Git 状态：

```powershell
git status --short
git diff HEAD --name-status
git diff HEAD --stat
git diff HEAD --check
```

2. 确认只修改允许范围：

```powershell
git diff HEAD --name-only
```

审计判断：

- 如果任务是文档任务，出现 `apps/`、`packages/`、`tests/`、`infra/` 修改，需要重点追问；
- 如果出现临时文件 `.bak`、`.backup`、`.tmp`、`.copy`，要求清理；
- 如果出现未跟踪脚本，确认是否仅用于临时检查，通常不应提交。

3. 对任务关键口径做 `rg` 扫描。

4. 对统计类任务使用脚本或正则自动统计，不要手数。

5. 对日志类任务检查 front matter：

```yaml
task_id: R1-XX
status: in_progress 或 completed
stage: R1
title: ...
started_at: ...
completed_at:
estimated_hours:
actual_hours:
```

6. 检查任务勾选：

- 当前任务应为 `[x]`；
- 后续任务应为 `[ ]`；
- 不能提前勾选后续任务。

7. 给出结论：

- 审计通过：说明可提交，但不自动提交；
- 审计不通过：列问题和整改指令；
- 如果只是小问题：仍然不通过，除非用户授权 Codex 直接改。

### 7.2 审计结论格式

```text
审计结论：通过 / 不通过

关键核验：
1. Git 修改范围：
2. 任务状态：
3. 统计结果：
4. 权威口径：
5. 自检结果：

如通过：
可以提交本批修改。建议提交信息：
docs(project): <summary>

如不通过：
问题：
1. ...
2. ...

整改指令：
<复制给执行工具的完整指令>
```

### 7.3 常见审计红线

出现以下情况，一般直接判为不通过：

- 当前正文中出现“待补充”作为最终结果；
- 文档声称测试已执行、测试通过、0 缺陷，但实际只是定义；
- 将控制状态从 `planned` 升为 `implemented` 或 `verified`，但没有实现和验证证据；
- 修改冻结的 API / WebSocket 契约语义；
- 修改业务代码但任务只要求文档；
- 后续任务被提前勾选；
- 权威统计数字不一致；
- completed 日志中存在两份当前权威记录；
- in-progress 中残留已完成任务日志；
- 历史日志没有标注 historical，却与当前口径冲突。

### 7.4 R1-32 专用审计清单

R1-32 审计时，重点检查：

```powershell
git status --short
git diff HEAD --name-status
git diff HEAD --stat
git diff HEAD --check
```

日志归档：

```powershell
Get-ChildItem development-logs/in-progress
Get-ChildItem development-logs/completed/remediation-r1 | Select-String "R1-30|R1-31|R1-32"
```

章节引用：

```powershell
rg -n "PRIVACY_TEST_MATRIX\.md §13|§13（追踪矩阵|§13（追踪矩阵，R1-30" docs/ development-logs/
rg -n "PRIVACY_TEST_MATRIX\.md §14|§14（威胁|追踪矩阵" docs/ development-logs/
rg -n "DATA_INVENTORY.md §13|数据保留策略矩阵" docs/ development-logs/
```

回归统计：

```powershell
rg -n "正式测试定义总数|defined=100|not_run=100|planned=9|implemented=0|verified=0" docs/
rg -n "68 MVP|3 internal|71" docs/
rg -n "v1.0-frozen" docs/api/WEBSOCKET_CONTRACT.md
```

链接检查应报告：

- 扫描文件数；
- Markdown 链接数；
- 内部链接数；
- 修复前失效链接数；
- 修复后失效链接数；
- historical 例外数。

## 8. 提交与推送模板

只有在 Codex 审计通过且用户明确要求提交时执行。

提交前：

```powershell
git status --short
git diff HEAD --stat
git diff HEAD --check
```

提交：

```powershell
git add docs development-logs
git commit -m "docs(project): <summary>"
```

推送：

```powershell
git push origin main
```

如果 Codex 推送时遇到 SSH / known_hosts 权限问题，可使用提升权限重试 `git push origin main`。

提交后确认：

```powershell
git status --short
git log -1 --oneline
```

### 8.1 推荐提交信息

| 任务 | 推荐提交信息 |
|---|---|
| R1-32 | `docs(project): fix internal links for R1 handoff` |
| R1-33 | `docs(project): align P0 completion summary` |
| R1-34 | `docs(project): update P0 progress status` |
| R1-35 | `docs(project): record P0 manual review` |
| R1-36 | `docs(project): freeze P0 documentation` |

### 8.2 推送失败排查

如果 `git push` 报 SSH / known_hosts 权限问题：

1. 确认远程：

```powershell
git remote -v
```

2. 测试 GitHub SSH：

```powershell
ssh -T git@github.com
```

3. 在 Codex 沙箱中可能需要提升权限推送，因为真实用户的 SSH config、known_hosts、私钥在 `C:\Users\10481\.ssh\` 下。

4. 推送后确认：

```powershell
git status --short
git log -1 --oneline
```

## 9. R1-32 任务提示（历史留档）

本节为 2026-07-16 执行 R1-32 时使用的历史任务模板，保留用于追溯指令质量。当前 R1-32～R1-36 已完成，不应按本节重复执行。

核心要点：

- 归档 R1-30 / R1-31 日志到 `development-logs/completed/remediation-r1/`。
- 当前权威日志为 `development-logs/completed/remediation-r1/R1-32-fix-internal-links.md`。
- 检查 `docs/` 和 `development-logs/` 中 Markdown 内部链接、相对路径、锚点、章节号。
- 修复失效链接到 0。
- `P0_P1_REMEDIATION_PLAN.md` 中 R1-32 改为 `[x]`。
- 历史执行时 R1-33～R1-36 保持 `[ ]`。
- 当前 R1-E 已完成并进入本地冻结提交。

### 9.1 R1-32 详细执行指令

以下是当时可直接发送给执行工具的 R1-32 完整指令；当前仅作历史参考。

```text
你现在负责 CampusAgent 项目的：

R1-32：修复全部内部链接

项目目录：
F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent

前置条件：
1. R1-30、R1-31 已通过 Codex 审计并已推送；
2. 最新提交应为 3f2ee03 docs(security): define fail-closed and retention tests；
3. R1-32 尚未执行；
4. R1-33～R1-36 不得执行；
5. 不提交，不推送，等待 Codex 审计。

==================================================
一、任务目标
==================================================

修复 docs/ 和 development-logs/ 中所有当前有效文档的内部链接、相对路径、章节锚点、开发日志路径引用。

验收标准：
1. 当前有效 Markdown 内部链接失效数为 0；
2. 当前有效章节引用无错误章节号；
3. R1-30、R1-31 日志完成归档；
4. R1-32 创建当前任务日志；
5. P0_P1_REMEDIATION_PLAN.md 中 R1-32 标记为 [x]；
6. R1-33～R1-36 保持 [ ]；
7. 不修改业务代码、测试代码、API 端点、WebSocket Schema；
8. 测试定义仍为 100；
9. 威胁仍为 9；
10. 控制状态仍为 planned=9、implemented=0、verified=0。

==================================================
二、必须阅读
==================================================

1. docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md
2. docs/project/P0_P1_REMEDIATION_PLAN.md
3. docs/project/README.md
4. docs/security/THREAT_MODEL.md
5. docs/privacy/PRIVACY_TEST_MATRIX.md
6. docs/architecture/DATA_INVENTORY.md
7. docs/api/API_CONTRACT.md
8. docs/api/WEBSOCKET_CONTRACT.md
9. development-logs/in-progress/R1-30-check-privacy-fail-closed.md
10. development-logs/in-progress/R1-31-review-retention-policy.md

==================================================
三、日志归档
==================================================

将：
development-logs/in-progress/R1-30-check-privacy-fail-closed.md

移动到：
development-logs/completed/remediation-r1/R1-30-check-privacy-fail-closed.md

将：
development-logs/in-progress/R1-31-review-retention-policy.md

移动到：
development-logs/completed/remediation-r1/R1-31-review-retention-policy.md

修改 front matter：
status: completed
completed_at: 2026-07-16TXX:XX:XX+08:00
actual_hours: 填合理值

不得删除 Codex 审计整改记录。

==================================================
四、新建 R1-32 日志
==================================================

新建：
development-logs/in-progress/R1-32-fix-internal-links.md

> 历史说明：该日志在 R1-36 收口时已归档为 `development-logs/completed/remediation-r1/R1-32-fix-internal-links.md`。

front matter：
---
task_id: R1-32
status: in_progress
stage: R1
title: 修复全部内部链接
started_at: 2026-07-16TXX:XX:XX+08:00
completed_at:
estimated_hours: 2
actual_hours:
---

日志记录：
1. 检查范围；
2. 检查方法；
3. 修复前失效链接数；
4. 修复后失效链接数；
5. historical 例外数；
6. 修改文件；
7. 自检结果；
8. 未提交、未推送。

==================================================
五、检查范围
==================================================

扫描：
docs/**/*.md
development-logs/**/*.md

检查：
1. Markdown 链接路径；
2. 带 #anchor 的章节链接；
3. 裸路径引用；
4. development-logs 当前权威日志路径；
5. historical 日志标注；
6. 章节号引用。

忽略：
1. http://
2. https://
3. mailto:
4. git@
5. 代码块中的示例链接，除非明显是项目文档引用。

==================================================
六、当前权威章节
==================================================

PRIVACY_TEST_MATRIX.md：
- §12：FC 测试定义
- §13：RT 测试定义
- §14：威胁—控制—测试追踪矩阵
- §15：测试执行要求
- §16：相关文档

DATA_INVENTORY.md：
- §13：数据保留策略矩阵（R1-31 权威口径）

WEBSOCKET_CONTRACT.md：
- v1.0-frozen

API_CONTRACT.md：
- 68 MVP HTTP + 3 internal = 71

==================================================
七、自检命令
==================================================

必须执行：

git status --short
git diff HEAD --name-status
git diff HEAD --stat
git diff HEAD --check

章节引用：

rg -n "PRIVACY_TEST_MATRIX\\.md §13|§13（追踪矩阵|§13（追踪矩阵，R1-30" docs/ development-logs/
rg -n "PRIVACY_TEST_MATRIX\\.md §14|§14（威胁|追踪矩阵" docs/ development-logs/
rg -n "DATA_INVENTORY.md §13|数据保留策略矩阵" docs/ development-logs/

回归：

rg -n "正式测试定义总数|defined=100|not_run=100" docs/
rg -n "planned=9|implemented=0|verified=0" docs/
rg -n "68 MVP|3 internal|71" docs/
rg -n "v1.0-frozen" docs/api/WEBSOCKET_CONTRACT.md

==================================================
八、完成报告
==================================================

按以下格式报告：

1. 修改文件列表；
2. R1-30/R1-31 日志归档结果；
3. R1-32 当前日志路径；
4. 链接检查方法；
5. 修复前失效链接数量；
6. 修复后失效链接数量；
7. 修复的主要链接/章节引用；
8. historical 例外说明；
9. P0_P1_REMEDIATION_PLAN.md 更新结果；
10. R1-33～R1-36 是否保持未执行；
11. 回归检查结果；
12. git diff HEAD --check 结果；
13. git status --short 摘要；
14. 明确：未提交、未推送，等待 Codex 审计。
```

## 10. 最容易出错的点

1. 把历史记录当成当前口径。
2. 章节重排后忘记更新引用。
3. 把测试定义写成测试通过。
4. 把 planned 控制写成 implemented / verified。
5. 忘记归档已完成任务日志。
6. completed 中出现两份当前权威日志。
7. historical 日志没有标注历史状态。
8. 文档任务误改业务代码。
9. API / WebSocket 已冻结后仍随意修改契约。
10. 提交前没有运行 `git diff HEAD --check`。

## 11. 常用命令速查

### 11.1 进入项目

Windows PowerShell：

```powershell
cd "F:\工作盘\实习经历汇总\星星之火-创业\模型互联网比赛\CampusAgent"
```

WSL：

```bash
cd /root/CampusAgent
```

### 11.2 Git 状态

```powershell
git status --short
git log -1 --oneline
git diff HEAD --name-status
git diff HEAD --stat
git diff HEAD --check
```

### 11.3 搜索

```powershell
rg -n "关键词" docs/ development-logs/
rg --files docs development-logs
```

### 11.4 Conda 环境

```powershell
conda activate CampusAgent
```

### 11.5 SSH / WSL 连接

```powershell
ssh Ubuntu2-Codex
ssh -o BatchMode=yes -o ConnectTimeout=10 Ubuntu2-Codex "echo SSH_OK; hostname; whoami; uname -a"
```

如果失败：

```powershell
ssh -G Ubuntu2-Codex
Test-NetConnection 127.0.0.1 -Port 2222
netstat -ano | findstr :2222
```

进入 WSL 后启动 SSH：

```bash
sudo service ssh start
```

## 12. 文档权威优先级

当文档冲突时，按以下优先级判断：

1. 当前任务的权威契约章节；
2. `P0_P1_REMEDIATION_PLAN.md` 的任务勾选和退出条件；
3. `P0_REVIEW_RECORD.md` 的复审记录；
4. 具体领域权威文档：
   - API：`API_CONTRACT.md`
   - WebSocket：`WEBSOCKET_CONTRACT.md`
   - 威胁：`THREAT_MODEL.md`
   - 测试：`PRIVACY_TEST_MATRIX.md`
   - 数据保留：`DATA_INVENTORY.md §13`
   - 权限：`PERMISSION_MATRIX.md`
5. 完成总结；
6. 历史日志。

历史日志只能解释“当时为什么这么做”，不能推翻当前权威口径。

## 13. 新对话最小恢复清单

如果时间很紧，新对话至少要让 Codex 做这几件事：

```text
1. 读取 docs/project/PROJECT_HANDOFF_AUDIT_WORKFLOW.md；
2. 读取 docs/project/P0_P1_REMEDIATION_PLAN.md；
3. 执行 git status --short；
4. 执行 git log -1 --oneline；
5. 确认最新提交是否为 3f2ee03；
6. 确认当前任务是否为 R1-32；
7. 不提交、不推送，除非我明确要求。
```
