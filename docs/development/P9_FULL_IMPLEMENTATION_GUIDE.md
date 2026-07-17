# P9 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P9「宿舍聚餐协商完整闭环」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P9-01～P9-17；不得跳任务、不得执行 P10+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。

## 0. 项目背景

P9 前置条件：

- P8 已由 Codex 审计、修复、提交、推送，远端 CI 绿色。
- 如果 P8 未提交或工作树不干净，停止并报告。

P9 是比赛主线 Demo：

- 宿舍四人聚餐协商。
- 必须可离线运行。
- 必须 deterministic。
- 模型关闭时仍可用规则路径完成。
- 模型只能润色非敏感结构化结果。
- 私有偏好不得暴露给群主、管理员、其他成员、WebSocket、日志或模型 prompt。

## 1. 必读文件

1. `docs/development/P8-COMPLETION-REPORT.md`
2. `docs/api/API_CONTRACT.md`
3. `docs/privacy/PRIVACY_TEST_MATRIX.md`
4. `docs/security/THREAT_MODEL.md`
5. `apps/api/src/modules/scenes/`
6. `apps/api/src/modules/model_gateway/`
7. `apps/api/src/modules/memories/`
8. `apps/api/src/modules/conversations/`
9. `apps/api/src/modules/organizations/`

## 2. 文件结构规划

后端：

```text
apps/api/src/modules/scenes/plugins/dorm_dinner/__init__.py
apps/api/src/modules/scenes/plugins/dorm_dinner/schema.py
apps/api/src/modules/scenes/plugins/dorm_dinner/privacy.py
apps/api/src/modules/scenes/plugins/dorm_dinner/restaurants.py
apps/api/src/modules/scenes/plugins/dorm_dinner/capsule.py
apps/api/src/modules/scenes/plugins/dorm_dinner/algorithm.py
apps/api/src/modules/scenes/plugins/dorm_dinner/reasons.py
apps/api/src/modules/scenes/plugins/dorm_dinner/plugin.py
apps/api/src/modules/scenes/plugins/dorm_dinner/api.py
```

前端：

```text
apps/web/src/app/scenes/dorm-dinner/page.tsx
apps/web/src/app/scenes/dorm-dinner/[sceneInstanceId]/page.tsx
apps/web/src/lib/dormDinner.ts
```

测试：

```text
apps/api/tests/unit/test_dinner_schema.py
apps/api/tests/unit/test_dinner_privacy_policy.py
apps/api/tests/unit/test_dinner_capsule.py
apps/api/tests/unit/test_dinner_restaurants.py
apps/api/tests/unit/test_dinner_candidate_generation.py
apps/api/tests/unit/test_dinner_private_evaluation.py
apps/api/tests/unit/test_dinner_aggregation.py
apps/api/tests/unit/test_dinner_public_reasons.py
apps/api/tests/unit/test_dinner_model_enhancement.py
apps/api/tests/unit/test_dinner_api.py
apps/api/tests/unit/test_dinner_memory_confirmation.py
apps/api/tests/unit/test_dinner_cleanup.py
apps/api/tests/integration/test_dinner_e2e_privacy.py
```

## 3. P9-01 输入 Schema

字段：

- `budget_min`
- `budget_max`
- `cuisine_preferences`
- `dietary_restrictions`
- `distance_preference`
- `available_time`
- `environment_preference`
- `notes`

校验：

- budget_min >= 0。
- budget_max >= budget_min。
- cuisine enum。
- distance enum。
- environment enum。
- notes 最大长度 500。
- notes 可为空。
- notes 中的提示注入只作为普通私有文本，不进入模型。

## 4. P9-02 披露策略

字段分类：

| 字段 | 分类 | 公开策略 |
|---|---|---|
| budget_min/max | aggregate_only | 可区间化 |
| cuisine_preferences | category_disclosable | 可汇总 |
| dietary_restrictions | aggregate_only | 不指认成员 |
| distance_preference | aggregate_only | 可汇总 |
| available_time | aggregate_only | 可交集 |
| environment_preference | category_disclosable | 可汇总 |
| notes | never_disclose | 不公开、不入模型 |

测试必须证明：

- notes 不进入 public result。
- notes 不进入 prompt。
- notes 不进入 message。

## 5. P9-03 输入校验

测试：

- budget 非法。
- 时间非法。
- enum 非法。
- notes 超长。
- injection text 不执行。
- 空偏好仍可生成保守 capsule。

## 6. P9-04 偏好胶囊

capsule 包含：

- hard_constraints。
- soft_preferences。
- weights。
- allowed_reason_codes。

capsule 不包含：

