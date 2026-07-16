---
task_id: P2-06
task_name: 统一 API Envelope
status: in_review
started_at: 2026-07-16T21:00:00+08:00
completed_at: 2026-07-16T21:30:00+08:00
actual_hours: 0.5
owner: Claude
auditor: Codex
---

# P2-06: 统一 API Envelope

## 1. 背景

- P2-01～P2-05 已完成。
- 当前路径：`/root/CampusAgent`
- 本次任务只做 P2-06：统一 API 响应 envelope 和错误格式。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/schemas/envelope.py` | 新增 | 统一成功/错误 envelope 模型、稳定错误码映射、工厂函数 |
| `apps/api/src/main.py` | 修改 | 异常处理器改用 envelope 工厂；新增 RequestValidationError/HTTPException/通用 Exception 处理器 |
| `apps/api/tests/unit/test_api_envelope.py` | 新增 | 20 个测试覆盖 envelope 构造、错误码映射、AppError 处理器、request_id 回填、未知异常不泄露、健康端点例外 |

## 3. 设计说明

### 3.1 Success Envelope

```json
{"success": true, "data": {}, "request_id": "uuid-or-null"}
```

### 3.2 Error Envelope

```json
{
  "success": false,
  "error": {"code": "STABLE_CODE", "message": "safe", "details": {}},
  "request_id": "uuid-or-null"
}
```

### 3.3 稳定错误码映射

| HTTP Status | Error Code |
|---|---|
| 400 | VALIDATION_ERROR |
| 401 | AUTH_FAILED |
| 403 | PERMISSION_DENIED |
| 404 | NOT_FOUND |
| 409 | CONFLICT |
| 422 | UNPROCESSABLE_ENTITY |
| 429 | RATE_LIMITED |
| 500 | INTERNAL_ERROR |
| unknown | INTERNAL_ERROR |

### 3.4 异常处理器

- `AppError` → 使用 envelope_error() 构造稳定错误
- `RequestValidationError` → 422 + UNPROCESSABLE_ENTITY
- `StarletteHTTPException` → 使用 error_code_for_status() 映射
- `Exception` (catch-all) → 500 + INTERNAL_ERROR，不泄露内部细节

### 3.5 健康端点例外

`/health/live` 和 `/health/ready` 不使用 envelope 格式，保持简单响应。

## 4. 验证命令结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 152 source files | |
| `python -m pytest apps/api/tests -q -p no:cacheprovider` | 156 passed, 1 warning in 0.83s | 136(P2-05) + 20(P2-06) |

## 5. 边界声明

- 未执行 P2-07～P2-14
- 未批量改所有 API（只建立工具和处理器）
- 未修改 P0/P1 冻结契约
- 未提交、未推送，等待 Codex 审计
