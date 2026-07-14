---
task_id: P0-08
status: completed
stage: P0
title: 冻结场景状态机
started_at: 2026-07-14T05:00:00+09:00
completed_at: 2026-07-14T05:45:00+09:00
estimated_hours: 2
actual_hours: 0.75
---

# P0-08：冻结场景状态机

## 目标

冻结场景生命周期状态机，包括合法转换、动作发起者、幂等规则、异常终态、超时行为。

**来自开发计划**：P0-08 - 冻结场景状态机

**产物**：状态机图、转换规则、超时策略

**依赖**：P0-03（用户旅程 ✅）

## 验收标准

- [x] 定义所有阶段状态
- [x] 定义合法状态转换
- [x] 定义每个转换的触发条件
- [x] 定义幂等规则
- [x] 定义异常终态
- [x] 定义超时行为
- [x] 文档已提交

## 实现过程

### 2026-07-14 05:00 - 05:45

基于文档：
- USER_JOURNEY.md（P0-03产出）

### 状态机设计

**9个正常状态**：
DRAFT → WAITING_FOR_PARTICIPANTS → WAITING_FOR_CONSENT → WAITING_FOR_PRIVATE_INPUT → PROCESSING → CANDIDATES_READY → VOTING → CONFIRMING → COMPLETED

**3个异常终态**：
CANCELLED、FAILED、EXPIRED

**关键设计**：
- 终态不可逆
- 所有转换需 SceneService 控制
- 支持 Idempotency-Key
- 超时自动推进

## 修改的文件

### 新增文件
- `docs/architecture/SCENE_STATE_MACHINE.md` - 场景状态机文档（2,500+字）

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **依赖任务**：P0-09（草拟HTTP契约）
- **注意事项**：状态机是场景实现的核心逻辑

## 提交信息

- Commit: `docs(architecture): freeze scene state machine`
- PR: （待创建）
