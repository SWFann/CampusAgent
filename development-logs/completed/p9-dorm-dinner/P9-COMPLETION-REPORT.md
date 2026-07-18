---
task_id: P9-01..P9-17
task_name: 宿舍聚餐协商完整闭环
status: complete
started_at: 2026-07-18T00:00:00+08:00
completed_at: 2026-07-18T18:30:00+08:00
actual_hours: 10
owner: Claude
auditor: pending
---

# P9: 宿舍聚餐协商完整闭环 — 完成报告

## 概述

P9 阶段实现了比赛唯一的可执行场景——宿舍聚餐协商完整闭环。从输入校验、
偏好胶囊、候选生成、私有评价、确定性聚合到安全公共理由和模型增强，
全部通过确定性规则保证可复现，模型仅用于非敏感结果润色。

核心隐私契约：**原始偏好不离开私有域，公共结果不含可指认成员的信息，
场景结束后所有 P4 数据被清理**。

## 任务完成清单

| ID | 任务 | 状态 |
|---|---|---|
| P9-01 | 冻结聚餐输入 Schema | ✅ schema.py (预算、菜系、禁忌、距离、时间、环境、备注) |
| P9-02 | 定义披露策略 | ✅ privacy.py (FIELD_DISCLOSURE_POLICY: NEVER_DISCLOSE/AGGREGATE_ONLY/CATEGORY_DISCLOSE) |
| P9-03 | 实现输入校验 | ✅ schema.py (范围、时区、长度、枚举、危险输入、budget_min≤budget_max) |
| P9-04 | 实现偏好胶囊 | ✅ capsule.py (硬约束、软偏好、权重、允许理由码) |
| P9-05 | 验证最小化 | ✅ capsule.py (自由文本不离开私有域、预算区间化、敏感推断禁止) |
| P9-06 | 建立 8+ 餐厅数据 | ✅ restaurants.py (10 家虚构餐厅、确定性 seed) |
| P9-07 | 实现候选生成 | ✅ algorithm.py (公开上下文筛选、≥3 项候选、无外网依赖) |
| P9-08 | 实现私有候选评价 | ✅ algorithm.py (hard pass、utility、objection、reason codes) |
| P9-09 | 实现确定性聚合 | ✅ algorithm.py (hard gate、均值、公平性、距离、预算、稳定排序) |
| P9-10 | 实现安全公共理由 | ✅ reasons.py (allowlist 映射、不指认成员、不暴露阈值/心理/经济标签) |
| P9-11 | 接入模型增强 | ✅ model_enhancement.py (仅润色结构化非敏感结果、失败使用规则文本) |
| P9-12 | 实现场景 API | ✅ plugin.py + scenes/api.py (创建、参与、授权、提交、开始、候选、投票、确认、取消) |
| P9-13 | 实现群聊场景卡 | ✅ scenes/events.py + conversations/models.py (SCENE_CARD 消息类型、阶段/进度/隐私说明) |
| P9-14 | 实现长期记忆二次确认 | ✅ plugin.py (默认不保存、确认后才写入明确类别) |
| P9-15 | 验证场景清理 | ✅ plugin.py + scenes/cleanup.py (原始输入、胶囊、私有评价、中间响应均清理) |
| P9-16 | 完成算法测试 | ✅ 12 个单元测试文件、238 个测试用例 |
| P9-17 | 完成端到端隐私测试 | ✅ 1 个集成测试文件、9 个 E2E 隐私测试用例 |

## 修改/新增文件列表

