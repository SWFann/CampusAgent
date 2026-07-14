---
task_id: R1-05
status: completed
stage: R1
title: 建立枚举对照表
started_at: 2026-07-14T12:44:00+09:00
completed_at: 2026-07-14T12:46:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# R1-05：建立枚举对照表

## 完成状态

✅ **枚举对照表已建立**

**完成时间**：2026-07-14T12:46:00+09:00

## 目标

在领域词汇表中建立枚举值对照，确保中英文、数据库值、API 值一一对应。

**来自整改计划**：R1-05 - 建立枚举对照表

## 验收标准

- [x] 领域词汇表包含枚举值对照
- [x] 中英文、数据库值、API 值一一对应

## 修改的文件

- `docs/domain/DOMAIN_VOCABULARY.md` - 添加附录 A：枚举值对照表

## 添加的对照表

### A. 枚举值对照表

已添加到 `DOMAIN_VOCABULARY.md` 附录部分，包含以下枚举：

1. **GlobalRole（全局角色）**：6 个值
2. **OrganizationRole（组织内角色）**：4 个值
3. **SceneState（场景状态）**：9 个值
4. **AgentAutonomyLevel（代理等级）**：4 个值

每个对照表包含四列：
- **数据库值**：snake_case（如 `org_admin`）
- **API 值**：UPPER_SNAKE_CASE（如 `ORG_ADMIN`）
- **中文名**：界面显示名称
- **英文标识符**：代码中使用的枚举名称

## 枚举对照

### GlobalRole（全局角色）

| 数据库值 | API 值 | 中文名 | 英文标识符 |
|---------|--------|--------|----------|
| student | STUDENT | 学生 | Student |
| teacher | TEACHER | 教师 | Teacher |
| counselor | COUNSELOR | 心理支持人员 | Counselor |
| org_admin | ORG_ADMIN | 组织管理员 | OrganizationAdmin |
| school_admin | SCHOOL_ADMIN | 校方管理员 | SchoolAdmin |
| system_admin | SYSTEM_ADMIN | 系统管理员 | SystemAdmin |

### OrganizationRole（组织内角色）

| 数据库值 | API 值 | 中文名 | 英文标识符 |
|---------|--------|--------|----------|
| owner | OWNER | 所有者 | Owner |
| admin | ADMIN | 管理员 | Admin |
| member | MEMBER | 成员 | Member |
| guest | GUEST | 访客 | Guest |

### SceneState（场景状态）

| 数据库值 | API 值 | 中文名 | 说明 |
|---------|--------|--------|------|
| draft | DRAFT | 草稿 | 场景定义中 |
| published | PUBLISHED | 已发布 | 可被订阅 |
| running | RUNNING | 运行中 | 实例进行中 |
| voting | VOTING | 投票中 | 等待参与者投票 |
| completed | COMPLETED | 已完成 | 场景实例结束 |
| cancelled | CANCELLED | 已取消 | 提前终止 |
| archived | ARCHIVED | 已归档 | 历史存档 |
| failed | FAILED | 失败 | 运行出错 |
| timeout | TIMEOUT | 超时 | 超时终止 |

### AgentAutonomyLevel（代理等级）

| 数据库值 | API 值 | 中文名 | 说明 |
|---------|--------|--------|------|
| disabled | DISABLED | 禁用 | 仅人工处理 |
| suggest | SUGGEST | 建议 | 提供建议，人工确认 |
| auto_execute | AUTO_EXECUTE | 自动执行 | 自动处理，结果通知 |
| autonomous | AUTONOMOUS | 自主 | 完全自主运行 |

## 验证结果

- [x] 对照表已添加到 DOMAIN_VOCABULARY.md
- [x] 每个枚举的四列数据完整
- [x] 与 DOMAIN_VOCABULARY.md 中的枚举定义一致

## 下一步

- **R1 完成**：R1-A 全部完成
- **R1-B**：开始补全 HTTP API 合同

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
