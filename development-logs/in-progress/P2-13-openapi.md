---
task_id: P2-13
task_name: OpenAPI 生成基线
status: in_review
started_at: 2026-07-16T23:50:00+08:00
completed_at: 2026-07-17T00:00:00+08:00
actual_hours: 0.17
owner: Claude
auditor: Codex
---

# P2-13: OpenAPI 生成基线

## 修改文件列表
| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/main.py` | 修改 | FastAPI 增加 description 和 openapi_tags；健康端点加 tags=["health"] |
| `apps/api/tests/unit/test_openapi.py` | 新增 | 4 个测试覆盖 /openapi.json 生成、/docs、/redoc、tags |

## 设计说明
- FastAPI 自动生成 OpenAPI schema
- openapi_tags: [{"name": "health", "description": "..."}]
- 健康端点标记 tags=["health"]
- /metrics 端点 include_in_schema=False（内部端点）
- /docs (Swagger UI) 和 /redoc 可用

## 验证结果
| 命令 | 结果 |
|---|---|
| ruff | All checks passed! |
| mypy | 167 source files, no issues |
| pytest | 222 passed |

## 边界声明
- 未修改 P0/P1 冻结契约
- 未提交、未推送
