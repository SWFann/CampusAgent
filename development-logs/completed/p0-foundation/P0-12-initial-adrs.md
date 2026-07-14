---
task_id: P0-12
status: completed
stage: P0
title: 接受首批ADR
started_at: 2026-07-14T08:00:00+09:00
completed_at: 2026-07-14T08:10:00+09:00
estimated_hours: 2
actual_hours: 1
---

# P0-12：接受首批ADR

## 目标

创建并接受首批架构决策记录（ADR），记录P0阶段的关键决策。

**来自开发计划**：P0-12 - 接受首批ADR

**产物**：5个关键ADR文档

**依赖**：P0-07（威胁模型 ✅）、P0-09（HTTP契约 ✅）、P0-10（WebSocket契约 ✅）

## 验收标准

- [x] ADR-001：模块化单体架构
- [x] ADR-002：技术栈选择
- [x] ADR-003：认证方式
- [x] ADR-004：模型路由策略
- [x] ADR-005：数据保留策略
- [x] 所有ADR状态为Accepted
- [x] 文档已提交

## 实现过程

### ADR-001：模块化单体架构
- **决策**：采用模块化单体架构
- **理由**：平衡开发效率和架构合理性
- **后果**：
  - 所有业务模块放在 `backend/app/modules/` 下
  - 每个模块有独立目录
  - 模块间通过公开 Service Interface 调用
  - 未来可拆分为微服务

### ADR-002：技术栈选择
- **前端**：Next.js 14 + TypeScript + Tailwind + shadcn/ui + Zustand
- **后端**：FastAPI + Pydantic + SQLAlchemy 2.0 + Alembic
- **数据存储**：PostgreSQL 15 + pgvector + Redis 7 + MinIO（可选）
- **AI 基础设施**：OpenAI-compatible API + Ollama/vLLM + Mock/规则引擎
- **部署**：Docker + Docker Compose

### ADR-003：认证方式
- **决策**：JWT + HttpOnly Cookie
- **Access Token**：1小时有效期
- **Refresh Token**：7天有效期，单次使用（旋转）
- **安全措施**：bcrypt密码、强制HTTPS、CSRF Token、接口限流

### ADR-004：模型路由策略
- **统一入口**：所有模型调用必须经过 Model Gateway
- **隐私优先**：敏感数据优先本地节点
- **降级策略**：本地节点 → 外部API（仅授权） → Mock → 规则引擎
- **元数据**：只记录哈希，不记录原始内容

### ADR-005：数据保留策略
- **P4 数据**：立即删除（私有提交、偏好胶囊、私有评价）
- **Audit 日志**：90天后自动删除
- **Agent Run**：30天后删除
- **长期记忆**：用户控制
- **清理机制**：每5分钟运行一次定时任务

## 修改的文件

### 新增文件
- `docs/decisions/0001-modular-monolith.md` ✅
- `docs/decisions/0002-tech-stack.md` ✅
- `docs/decisions/0003-authentication.md` ✅
- `docs/decisions/0004-model-routing.md` ✅
- `docs/decisions/0005-data-retention.md` ✅

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- ✅ **P0 阶段完成！** 🎉
- **注意事项**：进入P1工程初始化阶段
- **后续任务**：P1-01 到 P1-12（Monorepo & Engineering Toolchain）

## 提交信息

- Commit: `docs(adr): accept first batch of ADRs`
