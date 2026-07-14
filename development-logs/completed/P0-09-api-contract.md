---
task_id: P0-09
status: completed
stage: P0
title: 草拟HTTP契约
started_at: 2026-07-14T05:45:00+09:00
completed_at: 2026-07-14T06:30:00+09:00
estimated_hours: 3
actual_hours: 0.75
---

# P0-09：草拟HTTP契约

## 目标

草拟完整的HTTP API契约，包括资源路径、请求响应、分页、错误码、Idempotency-Key。

**来自开发计划**：P0-09 - 草拟HTTP契约

**产物**：API规范文档

**依赖**：P0-04（权限矩阵 ✅）、P0-08（状态机 ✅）

## 验收标准

- [x] 定义所有API资源
- [x] 定义请求/响应格式
- [x] 定义分页规范
- [x] 定义错误码体系
- [x] 定义Idempotency-Key使用
- [x] 文档已提交

## 实现过程

### 2026-07-14 05:45 - 06:30

基于文档：
- DOMAIN_VOCABULARY.md（P0-01）
- PERMISSION_MATRIX.md（P0-04）
- SCENE_STATE_MACHINE.md（P0-08）
- MVP_SCOPE.md（P0-02）

### API端点统计

**62个MVP端点**：
- Auth: 5
- User: 4
- Organization: 11
- Directory: 3
- Conversation: 9
- Agent: 6
- Memory: 7
- Scene: 12（含私有提交）
- Model Gateway: 3（内部）
- Admin: 11

## 修改的文件

### 新增文件
- `docs/api/API_CONTRACT.md` - HTTP API契约文档（3,500+字）

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **依赖任务**：P0-10（实时与事件契约）

## 提交信息

- Commit: `docs(api): draft HTTP API contract`
- PR: （待创建）
