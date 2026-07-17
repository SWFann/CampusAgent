# P7 Full Implementation Guide

> 给 Claude / CatPaw / GLM / Codex 等执行工具使用。本文是 P7「模型网关与边缘节点」完整执行指令。执行方必须在 `/root/CampusAgent` 中按任务顺序完成 P7-01～P7-12；不得跳任务、不得执行 P8+、不得提交、不得推送。完成后输出完整报告，交给 Codex 做全量审计、修复、提交和远端 CI 观察。

## 0. 项目背景

项目路径：`/root/CampusAgent`

P7 前置条件：

- P6 必须已由 Codex 审计、修复、提交、推送，并且远端 CI 绿色。
- 如果 P6 仍未提交或工作树不干净，停止并报告。

P7 阶段名称：模型网关与边缘节点。

P7 目标：

- 所有模型调用必须经过统一 Model Gateway。
- 业务模块不得直接依赖模型厂商 SDK。
- 默认核心 Demo 不依赖公网。
- 敏感请求不得路由到外部模型。
- 节点凭据加密存储。
- Prompt 和完整响应不得进入日志、审计、metrics label 或 AgentRun。

## 1. 实验室模型接入背景

当前实验室模型可能有两类部署架构：

- vLLM 架构。
- llama.cpp 架构。

部署环境：

- 统一在 k8s 平台部署。
- 可能通过 Ingress 暴露。
- 可能通过 NodePort 暴露。
- 命名空间可能包括 `inference`、`llama-cpp`、`light`。

非常重要：

- 不得把 Kuboard 地址写入代码。
- 不得把账号写入代码。
- 不得把密码写入代码。
- 不得把飞书一次性 token 写入代码、文档或日志。
- 不得把真实模型 endpoint 写入测试 fixture。
- 不得提交真实 API key。

正确做法：

- 抽象为 OpenAI-compatible provider。
- endpoint、api key、namespace、exposure_type 存入数据库加密字段或环境变量。
- 本地和 CI 默认使用 Mock Provider / Rule Provider。
- 真实实验室节点只在部署环境配置。

## 2. 开始前检查

```bash
cd /root/CampusAgent
git status --short --branch
git log -5 --oneline
```

预期：

- 工作树干净。
- 最新提交为 P6 Codex 收口提交。

## 3. 必读文件

1. `docs/development/DEVELOPMENT_PLAN.md`
2. `docs/development/P6-COMPLETION-REPORT.md`
3. `docs/api/API_CONTRACT.md`
4. `docs/privacy/PRIVACY_TEST_MATRIX.md`
5. `docs/security/THREAT_MODEL.md`
6. `docs/architecture/PERMISSION_MATRIX.md`
7. `apps/api/src/config.py`
8. `apps/api/src/modules/agents/`
9. `apps/api/src/modules/audit/`
10. `apps/api/src/modules/memories/encryption.py`
11. `apps/api/src/utils/redaction.py`
12. `apps/api/src/utils/metrics.py`

## 4. 文件结构规划

Model Gateway：

```text
apps/api/src/modules/model_gateway/models.py
apps/api/src/modules/model_gateway/schemas.py
apps/api/src/modules/model_gateway/exceptions.py
apps/api/src/modules/model_gateway/providers.py
apps/api/src/modules/model_gateway/mock_provider.py
apps/api/src/modules/model_gateway/rule_provider.py
apps/api/src/modules/model_gateway/openai_compatible.py
apps/api/src/modules/model_gateway/router.py
apps/api/src/modules/model_gateway/service.py
apps/api/src/modules/model_gateway/api.py
```

Nodes：

```text
apps/api/src/modules/nodes/models.py
apps/api/src/modules/nodes/schemas.py
apps/api/src/modules/nodes/repository.py
apps/api/src/modules/nodes/service.py
apps/api/src/modules/nodes/api.py
apps/api/src/modules/nodes/health.py
```

Migration：

```text
apps/api/alembic/versions/0006_model_gateway_node_tables.py
```

Frontend admin：

```text
apps/web/src/app/admin/models/page.tsx
apps/web/src/app/admin/nodes/page.tsx
apps/web/src/app/admin/deployments/page.tsx
apps/web/src/lib/modelGateway.ts
apps/web/src/lib/nodes.ts
```

Tests：

```text
apps/api/tests/unit/test_model_gateway_contract.py
apps/api/tests/unit/test_mock_provider.py
apps/api/tests/unit/test_rule_provider.py
apps/api/tests/unit/test_openai_compatible_adapter.py
apps/api/tests/unit/test_model_routing_policy.py
apps/api/tests/unit/test_structured_output_validation.py
apps/api/tests/unit/test_model_metadata_recording.py
apps/api/tests/unit/test_model_node_models.py
apps/api/tests/unit/test_node_health.py
apps/api/tests/unit/test_admin_model_api.py
apps/api/tests/unit/test_model_metrics.py
apps/api/tests/unit/test_model_privacy_leakage.py
```

## 5. P7-01 定义网关契约

定义统一 provider protocol：

```python
class ModelProvider(Protocol):
    def chat(self, request: ChatRequest) -> ChatResponse: ...
    def embedding(self, request: EmbeddingRequest) -> EmbeddingResponse: ...
    def health(self) -> ProviderHealth: ...
```

