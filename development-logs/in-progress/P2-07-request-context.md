---
task_id: P2-07
task_name: 请求上下文中间件
status: in_review
started_at: 2026-07-16T21:45:00+08:00
completed_at: 2026-07-16T22:30:00+08:00
actual_hours: 0.75
owner: Claude
auditor: Codex
---

# P2-07: 请求上下文中间件

## 1. 背景

- P2-01～P2-06 已完成。
- 本次任务只做 P2-07：请求上下文中间件（request ID、耗时、actor 摘要、结构化日志）。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/middleware/request_context.py` | 新增 | RequestContextMiddleware：UUID 验证、request_id 生成/复用、耗时记录、结构化日志、敏感 header 排除 |
| `apps/api/src/utils/logging.py` | 新增 | JsonFormatter 结构化日志、configure_logging、get_logger |
| `apps/api/src/main.py` | 修改 | 替换内联 correlation_id_middleware 为 RequestContextMiddleware；配置结构化日志；移除直接 uuid 使用 |
| `apps/api/tests/unit/test_request_context.py` | 新增 | 16 个测试覆盖 UUID 验证、安全 header、request ID 处理、耗时跟踪、日志时间戳格式 |

## 3. 设计说明

### 3.1 Request ID 解析

- 优先检查 `X-Correlation-ID`，如果包含合法 UUID 则复用
- 其次检查 `X-Request-ID`，如果包含合法 UUID 则复用
- 否则生成 UUID v4
- 非 UUID 值被忽略（不回传、不记录）

### 3.2 State 属性

- `request.state.request_id`：当前 request ID
- `request.state.correlation_id`：向后兼容别名
- `request.state.request_duration_ms`：请求耗时（毫秒）

### 3.3 响应 Header

- `X-Correlation-ID` 始终回传

### 3.4 日志策略

- 请求开始/结束/错误时记录结构化 JSON 日志
- actor 当前为 `anonymous`（P3 实现 auth 后更新）
- 不记录 Authorization、Cookie、Set-Cookie、X-API-Key、X-Auth-Token
- 不记录请求体、prompt、私有数据

## 4. 验证命令结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 155 source files | |
| `python -m pytest apps/api/tests/unit/test_request_context.py -q -p no:cacheprovider` | 16 passed, 1 warning in 0.30s | Codex 审计修正后 P2-07 定向回归 |

## 4.1 Codex 审计修正

Codex 全量审计发现 `JsonFormatter` 时间戳中 `%f` 未被展开，运行时日志输出类似 `2026-07-16T20:48:06.%fZ`，不符合 P2-07 结构化日志的 ISO-8601 UTC 目标。已修正为基于 `datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds")` 的毫秒级 UTC 时间戳，并新增 `TestStructuredLogging::test_json_formatter_uses_iso_timestamp` 回归测试。

## 5. 边界声明

- 未执行 P2-08～P2-14
- 未实现 auth/actor 识别（P3）
- 未修改 P0/P1 冻结契约
- 未提交、未推送，等待 Codex 审计