### 后端源码 (apps/api/src/modules/scenes/plugins/dorm_dinner/)
| 文件 | 行数 | 说明 |
|---|---|---|
| `__init__.py` | 18 | 包初始化，导出 DormDinnerPlugin |
| `schema.py` | 246 | P9-01/03: DinnerPreferenceInput、Cuisine/DietaryRestriction/DistancePreference/EnvironmentPreference/TimeSlot 枚举、输入校验 |
| `privacy.py` | 247 | P9-02: FIELD_DISCLOSURE_POLICY、DisclosureLevel、sanitize_for_public、check_privacy_leakage |
| `capsule.py` | 189 | P9-04/05: PrivateCapsule 构建、硬约束提取、软偏好权重、最小化验证 |
| `restaurants.py` | 338 | P9-06: 10 家虚构餐厅数据、to_candidate_metadata、确定性 seed |
| `algorithm.py` | 554 | P9-07/08/09: 候选生成、私有评价（utility 5 维评分）、确定性聚合（hard gate + 公平性 + 稳定排序） |
| `reasons.py` | 117 | P9-10: REASON_CODE_ALLOWLIST、validate_reason_codes、check_reason_for_leaks |
| `model_enhancement.py` | 175 | P9-11: enhance_public_summary、build_model_prompt、安全响应 schema、失败回退 |
| `plugin.py` | 197 | P9-12/14/15: DormDinnerPlugin（ScenePlugin 实现、生命周期管理、记忆二次确认、清理） |
| **合计** | **2081** | |

### 修改的后端源码
| 文件 | 说明 |
|---|---|
| `apps/api/src/main.py` | 注册 DormDinnerPlugin 到场景注册表 |
| `apps/api/src/modules/scenes/privacy.py` | 修复 mypy no-any-return（cast） |
| `apps/api/src/modules/scenes/coordinator.py` | 修复 mypy no-any-return（cast） |
| `apps/api/src/modules/scenes/service.py` | 修复 mypy no-any-return（cast） |

### 测试文件 (apps/api/tests/)
| 文件 | 测试数 | 说明 |
|---|---|---|
| `tests/unit/test_dinner_schema.py` | 26 | P9-01/03: Schema 校验（范围、枚举、默认值、危险输入） |
| `tests/unit/test_dinner_privacy_policy.py` | 30 | P9-02/16: 披露策略、脱敏、泄露检测 |
| `tests/unit/test_dinner_capsule.py` | 25 | P9-04/05/16: 胶囊构建、硬约束、权重、最小化 |
| `tests/unit/test_dinner_restaurants.py` | 23 | P9-06: 餐厅数据、候选元数据 |
| `tests/unit/test_dinner_candidate_generation.py` | 16 | P9-07/16: 候选生成、筛选、≥3 项保证 |
| `tests/unit/test_dinner_private_evaluation.py` | 22 | P9-08/16: 私有评价、utility、hard pass、objection |
| `tests/unit/test_dinner_aggregation.py` | 25 | P9-09/16: 聚合、公平性、稳定排序、hard gate |
| `tests/unit/test_dinner_public_reasons.py` | 31 | P9-10/16: 安全理由、allowlist、泄露检测 |
| `tests/unit/test_dinner_model_enhancement.py` | 20 | P9-11: 模型增强、失败回退、泄露检测 |
| `tests/unit/test_dinner_api.py` | 5 | P9-12: 场景 API 全生命周期 |
| `tests/unit/test_dinner_memory_confirmation.py` | 8 | P9-14: 记忆二次确认、默认不保存 |
| `tests/unit/test_dinner_cleanup.py` | 7 | P9-15: 清理原始输入、胶囊、私有评价 |
| `tests/integration/test_dinner_e2e_privacy.py` | 9 | P9-17: E2E 隐私（A/B 隔离、管理员拒绝、日志、WebSocket） |
| **合计** | **247** | |

## 设计要点

### 1. 确定性保证
- 相同输入始终产生相同输出（无随机数、无时间戳依赖）
- 参与者顺序不影响结果（排序后处理）
- 平局按确定性餐厅 ID 打破
- 算法无需任何模型调用即可运行（模型仅用于可选润色）

### 2. 隐私分层
- **NEVER_DISCLOSE**: notes（自由文本）、budget_exact（精确预算）
- **AGGREGATE_ONLY**: budget_min/max（区间化后可聚合）
- **CATEGORY_DISCLOSE**: cuisine/dietary/environment/time/distance（类别级可披露）
- 公共理由只使用 allowlist 中的代码，不指认成员、不暴露阈值

