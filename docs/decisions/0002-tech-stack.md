# ADR-002：技术栈选择

**状态**：Accepted  
**日期**：2026-07-14  
**决策者**：开发团队

## 背景

需要确定 MVP 的技术栈。

## 前端技术栈

### 决策

- **框架**：Next.js 14（App Router）
- **语言**：TypeScript（严格模式）
- **样式**：Tailwind CSS + shadcn/ui
- **状态管理**：Zustand
- **API 调用**：OpenAPI 生成客户端
- **实时通信**：原生 WebSocket

### 理由

- Next.js 生态成熟，适合快速开发
- TypeScript 提供类型安全
- Tailwind + shadcn/ui 提供完整设计系统
- Zustand 简单轻量

---

## 后端技术栈

### 决策

- **框架**：FastAPI
- **语言**：Python 3.11+
- **数据验证**：Pydantic
- **ORM**：SQLAlchemy 2.0（异步）
- **数据库迁移**：Alembic
- **实时通信**：WebSocket
- **任务队列**：BackgroundTasks（初期），Celery（后续）

### 理由

- FastAPI 现代化、类型安全、性能好
- Pydantic 提供强大数据验证
- SQLAlchemy 成熟稳定
- FastAPI 原生支持 WebSocket

---

## 数据存储

### 决策

- **主数据库**：PostgreSQL 15
- **向量数据库**：pgvector（PostgreSQL 扩展）
- **缓存**：Redis 7
- **对象存储**：MinIO（可选）

### 理由

- PostgreSQL 功能强大、稳定
- pgvector 提供向量检索能力
- Redis 适合会话和实时通信

---

## AI 基础设施

### 决策

- **统一接口**：OpenAI-compatible API
- **本地模型**：Ollama/vLLM
- **模拟**：Mock + 规则引擎

### 理由

- OpenAI 协议已成为事实标准
- 便于切换不同模型
- Mock + 规则引擎提供备用路径

---

## 部署

### 决策

- **容器化**：Docker + Docker Compose
- **监控**：Prometheus + Grafana（可选）

### 理由

- Docker Compose 简单易用
- 适合 MVP 快速部署

---

## 后果

- 全栈 TypeScript + Python
- 统一开发体验
- 良好的类型安全
- 便于 AI 辅助开发

## 相关文档

- [完整项目计划书](../product/CampusAgent_Project_Plan.md)
- [开发计划表](../development/DEVELOPMENT_PLAN.md)
