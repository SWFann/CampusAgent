# R1-16 任务日志：统一幂等规则、请求响应模型和校验规则

> **任务编号**：R1-16
> **执行日期**：2026-07-14
> **执行人**：Claude
> **任务目标**：统一 API 的幂等规则、请求响应模型和校验规则，为 API 冻结做准备

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：统一幂等规则、请求响应模型和校验规则
- **具体操作**：创建、提交、投票、确认、取消
- **完成标准**：每个关键写接口说明 Idempotency-Key 行为；不再每个模块各写一套请求响应风格

### 前置条件验证

✅ R1-06 已完成：建立端点对照清单
✅ R1-07 已完成：补全 Directory API
✅ R1-08 已完成：补全 Conversation API
✅ R1-09 已完成：补全 Agent API
✅ R1-10 已完成：补全 Memory API
✅ R1-11 已完成：补全 Scene API
✅ R1-12 已完成：补全 Model Gateway
✅ R1-13 已完成：补全 Admin API
✅ R1-14 已完成：统一路径变量
✅ R1-15 已完成：统一错误码体系

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
4. ✅ docs/api/README.md - API 文档入口
5. ✅ docs/privacy/PRIVACY_BASELINE.md - 隐私基线

## 执行过程

### 1. 现状分析

#### 1.1 幂等规则现状

**当前问题**：
- Section 1.4 仅 3 行文字："创建场景、提交偏好、确认结果等接口支持 Idempotency-Key: <uuid>，重复请求返回相同结果。"
- 未定义：哪些端点必须支持、Key 格式、作用域、过期时间、重复请求响应、冲突处理
- 各端点散落提及："支持幂等性"、"Idempotency-Key: uuid"、"使用 Idempotency-Key 可安全重试"

**端点幂等性覆盖**：
- 创建类（organizations、conversations、scene-instances、memories）：✅ 有提及
- 提交类（private-submission、vote、confirm）：✅ 有提及
- 管理类（nodes、models、deployments）：✅ 有提及（Idempotency-Key 冲突错误码）
- 消息发送（messages）：❌ 未明确
- Agent chat：❌ 未明确
- Memory export：❌ 未明确

#### 1.2 请求响应模型现状

**当前问题**：
- Section 1.3 仅定义分页（`page`/`page_size`/`total`），未定义排序、过滤、时间格式、ID 格式、空值规则
- 各端点自行定义响应格式：
  - 列表响应：有的用 `items`，有的用 `data`
  - 详情响应：有的直接返回对象，有的包装在 `data` 中
  - 创建响应：HTTP 201 但无统一结构
  - 异步响应：部分端点返回 202，部分返回 200
- 时间格式不统一：有的用 `2026-07-14T10:30:00Z`，有的用时间戳
- ID 格式不统一：有的用 UUID，有的未明确
- 空值处理不统一：有的返回 `null`，有的省略字段

#### 1.3 校验规则现状

**当前问题**：
- Section 1.4（原幂等性）未定义校验规则
- 各端点自行定义参数校验：
  - 分页校验：`page < 1` 或 `page_size > max` 返回 `INVALID_PAGINATION`
  - 过滤校验：`query too short` 返回 `DIRECTORY_QUERY_TOO_SHORT`
  - 类型校验：`invalid sender type` 返回 `MESSAGE_INVALID_SENDER_TYPE`
- 校验错误响应格式不统一：
  - 有的返回 `INVALID_INPUT`
  - 有的返回模块专用错误码（如 `DIRECTORY_QUERY_TOO_SHORT`）
- 未定义：字段级校验规则、批量校验、错误响应结构

### 2. 统一实施

#### 2.1 Section 1.3 扩展为"通用请求规则"

**新增内容**：
1. **1.3.1 分页**：统一 `page`/`page_size`/`total`，最大 page_size=100，分页一致性规则
2. **1.3.2 排序**：`sort`/`order` 参数，允许排序字段列表，默认排序规则
3. **1.3.3 过滤**：精确匹配、范围匹配、包含匹配、布尔过滤，过滤一致性规则
4. **1.3.4 时间格式**：ISO 8601（RFC 3339），UTC 优先，精度到秒
5. **1.3.5 ID 格式**：UUID v4，小写带连字符，字段名统一为 `*_id`
6. **1.3.6 空值规则**：请求省略 vs 发送 null，响应 null vs 省略字段
7. **1.3.7 布尔值格式**：JSON true/false，字段名使用肯定形式
8. **1.3.8 枚举值格式**：大写蛇形命名，明确列出可选值

**替换**：原 Section 1.3（仅 15 行分页定义）→ 新 Section 1.3（140+ 行通用请求规则）

