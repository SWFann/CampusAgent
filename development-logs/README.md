# 开发日志系统

本目录用于追踪 CampusAgent 项目的完整开发过程，确保每个任务都留有可追溯的记录。

## 📁 目录结构

```
development-logs/
├── README.md                      # 本文件
├── PROGRESS.md                    # 总进度追踪表
├── completed/                     # 已完成任务归档
│   ├── P0-01-domain-vocabulary.md
│   └── ...
├── in-progress/                   # 进行中的任务
│   └── P1-02-workspace-init.md
└── planned/                       # 计划中的任务
    └── P0-03-user-journey.md
```

## 📝 任务日志模板

每个任务日志文件必须包含以下章节：

```markdown
---
task_id: P0-01
status: completed | in-progress | blocked | cancelled
started_at: 2026-07-13T21:00:00+09:00
completed_at: 2026-07-13T23:30:00+09:00
estimated_hours: 3
actual_hours: 3.5
---

# 任务标题

## 目标
（来自开发计划表的任务描述）

## 验收标准
- [ ] 标准1
- [ ] 标准2
- [ ] 标准3

## 实现过程
（详细记录实现步骤、关键决策、遇到的问题）

## 修改的文件
### 新增文件
- `path/to/file.md` - 文件用途说明

### 修改文件
- `path/to/existing.md` - 修改内容说明

### 删除文件
- （无或列出）

## 测试结果
- ✅ 单元测试：通过/失败
- ✅ 集成测试：通过/失败
- ✅ 隐私测试：通过/失败
- ✅ 手动验证：通过/失败

## 问题与解决
| 问题 | 解决方案 | 耗时 |
|------|---------|------|
| ... | ... | ... |

## 下一步
- 依赖任务：P0-02
- 注意事项：...

## 提交信息
- Commit: `docs(domain): establish domain vocabulary`
- PR: #1（如有）
```

## 🔄 工作流程

1. **开始任务前**
   - 从 `planned/` 移动到 `in-progress/`
   - 填写 `started_at` 和基本信息

2. **开发过程中**
   - 实时记录关键决策
   - 记录遇到的问题和解决方案
   - 更新修改的文件列表

3. **完成任务后**
   - 填写 `completed_at`
   - 更新所有验收标准状态
   - 填写测试结果
   - 移动到 `completed/`
   - 更新 `PROGRESS.md` 总进度表

4. **提交代码前**
   - 检查敏感信息泄露
   - 确保所有测试通过
   - 填写提交信息和PR链接

## 📊 PROGRESS.md 总进度表

总进度表位于根目录的 `PROGRESS.md`，格式：

```markdown
| 任务ID | 状态 | 开始日期 | 完成日期 | 实际人日 | 提交/PR | 备注 |
|--------|------|---------|---------|---------|---------|------|
| P0-01  | ✅   | 07-13   | 07-13   | 3.5h    | abc123  | -    |
| P0-02  | 🔄   | 07-13   | -       | -       | -       | 进行中 |
```

状态标记：
- ⬜ 未开始
- 🔄 进行中
- ✅ 已完成
- ❌ 阻塞
- 🚫 已取消

## 🏷️ 命名规范

任务日志文件命名：`{阶段}-{序号}-{简短描述}.md`

示例：
- `P0-01-domain-vocabulary.md`
- `P3-04-login-implementation.md`
- `P9-12-meal-scene-api.md`

## 📋 快速命令

```bash
# 开始新任务
cp development-logs/templates/task-template.md development-logs/in-progress/P0-XX-xxx.md

# 完成当前任务
mv development-logs/in-progress/P0-XX-xxx.md development-logs/completed/
# 然后更新 PROGRESS.md
```

## 🎯 使用原则

1. **透明性**：每个决策、修改、问题都要记录
2. **可追溯**：从日志可以重建整个开发过程
3. **可回顾**：定期回顾日志，提取经验教训
4. **不隐瞒**：问题、延期、重构都要如实记录
5. **及时更新**：边做边记，不要事后补记

---

**创建时间**：2026-07-13
**维护者**：开发团队
**最后更新**：2026-07-13
