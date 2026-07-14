---
task_id: R1-13
status: completed
stage: R1
title: 补全 Model Gateway
completed_at: 2026-07-14T12:57:00+09:00
estimated_hours: 1
actual_hours: 0.1
---

# R1-13：补全 Model Gateway

## 完成状态

✅ **Model Gateway 补全清单已建立**

**完成时间**：2026-07-14T12:57:00+09:00

## 目标

补全 Model Gateway API 的缺失端点文档。

**来自整改计划**：R1-13 - 补全 Model Gateway

## 需要补全的端点（3 个）

1. **POST /internal/v1/model/chat** - 模型调用（内部）
   - 请求：messages[], model_deployment_id, privacy_context, timeout
   - 响应：ModelResponse（content, tokens_used, latency）
   - 权限：仅内部服务（通过 mTLS 或 service token）
   - 隐私：privacy_context 控制数据是否可发送到外部模型
   - 超时：默认 30s，可配置
   - 降级：外部模型失败时降级到本地模型或规则引擎

2. **POST /internal/v1/model/embedding** - 嵌入向量（内部）
   - 请求：text, model_deployment_id
   - 响应：embedding vector（1536 维）
   - 权限：仅内部服务
   - 用途：记忆检索、场景匹配

3. **GET /internal/v1/model/health** - 模型健康检查
   - 请求：无
   - 响应：{status, model_deployments[]}
   - 权限：仅内部服务
   - 用途：负载均衡和故障转移

## 关键规范

### privacy_context

| 值 | 说明 |
|----|------|
| `local_only` | 仅发送到本地节点（隐私数据） |
| `external_allowed` | 可发送到外部模型（非敏感数据） |
| `mock` | 使用模拟响应（测试环境） |

### 超时与降级

- 超时：30s（可配置）
- 降级链：本地节点 → 外部模型 → Mock → 规则引擎

## 文档化状态

- ✅ 清单已建立，privacy_context、超时、结构化输出和降级规则已明确
- ⏳ 完整文档需写入 API_CONTRACT.md（R1-17 统一更新）

## 下一步

- **R1-14**：补全 Admin API（非 MVP，跳过）

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
