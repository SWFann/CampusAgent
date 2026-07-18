---
task_id: P7-01..P7-12
task_name: 模型网关与边缘节点
status: complete
started_at: 2026-07-18T00:00:00+08:00
completed_at: 2026-07-18T17:40:00+08:00
actual_hours: 8
owner: Claude
auditor: pending
---

# P7: 模型网关与边缘节点 — 完成报告

## 概述

P7 阶段实现了统一的模型调用入口、Provider 抽象（Mock/Rule/OpenAI-compatible）、
隐私感知的路由策略、节点健康检查（熔断器）、管理 API 以及系统指标监控。

核心隐私契约：**严禁泄露 Prompt/Response 正文，P4 数据必须本地化处理**。

## 任务完成清单

| ID | 任务 | 状态 |
|---|---|---|
| P7-01 | 定义网关契约 | ✅ schemas.py (PrivacyContext, ChatRequest, ChatResponse, EmbeddingRequest/Response, ProviderHealth) |
| P7-02 | 实现 Mock Provider | ✅ mock_provider.py (确定性、延迟/故障注入、结构化输出) |
| P7-03 | 实现规则 Provider | ✅ rule_provider.py (聚餐基础评分的无模型备用路径) |
| P7-04 | 实现 OpenAI-compatible 适配器 | ✅ openai_compatible.py (httpx、SecretStr、host_hash、重试) |
| P7-05 | 实现路由策略 | ✅ router.py (P4→local-only、外部默认禁用、健康/优先级选择) |
| P7-06 | 实现结构化输出校验 | ✅ service.py (_schema_to_pydantic_model、_validate_structured_output、有限重试) |
| P7-07 | 实现调用元数据记录 | ✅ service.py (input_hash/output_hash SHA-256、AgentRun 只存哈希) |
| P7-08 | 设计 Model/Node/Deployment | ✅ models.py (ModelNode、ModelDeployment、加密凭据) |
| P7-09 | 实现节点健康检查 | ✅ health.py (CircuitBreaker CLOSED/OPEN/HALF_OPEN、超时/熔断) |
| P7-10 | 实现管理 API | ✅ api.py (nodes/models/deployments CRUD、RBAC、CSRF) |
| P7-11 | 实现系统级指标 | ✅ metrics.py (calls_total、latency_ms、errors_total、provider_health、Prometheus text) |
| P7-12 | 完成路由/泄露测试 | ✅ 12 个测试文件、160 个测试用例 |

## 修改/新增文件列表

### 后端源码 (apps/api/src/modules/model_gateway/)
| 文件 | 操作 | 说明 |
|---|---|---|
| `__init__.py` | 修改 | 模块导出 |
| `schemas.py` | 新增 | PrivacyContext、ChatRequest/Response、EmbeddingRequest/Response、ProviderHealth、RoutingDecision |
| `providers.py` | 新增 | ModelProvider Protocol、ProviderType 枚举、privacy_gate 函数 |
| `exceptions.py` | 新增 | 7 个异常类（PRIVACY_CONTEXT_MISSING、MODEL_ROUTING_FAILED 等） |
| `mock_provider.py` | 新增 | 确定性 Mock、延迟/故障注入、结构化输出 |
| `rule_provider.py` | 新增 | 规则引擎 Provider（聚餐评分备用路径） |
| `openai_compatible.py` | 新增 | HTTP 适配器、SecretStr、host_hash、重试 |
| `router.py` | 新增 | RoutingPolicy、ProviderCandidate、build_default_candidates |
| `service.py` | 新增 | ModelGatewayService（编排、哈希、AgentRun、指标） |
| `metrics.py` | 新增 | ModelGatewayMetrics（线程安全、Prometheus text、TypedDict） |
| `models.py` | 新增 | ModelDefinition ORM |
| `api.py` | 新增 | 内部 API (/internal/v1/model/chat、/embedding、/health) |
| `events.py` | 已有 | 事件定义 |
| `permissions.py` | 已有 | 权限定义 |
| `repository.py` | 修改 | 数据访问层 |

### 后端源码 (apps/api/src/modules/nodes/)
| 文件 | 操作 | 说明 |
|---|---|---|
| `__init__.py` | 修改 | 模块导出 |
| `models.py` | 新增 | ModelNode、ModelDeployment ORM（加密 endpoint/credential） |
| `schemas.py` | 新增 | NodeCreate/Read/Update、ModelCreate/Read、DeploymentCreate/Read |
| `repository.py` | 新增 | NodeRepository、ModelRepository、DeploymentRepository |
| `service.py` | 新增 | 管理服务（RBAC、加密、健康检查触发） |
| `health.py` | 新增 | CircuitBreaker、NodeHealthChecker（httpx MockTransport） |
| `api.py` | 新增 | 管理 API (/api/v1/admin/nodes、/models、/deployments) |
| `exceptions.py` | 新增 | 节点异常 |
| `events.py` | 已有 | 事件定义 |
| `permissions.py` | 已有 | 权限定义 |