- notes 原文。
- email。
- student_no。
- user display_name。
- memory content。

## 7. P9-05 最小化验证

必须写测试：

- 自由文本不离开 private submission。
- budget 被区间化。
- dietary restriction 不指认成员。
- 不生成心理/经济推断标签。

## 8. P9-06 餐厅数据

创建至少 8 个虚构餐厅：

- name。
- cuisine。
- price_min/max。
- distance_minutes。
- capacity。
- noise_level。
- tags。
- deterministic id。

禁止使用真实商家数据。

## 9. P9-07 候选生成

规则：

- 只用公共上下文 + capsules。
- 不使用 raw private input。
- 至少 3 个候选。
- 若 hard constraints 全拒，返回安全空状态。

## 10. P9-08 私有候选评价

每个 participant 对每个候选生成：

- hard_pass。
- utility。
- objections。
- reason_codes。

该评价不公开。

## 11. P9-09 确定性聚合

算法顺序：

1. hard gate。
2. mean utility。
3. fairness penalty。
4. distance score。
5. budget score。
6. stable sort by deterministic id。

测试：

- 同输入同结果。
- participants 顺序变化结果不变。
- 平分稳定。
- 极端权重稳定。

## 12. P9-10 安全公共理由

理由只能来自 allowlist：

- `matches_common_cuisine`
- `within_group_budget`
- `reasonable_distance`
- `fits_shared_time`
- `balanced_tradeoff`

禁止：

- “因为张三预算低”。
- “有人不能吃辣”并指认。
- “某成员经济压力大”。
- 输出 notes 原文。

## 13. P9-11 模型增强

模型输入只能包含：

- restaurant name。
- aggregate score。
- allowlisted reason codes。
- public tags。

模型不能看到：

- raw preferences。
- capsules with user id。
- private evaluations。
- notes。

失败：

- 使用 rule text。

## 14. P9-12 场景 API

实现或接入：

- create。
- participate。
- grant consent。
- submit private preference。
- start candidate generation。
- get candidates。
- vote。
- confirm。
- cancel。

所有写端点：

- auth。
- CSRF。
- participant 权限。

## 15. P9-13 群聊场景卡

消息中只展示：

- phase。
- progress。
- privacy notice。
- candidate summary。
- vote action。
- final result。

不展示：

- raw preference。
- capsule。
- private evaluation。

## 16. P9-14 长期记忆二次确认

默认：

- 不保存偏好到 Memory。

确认后：

- 写入明确 category。
- 明确 source。
- 可撤销 consent。

## 17. P9-15 清理验证

完成/取消/过期后清理：

- raw input。
- capsule。
- private evaluation。
- intermediate model response。

测试：

- DB query 证明清理。
- API 读不到。
- cleanup 重复执行安全。

## 18. P9-16 算法测试

覆盖：

- hard constraints。
- 平分。
- 极端权重。
- fairness。
- stable order。
- empty candidates。
- all hard pass。

## 19. P9-17 端到端隐私测试

覆盖：

- A 看不到 B。
- 群主看不到成员私有偏好。
- 管理员看不到。
- 日志无正文。
- WebSocket 无正文。
- 导出无正文。
- TTL 后清理。

## 20. 前端页面

页面：

- `/scenes/dorm-dinner`
- `/scenes/dorm-dinner/[sceneInstanceId]`

要求：

- 创建聚餐场景。
- 邀请/展示参与者。
- 隐私说明。
- 私有偏好表单。
- 候选展示。
- 投票。
- 确认。
- 结果页。
- 不保存私有偏好到 localStorage。

## 21. 文档和报告

新增：

- `docs/development/P9-COMPLETION-REPORT.md`
- P9-01～P9-17 logs。

更新：

- `docs/development/DEVELOPMENT_PLAN.md`
- P9 `[x]`。
- P10 未开始。

完成报告必须包含：

- 输入 schema。
- 披露策略。
- 胶囊示例。
- 算法说明。
- 模型增强边界。
- 清理证明。
- E2E 隐私测试结果。

## 22. 全量验证

```bash
git status --short --branch
git diff HEAD --check
conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
conda run -n CampusAgent pip check
conda run -n CampusAgent ruff check apps/api --no-cache
conda run -n CampusAgent mypy apps/api/src apps/api/tests --no-incremental
conda run -n CampusAgent python -m pytest apps/api/tests -q -p no:cacheprovider
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm --filter @campus-agent/web build
if [ -x /tmp/gitleaks ]; then /tmp/gitleaks detect --source . --config .gitleaks.toml --gitleaks-ignore-path .gitleaksignore --redact --verbose --no-banner; fi
```

不要提交，不要推送。
