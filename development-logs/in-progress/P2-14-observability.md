---
task_id: P2-14
task_name: 基础可观测性
status: in_review
started_at: 2026-07-17T00:00:00+08:00
completed_at: 2026-07-17T00:15:00+08:00
actual_hours: 0.25
owner: Claude
auditor: Codex
---

# P2-14: 基础可观测性

## 修改文件列表
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/utils/metrics.py` | 新增 | RequestMetrics 内存计数器、MetricsMiddleware、register_metrics_endpoint /metrics |
| `apps/api/src/main.py` | 修改 | 集成 MetricsMiddleware 和 /metrics 端点 |
| `apps/api/tests/unit/test_metrics.py` | 新增 | 6 个测试覆盖 record、Prometheus text、空 metrics、/metrics 端点、请求递增 |

## 设计说明
- RequestMetrics: 内存中跟踪请求计数、状态码分布、延迟统计
- MetricsMiddleware: 拦截所有请求并记录
- /metrics: Prometheus-style text 输出（不含敏感标签）
- /metrics 端点 include_in_schema=False（内部端点）
- 健康检查统一在 /health/live 和 /health/ready

## 验证结果
| 命令 | 结果 |
|---|---|
| ruff | All checks passed! |
| mypy | 167 source files, no issues |
| pytest | 222 passed |

## 边界声明
- 未引入 Prometheus 客户端库或 OpenTelemetry（P3+ 可替换）
- 未修改 P0/P1 冻结契约
- 未提交、未推送