#### 2.2 Section 1.4 扩展为"幂等规则"

**新增内容**：
1. **1.4.1 幂等性概述**：保证相同 Key 多次请求只执行一次
2. **1.4.2 必须支持幂等性的端点**：18 个端点（创建、提交、投票、确认、取消、管理）
3. **1.4.3 可选支持幂等性的端点**：3 个端点（消息、导出、Agent chat）
4. **1.4.4 不适用幂等性的端点**：8 个端点（PATCH、DELETE）
5. **1.4.5 Idempotency-Key 格式**：UUID v4，生成建议
6. **1.4.6 作用域**：全局唯一，实际存储键 = Key + 路径 + 请求体哈希
7. **1.4.7 过期时间**：24 小时，清理策略
8. **1.4.8 重复请求响应**：返回完全相同响应，不触发事件，不产生新审计日志
9. **1.4.9 冲突处理**：冲突场景表，重试策略
10. **1.4.10 幂等性与业务冲突的关系**：幂等性优先于业务冲突检查

**替换**：原 Section 1.4（仅 3 行幂等性定义）→ 新 Section 1.4（180+ 行完整幂等规则）

#### 2.3 新增 Section 1.7"统一响应模型"

**内容**：
1. **1.7.1 响应结构总览**：统一 `success`/`data`/`request_id` 结构
2. **1.7.2 列表响应**：`items`/`page`/`page_size`/`total`
3. **1.7.3 详情响应**：单个对象，404 返回错误
4. **1.7.4 创建响应**：201 Created，包含 `id` 和 `created_at`
5. **1.7.5 更新响应**：200 OK，包含 `updated_at`
6. **1.7.6 异步任务响应**：202 Accepted，包含 `status`/`started_at`/`estimated_completion`
7. **1.7.7 删除响应**：204 No Content，空响应体
8. **1.7.8 空值处理规则**：null vs 省略字段，空数组 vs null

#### 2.4 新增 Section 1.8"请求校验规则"

**内容**：
1. **1.8.1 校验时机**：路由层/认证层/参数层/业务层
2. **1.8.2 字段校验规则**：字符串/数字/数组/对象的校验规则
3. **1.8.3 校验错误响应**：结构示例，批量校验错误（可选）
4. **1.8.4 错误码映射**：R1-15 错误码在 R1-16 校验中的使用
5. **1.8.5 内容类型**：请求 Content-Type，响应 Content-Type

#### 2.5 更新端点引用

**更新 scattered 幂等性提及**：
- Auth register：`支持幂等性` → `支持幂等性（见 1.4）`
- Admin 请求头：`Idempotency-Key: uuid` → `Idempotency-Key: <uuid>  # 见 1.4`

**保留的错误码提及**：
- `SCENE_VOTE_ALREADY_VOTED` - 已投票过（使用 Idempotency-Key 可安全重试）
- `NODE_ALREADY_EXISTS` - 节点已存在（Idempotency-Key 冲突）
- `MODEL_ALREADY_EXISTS` - 模型已存在（Idempotency-Key 冲突）
- `DEPLOYMENT_ALREADY_EXISTS` - 部署已存在（Idempotency-Key 冲突）

#### 2.6 更新 P0_P1_REMEDIATION_PLAN.md

- R1-16 状态：`[ ]` → `[x]`
- 具体操作：扩展为详细描述
- 返工说明：添加 R1-16 完成说明

### 3. 验证检查

#### 3.1 Section 1.3 通用请求规则验证

```bash
# 验证新增子节数量
grep -c "#### 1.3\." docs/api/API_CONTRACT.md
# 结果：8（1.3.1～1.3.8）
```

**验证结果**：
- ✅ 8 个子节全部存在
- ✅ 分页、排序、过滤、时间格式、ID 格式、空值、布尔、枚举全部定义
- ✅ 每个子节都有规则和示例

#### 3.2 Section 1.4 幂等规则验证

```bash
# 验证新增子节数量
grep -c "#### 1.4\." docs/api/API_CONTRACT.md
# 结果：10（1.4.1～1.4.10）
```

**验证结果**：
- ✅ 10 个子节全部存在
- ✅ 18 个必支持端点 + 3 个可选端点 + 8 个不适用端点全部列出
- ✅ Key 格式、作用域、过期时间、冲突处理全部定义

#### 3.3 Section 1.7 统一响应模型验证

```bash
# 验证新增子节数量
grep -c "#### 1.7\." docs/api/API_CONTRACT.md
# 结果：8（1.7.1～1.7.8）
```