### 3. 评价维度（Utility 5 维）
| 维度 | 权重 | 说明 |
|---|---|---|
| 菜系匹配 | 0.30 | 参与者偏好 vs 餐厅菜系 |
| 预算适配 | 0.25 | 参与者预算区间 vs 餐厅价格 |
| 距离匹配 | 0.15 | 参与者距离偏好 vs 餐厅距离 |
| 环境匹配 | 0.15 | 参与者环境偏好 vs 餐厅环境 |
| 时间匹配 | 0.15 | 参与者时间偏好 vs 餐厅时段 |

### 4. 聚合公平性
- Hard gate：任一参与者 hard fail → 候选得分归零
- Fairness penalty：得分方差越大，惩罚越重
- Distance bonus：近距离餐厅小幅加分
- Budget bonus：价格区间紧凑的餐厅小幅加分
- 最终得分 clamp 到 [0, 1]

### 5. 模型增强安全
- 仅发送结构化非敏感数据（餐厅名、菜系、价格区间）
- 响应必须通过严格 schema 验证（summary 字段、≤200 字符）
- 泄露检测：检查增强文本是否包含禁止模式
- 任何失败均回退到规则文本

### 6. 场景清理
- 原始偏好输入 → 删除
- 私有胶囊 → 删除
- 私有评价结果 → 删除
- 模型中间响应 → 不保存（只存哈希）
- 立即清理 + 24h 兜底清理

## 验证结果

| 命令 | 结果 |
|---|---|
| `ruff check src/ tests/` | All checks passed! |
| `mypy src/modules/scenes/` | Success: no issues found in 26 source files |
| `mypy src/modules/scenes/plugins/dorm_dinner/` | Success: no issues found in 9 source files |
| `pytest` (全套) | **1247 passed** in 106.18s |
| `pytest` (P9 专项 13 文件) | **247 passed** in 1.59s |

## 隐私验证矩阵

| 场景 | 测试覆盖 | 结果 |
|---|---|---|
| 原始偏好不离开私有域 | test_notes_never_in_capsule | ✅ |
| 预算可区间化 | test_budget_range_extracted | ✅ |
| 敏感推断禁止 | test_no_sensitive_inference | ✅ |
| 公共理由不指认成员 | test_reasons_no_member_identification | ✅ |
| 公共理由不暴露阈值 | test_reasons_no_threshold_exposure | ✅ |
| 公共理由不含心理/经济标签 | test_reasons_no_psychological_labels | ✅ |
| 模型增强不含原始偏好 | test_model_prompt_no_preferences | ✅ |
| 模型增强失败回退 | test_fallback_to_rule_summary | ✅ |
| 增强文本泄露检测 | test_enhanced_text_leak_check | ✅ |
| A 看不到 B 的偏好 | test_e2e_ab_isolation | ✅ |
| 群主无法查看偏好 | test_e2e_owner_denied | ✅ |
| 管理员无法查看偏好 | test_e2e_admin_denied | ✅ |
| 日志不含偏好正文 | test_e2e_log_no_preferences | ✅ |
| WebSocket 事件无私有字段 | test_e2e_websocket_safe | ✅ |
| 场景结束后数据已清理 | test_e2e_cleanup_verified | ✅ |
| 记忆默认不保存 | test_memory_default_no_save | ✅ |
| 记忆确认后写入 | test_memory_confirm_then_save | ✅ |
| 确定性排序 | test_deterministic_ordering | ✅ |
| 公平性惩罚 | test_fairness_penalty | ✅ |
| Hard gate 归零 | test_hard_gate_zero_score | ✅ |

## 边界声明
- 未修改 P0-P8 冻结契约
- 模型增强仅使用 P0（公开）数据分类
- 未引入真实外部模型（保留 Mock/Rule 备用路径）
- 预存 mypy 错误（25 个 `no-untyped-def`）不在 P9 范围内，分布于 memories/api.py、agents/api.py、main.py 等模块
- 未提交、未推送（等待用户审核）
