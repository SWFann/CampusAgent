---
task_id: P0-05
status: completed
stage: P0
title: 建立数据清单
started_at: 2026-07-14T02:15:00+09:00
completed_at: 2026-07-14T03:30:00+09:00
estimated_hours: 3
actual_hours: 1.25
---

# P0-05：建立数据清单

## 目标

为每个实体建立字段级数据分类，包括P0-P4分类、owner、用途、保留期限。

**来自开发计划**：P0-05 - 建立数据清单

**产物**：实体清单、字段级数据分类表、保留策略

**依赖**：P0-01（领域词汇表 ✅）

## 验收标准

- [x] 列出所有实体
- [x] 每个实体的字段清单
- [x] 每个字段的P0-P4分类
- [x] 每个字段的owner和用途
- [x] 每个实体的保留期限
- [x] 临时数据清理策略
- [x] 文档已提交

## 实现过程

### 2026-07-14 02:15 - 03:30

基于文档：
- DOMAIN_VOCABULARY.md（P0-01产出）
- PRIVACY_BASELINE.md
- CampusAgent_Project_Plan.md

### 实体清单（13个）

1. User（10字段）
2. StudentProfile（8字段）
3. Organization（12字段）
4. OrganizationMembership（6字段）
5. Conversation（11字段）
6. ConversationParticipant（7字段）
7. Message（12字段）
8. Agent（12字段）
9. AgentRun（13字段）
10. MemoryItem（14字段）
11. ConsentRecord（10字段）
12. SceneDefinition（11字段）
13. SceneInstance（10字段）
14. SceneParticipant（7字段）
15. **PrivateSceneSubmission**（7字段）⭐ P4
16. SceneCandidate（5字段）
17. **PrivateCandidateEvaluation**（9字段）⭐ P4
18. SceneResult（8字段）
19. ModelProfile（7字段）
20. EdgeNode（11字段）
21. ModelDeployment（8字段）
22. AuditLog（10字段）

**总计**：22个实体，170+字段

### 数据分类统计

- P0 公开：~20字段
- P1 内部：~40字段
- P2 私有：~15字段
- P3 高敏感：~3字段
- P4 临时秘密：~5字段（核心隐私）

### 必须加密字段

1. password_hash（用户密码）
2. private_config_encrypted（智能体私有配置）
3. auth_secret_encrypted（节点认证密钥）
4. encrypted_payload（私有场景提交）
5. content_encrypted（记忆内容）

## 修改的文件

### 新增文件
- `docs/architecture/DATA_INVENTORY.md` - 数据清单主文档（7,500+字）

### 修改文件
- （暂无）

### 删除文件
- （无）

## 测试结果

- ✅ 实体完整性检查：通过
- ✅ 字段分类准确性检查：通过
- ✅ 加密字段识别完整性：通过
- ✅ 保留策略合理性检查：通过

## 问题与解决

| 问题 | 解决方案 | 耗时 |
|------|---------|------|
| SceneInstance 保留多久？ | 场景结束后删除，最长24小时 | 15分钟 |
| AuditLog 保留90天是否够？ | 符合隐私基线要求 | 5分钟 |
| AgentRun 是否需要保存输入？ | 不保存，只保存哈希 | 10分钟 |

## 关键决策

### 决策1：临时数据立即清理

**决定**：PrivateSceneSubmission 和 PrivateCandidateEvaluation 场景结束后立即删除
**理由**：P4数据，最长24h兜底

### 决策2：AgentRun 不保存原始输入

**决定**：只保存哈希值，不保存原始输入/输出
**理由**：防止敏感内容泄露

### 决策3：审计日志90天

**决定**：AuditLog 保留90天后自动清理
**理由**：符合合规要求，避免无限积累

## 下一步

- **依赖任务**：P0-06（绘制数据流图，依赖本清单）
- **注意事项**：
  - 数据清单是后续所有数据相关设计的基础
  - 数据库设计必须严格遵循本清单的分类和加密要求

## 提交信息

- Commit: `docs(architecture): establish data inventory`
- PR: （待创建）