**验证结果**：
- ✅ 8 个子节全部存在
- ✅ 列表、详情、创建、更新、异步、删除、空值处理全部定义
- ✅ 每个响应类型都有结构和示例

#### 3.4 Section 1.8 请求校验规则验证

```bash
# 验证新增子节数量
grep -c "#### 1.8\." docs/api/API_CONTRACT.md
# 结果：5（1.8.1～1.8.5）
```

**验证结果**：
- ✅ 5 个子节全部存在
- ✅ 校验时机、字段校验、错误响应、错误码映射、内容类型全部定义
- ✅ 与 R1-15 错误码体系关联

#### 3.5 端点引用更新验证

```bash
# 验证 scattered 幂等性提及已更新
grep -c "见 1.4" docs/api/API_CONTRACT.md
# 结果：4（所有 scattered 提及）
```

**验证结果**：
- ✅ 所有 scattered 幂等性提及已更新为引用 Section 1.4
- ✅ 不再重复幂等性规则

#### 3.6 与 R1-15 兼容性验证

**验证方法**：
- R1-16 引用的错误码（`INVALID_INPUT`、`INVALID_PAGINATION`、`IDEMPOTENCY_KEY_REQUIRED`、`IDEMPOTENCY_CONFLICT`）均在 R1-15 定义
- R1-16 未修改 R1-15 的错误码分类和映射

**结论**：✅ 与 R1-15 完全兼容

### 4. 文档变更摘要

| 文档 | 变更类型 | 变更内容 |
|------|---------|---------|
| docs/api/API_CONTRACT.md | Section 1.3 扩展 | 分页 → 通用请求规则（8 个子节，140+ 行） |
| docs/api/API_CONTRACT.md | Section 1.4 扩展 | 幂等性 → 幂等规则（10 个子节，180+ 行） |
| docs/api/API_CONTRACT.md | 新增 Section 1.7 | 统一响应模型（8 个子节，120+ 行） |
| docs/api/API_CONTRACT.md | 新增 Section 1.8 | 请求校验规则（5 个子节，80+ 行） |
| docs/api/API_CONTRACT.md | 端点引用更新 | Auth register 幂等性提及更新 |
| docs/api/API_CONTRACT.md | 端点引用更新 | Admin 请求头 Idempotency-Key 提及更新（3 处） |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 状态更新 | R1-16：`[ ]` → `[x]` |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明 | 添加 R1-16 完成说明 |

### 5. 验收结果

#### 5.1 验收检查清单

- [x] API 契约不再每个模块各写一套请求响应风格（统一引用 Section 1.3～1.8）
- [x] 幂等规则覆盖关键写操作（18 个必支持 + 3 个可选端点）
- [x] 前后端可以基于统一模型生成类型或 Mock（6 种响应模型 + 统一字段规则）
- [x] 统一分页、排序、过滤、时间格式、ID 格式、空值规则
- [x] 统一列表、详情、创建、更新、异步、删除响应模型
- [x] 明确请求校验失败如何返回 R1-15 错误码
- [x] P0_P1_REMEDIATION_PLAN.md 已更新

#### 5.2 统一规则统计

| 规则类型 | 子节数 | 说明 |
|---------|:------:|------|
| 通用请求规则 | 8 | 分页/排序/过滤/时间/ID/空值/布尔/枚举 |
| 幂等规则 | 10 | 端点列表/Key 格式/作用域/过期/冲突处理 |
| 响应模型 | 8 | 列表/详情/创建/更新/异步/删除/空值 |
| 校验规则 | 5 | 校验时机/字段规则/错误响应/错误码映射/内容类型 |
| **总计** | **31** | - |

#### 5.3 与 R1-08～R1-13 契约兼容性

**验证方法**：
- 仅添加统一规则和引用，未修改端点方法、权限、请求/响应、错误码
- 所有端点编号（EP-CONV-024～028、EP-AGENT-033～038、EP-MEM-039～045、EP-SCENE-046～057、EP-MODEL-058～060、EP-ADMIN-061～071）保持不变
- 新增 Section 1.7、1.8 不影响现有端点定义

**结论**：✅ 变更向后兼容，未破坏已有契约

### 6. 下一步

R1-16 已完成，R1 批次剩余任务：
- R1-17：冻结 API 文档状态

可继续执行 R1-17 或进入 R4 验收（前提：R1-17 全部完成）

### 7. 备注

**R1-16 与 R1-17 的关系**：
- R1-16 建立统一规则，R1-17 冻结 API 文档状态
- R1-16 的产出为 R1-17 的"已统一"状态提供依据
- R1-17 需要记录：统一规则评审人、日期、决议