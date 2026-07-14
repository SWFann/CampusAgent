---
task_id: P0-10
status: completed
stage: P0
title: 草拟实时与事件契约
started_at: 2026-07-14T06:30:00+09:00
completed_at: 2026-07-14T07:15:00+09:00
estimated_hours: 2
actual_hours: 0.75
---

# P0-10：草拟实时与事件契约

## 目标

草拟WebSocket协议和领域事件契约，包括连接、订阅、事件格式、重连语义。

**来自开发计划**：P0-10 - 草拟实时与事件契约

**产物**：WebSocket协议文档、事件清单

**依赖**：P0-09（HTTP契约 ✅）

## 验收标准

- [x] 定义WebSocket连接方式
- [x] 定义事件Envelope格式
- [x] 定义客户端事件
- [x] 定义服务端事件
- [x] 定义订阅机制
- [x] 定义重连策略
- [x] 文档已提交

## 实现过程

### 2026-07-14 06:30 - 07:15

基于文档：
- API_CONTRACT.md（P0-09）
- PRIVACY_BASELINE.md

### 事件清单（15+）

**消息事件**：3个
**会话事件**：4个
**场景事件**：3个（⭐ 关键隐私控制）
**通知事件**：1个

### 隐私控制点

**scene.updated 事件**：
- ✅ 只包含进度数字
- ❌ 不含任何个人偏好
- ❌ 不含智能体辩论

## 修改的文件

### 新增文件
- `docs/api/WEBSOCKET_CONTRACT.md` - WebSocket与事件契约（2,800+字）

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **依赖任务**：P0-11（建立隐私测试矩阵）

## 提交信息

- Commit: `docs(api): draft WebSocket and event contract`
- PR: （待创建）