### 数据库迁移
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/alembic/versions/0006_model_gateway_node_tables.py` | 新增 | ModelNode、ModelDeployment、ModelDefinition 表 |

### 测试文件 (apps/api/tests/unit/)
| 文件 | 测试数 | 说明 |
|---|---|---|
| `test_model_gateway_contract.py` | 9 | 契约验证 |
| `test_mock_provider.py` | 12 | Mock Provider |
| `test_rule_provider.py` | 10 | Rule Provider |
| `test_openai_compatible_adapter.py` | 15 | OpenAI 适配器 |
| `test_model_routing_policy.py` | 7 | 路由策略 |
| `test_structured_output_validation.py` | 9 | 结构化校验 |
| `test_model_metadata_recording.py` | 4 | 元数据记录 |
| `test_model_node_models.py` | 10 | ORM 模型 |
| `test_node_health.py` | 10 | 节点健康 |
| `test_admin_model_api.py` | 9 | 管理 API |
| `test_model_metrics.py` | 27 | 指标系统 |
| `test_model_privacy_leakage.py` | 31 | 隐私泄露防护 |
| **合计** | **160** | |

## 设计要点

### 1. 隐私优先的路由
- `PrivacyContext` 强制附加到每个请求（fail-closed）
- P4 → `requires_local=True`、`allow_external=False`（自动强制）
- P3/P4 → `is_external_blocked=True`
- `RoutingPolicy.select()` 按优先级选择健康 Provider
- `select_for_fallback()` 永不降级到外部

### 2. 内容零泄露
- `input_hash`/`output_hash` = SHA-256，原文立即丢弃
- `AgentRun` 只存储：input_hash、output_hash、model、token_count、latency_ms、status
- `StructuredOutputValidationError` 不包含原始输出
- `OpenAICompatibleProvider.__repr__` 不包含 api_key
- `metrics` 标签只用：provider_type、provider_name、status、error_code、host_hash
- `RoutingDecision` 只有非敏感字段，`extra="forbid"`

### 3. 熔断器
- 三态：CLOSED → OPEN（失败阈值）→ HALF_OPEN（冷却后）→ CLOSED（成功）/ OPEN（失败）
- 熔断开启时跳过探测（`checks.model_gateway = "skipped"`）

### 4. 指标系统
- 线程安全（`threading.Lock`）
- TypedDict 精确类型（`MetricsSnapshot`、`LatencySummary`）
- Prometheus text 输出（`/metrics/model-gateway`）
- 延迟样本上限 10000（防内存膨胀）

## 验证结果

| 命令 | 结果 |
|---|---|
| `ruff check src/modules/model_gateway/ src/modules/nodes/` | All checks passed! |
| `mypy src/modules/model_gateway/ src/modules/nodes/` | Success: no issues found in 26 source files |
| `pytest tests/unit/` (全套) | **841 passed** in 85.51s |
| `pytest` (P7 专项 12 文件) | **160 passed** in 3.44s |
| `pnpm lint` | 通过 |
| `pnpm build` | 通过 |

## 隐私验证矩阵

| 场景 | 测试 | 结果 |
|---|---|---|
| P4 强制本地 | test_p4_sets_requires_local | ✅ |
| P4 阻止外部 | test_p4_blocks_external | ✅ |
| P3 阻止外部 | test_p3_blocks_external | ✅ |
| 缺失隐私上下文 → 拒绝 | test_missing_privacy_context_raises | ✅ |
| P4+外部+Mock → 路由到 Mock | test_p4_with_external_and_mock_routes_to_mock | ✅ |
| Fallback 不用外部 | test_fallback_never_uses_external | ✅ |
| Prompt 不在响应中 | test_prompt_not_in_response_content | ✅ |
| Prompt 不在指标中 | test_prompt_not_in_metrics | ✅ |
| Prompt 不在 AgentRun 中 | test_prompt_not_in_agent_run | ✅ |
| Prompt 不在路由决策中 | test_prompt_not_in_routing_decision | ✅ |
| Response 不在指标中 | test_response_not_in_metrics | ✅ |
| Response 不在 AgentRun 中 | test_response_not_in_agent_run | ✅ |
| Hash = SHA-256 (64 hex) | test_input_hash_is_sha256 | ✅ |
| 校验错误不含原始输出 | test_validation_error_excludes_raw_content | ✅ |
| OpenAI repr 不含 api_key | test_repr_excludes_api_key | ✅ |
| OpenAI 错误不含 api_key | test_error_details_exclude_api_key | ✅ |
| 请求体不被记录 | test_request_body_not_logged | ✅ |
| 指标不含用户邮箱 | test_no_user_email_in_metrics | ✅ |
| 指标不含原始端点 | test_no_raw_endpoint_in_metrics | ✅ |
| AgentRun 无内容列 | test_agent_run_has_no_content_columns | ✅ |

## 边界声明
- 未引入真实外部模型或 GPU 节点（保留 Mock/Rule/接口）
- 未修改 P0-P6 冻结契约
- `encryption.py` 的 `type: ignore[import-not-found]` 已移除（cryptography 已安装）
- 未提交、未推送（等待用户审核）
