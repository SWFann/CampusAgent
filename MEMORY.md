---
name: dev-logging-system
description: CampusAgent 开发日志系统的建立和使用方法
metadata:
  type: reference
---

# 开发日志系统

## 系统概述

CampusAgent 项目的开发日志追踪系统，确保每个开发任务都留有完整的可追溯记录。

## 目录结构

```
development-logs/
├── README.md              - 系统说明
├── PROGRESS.md            - 总进度追踪表
├── USAGE_GUIDE.md         - 详细使用指南
├── templates/
│   └── task-template.md   - 任务日志模板
├── completed/             - 已完成任务归档
├── in-progress/           - 进行中的任务
└── planned/               - 计划中的任务
```

## 核心原则

1. **透明性** - 每个任务独立记录，可追溯
2. **结构化** - 统一模板，清晰分类
3. **实时性** - 边做边记，不事后补记
4. **诚实性** - 如实记录问题、耗时、阻塞

## 任务日志模板

每个任务日志包含：

```markdown
---
task_id: P0-01
status: completed | in-progress | blocked | cancelled
started_at: 2026-07-13T22:00:00+09:00
completed_at: 2026-07-13T23:30:00+09:00
estimated_hours: 3
actual_hours: 1.5
---

# 任务标题

## 目标
## 验收标准
## 实现过程
## 修改的文件（新增/修改/删除）
## 测试结果
## 问题与解决
## 下一步
## 提交信息
```

## 工作流程

### 开始任务
```bash
cp development-logs/templates/task-template.md \
   development-logs/in-progress/P0-XX-xxx.md
```

### 完成任务
```bash
# 1. 更新日志（验收标准、测试结果等）
# 2. 移动到完成目录
mv development-logs/in-progress/P0-XX-xxx.md \
   development-logs/completed/
# 3. 更新 PROGRESS.md
# 4. 提交代码和日志
```

## 状态标记

- ⬜ 未开始
- 🔄 进行中
- ✅ 已完成
- ❌ 阻塞
- 🚫 已取消

## 当前进度

**阶段**：P0 初始化阶段
**已完成**：1/169 任务 (0.6%)
**当前任务**：P0-01 建立领域词汇表 ✅

## 关键文档

- [使用指南](USAGE_GUIDE.md) - 详细使用说明
- [总进度表](PROGRESS.md) - 所有任务进度
- [下一步指引](NEXT_STEPS.md) - 当前任务指引

## 初始化信息

**初始化时间**：2026-07-13
**系统版本**：v1.0
**状态**：✅ 就绪