ChatRequest 必须包含：

- messages
- privacy_context
- timeout_ms
- response_schema
- purpose
- request_id

PrivacyContext：

- `data_classification: P0/P1/P2/P3/P4`
- `allow_external: bool`
- `requires_local: bool`
- `contains_personal_data: bool`
- `purpose: str`

测试：

- request schema 可序列化。
- privacy_context 必填。
- P4 默认 requires_local。

## 6. P7-02 Mock Provider

要求：

- 固定输出。
- 可复现。
- 支持 delay injection。
- 支持 failure injection。
- 不依赖外网。

测试：

- 同输入同输出。
- delay 生效。
- failure 返回可控错误。
- 不记录 prompt。

## 7. P7-03 Rule Provider

用于 P9 聚餐备用路径。

输入：

- candidates
- constraints
- weights

输出：

- score
- reason_codes
- safe_public_summary

测试：

- deterministic。
- hard constraint 生效。
- no model dependency。

## 8. P7-04 OpenAI-compatible 适配器

实现：

- `/v1/chat/completions`
- `/v1/embeddings` 可选
- base_url。
- model。
- api_key。
- timeout。
- retry。

适配 vLLM/llama.cpp：

- 不使用厂商 SDK。
- HTTP 协议兼容 OpenAI。
- 支持 Ingress/NodePort endpoint。

安全：

- request/response 正文不入日志。
- api_key 不入 repr。
- endpoint 可记录 host hash，不记录完整敏感 query。

测试：

- 用 respx/httpx mock。
- timeout。
- non-200。
- malformed JSON。
- api key redacted。

## 9. P7-05 路由策略

规则：

- P4 请求默认禁止外部。
- `requires_local=True` 只能 local/mock/rule。
- external provider 默认禁用。
- provider unhealthy 跳过。
- timeout 后按策略降级。
- 无可用 provider 返回 `MODEL_ROUTING_FAILED`。
- 敏感外发返回 `PRIVACY_CONTEXT_SENSITIVE_EXTERNAL_BLOCKED`。

测试：

- P4 + external only -> blocked。
- P1 + allow_external -> external allowed。
- local unhealthy -> fallback mock。
- all failed -> error。

## 10. P7-06 结构化输出校验

实现：

- Pydantic schema validation。
- JSON parse。
- limited retry。
- invalid output reject。

测试：

- valid JSON pass。
- invalid JSON retry。
- schema mismatch reject。
- retry 不记录 invalid raw output。

## 11. P7-07 调用元数据记录

对接 P6 AgentRun。

记录：

- input_hash。
- output_hash。
- provider。
- model。
- latency。
- token_count。
- status。

禁止：

- prompt。
- full response。
- private preference。

测试：

- AgentRun 创建。
- hash 长度正确。
- metadata 无 prompt。

## 12. P7-08 Model/Node/Deployment

模型：

- ModelDefinition。
- ModelNode。
- ModelDeployment。

Node 字段：

- endpoint_encrypted。
- credential_encrypted。
- namespace。
- exposure_type: INGRESS/NODEPORT/LOCAL/MOCK。
- health_status。
- last_heartbeat_at。

Deployment：

- model_id。
- node_id。
- status。
- priority。
- capabilities。

测试：

- endpoint 加密。
- credential 加密。
- repr 不泄露。
- exposure_type 枚举。

## 13. P7-09 节点健康检查

实现：

- timeout。
- circuit breaker。
- heartbeat。
- ONLINE/DEGRADED/OFFLINE。

测试：

- health success -> ONLINE。
- timeout -> DEGRADED。
- repeated failures -> OFFLINE/circuit open。
- recovery closes circuit。

## 14. P7-10 管理 API

端点对齐 API_CONTRACT Admin Model/Node/Deployment。

权限：

- SYSTEM_ADMIN / SCHOOL_ADMIN。
- ORG_ADMIN 不自动具备模型管理权限。
- Bearer admin token 规则按冻结契约。
- Cookie 写请求按 CSRF。

测试：

- non-admin denied。
- admin create node。
- node credential encrypted。
- list nodes redacts credential。
- update deployment。

## 15. P7-11 系统级指标

指标：

- calls_total。
- latency_ms。
- errors_total。
- provider_health。
- simulated cpu/gpu。

禁止标签：

- prompt。
- user email。
- raw endpoint with token。
- private data。

## 16. P7-12 路由/泄露测试

必须覆盖：

- 敏感请求不外发。
- prompt 不入日志。
- response 不入日志。
- credential 不入 repr。
- node failure fallback。
- external disabled reject。
- gitleaks no new findings。

## 17. 文档和报告

新增：

- `docs/development/P7-COMPLETION-REPORT.md`
- P7-01～P7-12 logs。

更新：

- `docs/development/DEVELOPMENT_PLAN.md`
- P7 `[x]`。
- P8 未开始。

完成报告必须包含：

- 实验室模型接入抽象说明。
- 未写入真实账号/密码声明。
- provider 列表。
- routing policy。
- privacy tests。
- validation results。

## 18. 全量验证

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
