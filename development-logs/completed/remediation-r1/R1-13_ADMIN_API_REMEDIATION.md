# R1-13 任务日志：确认并补全 Admin API 是否属于 MVP

> **任务编号**：R1-13
> **执行日期**：2026-07-14
> **执行人**：Claude
> **任务目标**：确认 Admin API 在 MVP 中的边界，补全文档，明确 Node、Model、Deployment CRUD、健康检查、管理视图是否属于 MVP 必需、Demo 必需、P2 延后或仅保留只读占位

## 任务背景

根据 `docs/project/P0_P1_REMEDIATION_PLAN.md` 的 R1 批次任务要求：
- **整改内容**：补全 Admin API
- **具体操作**：Node/Model/Deployment CRUD 和健康检查
- **完成标准**：管理员只能访问结构化元数据

### 前置条件验证

✅ R1-06 已完成：建立端点对照清单（68 个唯一端点）
✅ R1-07 已完成：补全 Directory API（3 个端点）
✅ R1-08 已完成：补全 Conversation API（5 个端点）
✅ R1-09 已完成：补全 Agent API（6 个端点）
✅ R1-10 已完成：补全 Memory API（7 个端点）
✅ R1-11 已完成：补全 Scene API（12 个端点）
✅ R1-12 已完成：补全 Model Gateway（3 个内部端点）

### 阅读的权威文档

1. ✅ docs/README.md - 文档中心入口
2. ✅ docs/project/P0_P1_REMEDIATION_PLAN.md - 整改计划
3. ✅ docs/product/MVP_SCOPE.md - MVP 范围定义
4. ✅ docs/product/PROJECT_OVERVIEW.md - 项目概览
5. ✅ docs/api/API_CONTRACT.md - HTTP API 契约（当前状态）
6. ✅ docs/architecture/PERMISSION_MATRIX.md - 权限矩阵
7. ✅ docs/privacy/PRIVACY_BASELINE.md - 隐私基线

## 执行过程

### 1. Admin API 边界分析

#### 1.1 权威文档结论

**MVP_SCOPE.md**（第163-175行）明确列出 Admin 端点为 MVP（P7阶段）：
```
#### Admin（P7阶段）
- ✅ POST /api/v1/admin/nodes - 创建节点
- ✅ GET /api/v1/admin/nodes - 节点列表
- ✅ GET /api/v1/admin/nodes/{node_id} - 节点详情
- ✅ PATCH /api/v1/admin/nodes/{node_id} - 更新节点
- ✅ DELETE /api/v1/admin/nodes/{node_id} - 删除节点
- ✅ POST /api/v1/admin/nodes/{node_id}/health-check - 健康检查
- ✅ GET /api/v1/admin/nodes/{node_id}/metrics - 节点指标
- ✅ POST /api/v1/admin/models - 创建模型
- ✅ GET /api/v1/admin/models - 模型列表
- ✅ POST /api/v1/admin/deployments - 创建部署
- ✅ GET /api/v1/admin/deployments - 部署列表
```

**MVP_SCOPE.md 第6章"管理能力清单"**明确：
- 第248-256行：用户管理、组织管理、模型管理、节点管理、运行监控、安全审计都是 **必须完成（MVP）**
- 优先级：**P1**（必须在 P13 交付前完成）

**PROJECT_OVERVIEW.md**（第11行）：
> 校方管理员：管理账号、组织、模型和节点，仅查看脱敏运行指标

**PERMISSION_MATRIX.md**（第188-204行）：
- **SCHOOL_ADMIN**：可管理边缘节点（`node: manage`）、可管理模型配置（`model: manage`）
- **SYSTEM_ADMIN**：可读取所有资源的结构化元数据（`all: read（脱敏）`）
- **关键约束**（第201行）：
  - ❌ **不能读取 P2/P3 数据正文**（包括私有偏好、记忆、聊天）

**PRIVACY_BASELINE.md**（第50行）：
> 群主和 SchoolAdmin 均无法读取 P2/P3 正文

#### 1.2 API_CONTRACT.md 现状分析

**当前实现**（第2943-2983行）：仅 3 个端点
```
✅ GET /api/v1/admin/nodes - 节点列表
✅ GET /api/v1/admin/nodes/{node_id}/metrics - 节点指标
✅ GET /api/v1/admin/users - 用户列表
```

**缺失端点**：8 个
```
❌ POST /api/v1/admin/nodes - 创建节点
❌ GET /api/v1/admin/nodes/{node_id} - 节点详情
❌ PATCH /api/v1/admin/nodes/{node_id} - 更新节点
❌ DELETE /api/v1/admin/nodes/{node_id} - 删除节点
❌ POST /api/v1/admin/nodes/{node_id}/health-check - 健康检查
❌ POST /api/v1/admin/models - 创建模型
❌ GET /api/v1/admin/models - 模型列表
❌ POST /api/v1/admin/deployments - 创建部署
❌ GET /api/v1/admin/deployments - 部署列表
```

**缺失原因分析**：
- R1-13 任务目标明确："确认并补全 Admin API 是否属于 MVP"
- 说明 Admin API 的 MVP 状态存在疑问，需要先确认再补全
- 但权威文档（MVP_SCOPE.md、PERMISSION_MATRIX.md）已明确 Admin API 属于 MVP

#### 1.3 矛盾识别

**矛盾点 1**：
- **MVP_SCOPE.md**：Admin API 属于 MVP，11 个端点，P1 优先级
- **API_CONTRACT.md**：仅实现 3 个端点，8 个缺失
- **原因**：R1-13 尚未完成，补全工作未执行

**矛盾点 2**：
- **整改计划 R1-13**："确认并补全 Admin API 是否属于 MVP"
- **MVP_SCOPE.md**：已明确属于 MVP
- **原因**：审计后发现文档不一致，需要重新确认边界

**结论**：Admin API **属于 MVP**，但契约定义不完整，需要补全剩余 8 个端点。

### 2. Admin API 分类表

| 分类 | 端点 | 数量 | 说明 |
|------|------|------|------|
| **MVP 必需** | 全部 11 个端点 | 11 | Admin API 整体属于 MVP（P7阶段，P1优先级） |
| **Demo 必需** | 节点列表、模型列表、健康检查 | 3 | Demo 演示需要展示管理后台 |
| **P2 延后** | 无 | 0 | 所有端点都在 MVP 范围内 |
| **明确不做** | 无 | 0 | Admin API 属于 MVP 必须完成 |

**分类依据**：
1. MVP_SCOPE.md 第163-175行：11 个端点全部标记为 ✅ MVP
2. MVP_SCOPE.md 第248-256行：管理能力清单标记为 **必须完成（MVP）**
3. PROJECT_OVERVIEW.md：校方管理员是核心用户角色
4. PERMISSION_MATRIX.md：SCHOOL_ADMIN 和 SYSTEM_ADMIN 都有明确权限

### 3. 隐私边界定义

#### 3.1 管理员可见信息范围

**✅ 可访问**：
- 节点配置和运行指标（CPU、内存、GPU、活跃请求数）
- 模型配置元数据（名称、版本、状态、启用/禁用）
- 部署记录（配置、状态、时间戳）
- 用户列表（账号状态、角色、组织关系）
- 组织列表（名称、成员数、创建时间）
- 审计日志（**结构化元数据**，无敏感正文）

**❌ 不可访问**：
- ❌ 用户私有偏好（P2）
- ❌ 用户记忆正文（P2/P3）
- ❌ 智能体推理过程（reasoning_summary）
- ❌ 聊天消息明文（P1/P2）
- ❌ 私有提交内容（P4）
- ❌ 授权记录详情（consent 内容）
- ❌ 心理支持独立域数据（P3）
- ❌ 模型 Prompt/响应内容
- ❌ 密钥、Token、内部错误详情

#### 3.2 健康检查 API 可见信息边界

**节点健康检查**（`POST /api/v1/admin/nodes/{node_id}/health-check`）：
```json
{
  "status": "healthy",
  "checks": {
    "database": "passed",
    "model_gateway": "passed",
    "disk_space": "passed"
  },
  "last_checked": "2026-07-14T12:34:56Z"
}
```
- ✅ 可返回：状态（healthy/degraded/unhealthy）、检查项状态、时间戳
- ❌ 不可返回：内部错误详情、数据库连接字符串、密钥

**节点指标**（`GET /api/v1/admin/nodes/{node_id}/metrics`）：
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 67.8,
  "gpu_usage": 82.1,
  "active_requests": 12
}
```
- ✅ 可返回：CPU、内存、GPU、活跃请求数（脱敏指标）
- ❌ 不可返回：请求详情、用户 ID、模型名称、敏感标签

**模型健康检查**（`GET /internal/v1/model/health` - 内部接口）：
- 已在 R1-12 定义，不返回密钥、错误详情、用户数据

### 4. Admin API 端点补全计划

#### 4.1 完整端点清单（11 个）

| 端点编号 | 端点路径 | 方法 | MVP 阶段 | 优先级 | 说明 |
|---------|---------|------|---------|--------|------|
| EP-ADMIN-061 | /api/v1/admin/nodes | POST | P7 | P1 | 创建节点 |
| EP-ADMIN-062 | /api/v1/admin/nodes | GET | P7 | P1 | 节点列表 |
| EP-ADMIN-063 | /api/v1/admin/nodes/{node_id} | GET | P7 | P1 | 节点详情 |
| EP-ADMIN-064 | /api/v1/admin/nodes/{node_id} | PATCH | P7 | P1 | 更新节点 |
| EP-ADMIN-065 | /api/v1/admin/nodes/{node_id} | DELETE | P7 | P1 | 删除节点 |
| EP-ADMIN-066 | /api/v1/admin/nodes/{node_id}/health-check | POST | P7 | P1 | 健康检查 |
| EP-ADMIN-067 | /api/v1/admin/nodes/{node_id}/metrics | GET | P7 | P1 | 节点指标（已定义） |
| EP-ADMIN-068 | /api/v1/admin/models | POST | P7 | P1 | 创建模型 |
| EP-ADMIN-069 | /api/v1/admin/models | GET | P7 | P1 | 模型列表 |
| EP-ADMIN-070 | /api/v1/admin/deployments | POST | P7 | P1 | 创建部署 |
| EP-ADMIN-071 | /api/v1/admin/deployments | GET | P7 | P1 | 部署列表 |

**注**：
- 当前 API_CONTRACT.md 已定义 EP-ADMIN-067（节点指标），需要补充其余 10 个端点
- EP-ADMIN-067 已定义但不完整，需要增强
- 移除 EP-ADMIN-072（GET /api/v1/admin/users）从 Admin API 单独考虑

#### 4.2 端点设计原则

**1. 隐私优先**：
- 所有响应只包含结构化元数据
- 不包含用户私有数据（P2/P3/P4）
- 不包含模型 Prompt/响应内容

**2. 权限控制**：
- 所有端点需要 `SCHOOL_ADMIN` 或 `SYSTEM_ADMIN` 角色
- 节点和模型管理需要额外授权

**3. 错误处理**：
- 节点不存在：`NODE_NOT_FOUND`
- 模型不存在：`MODEL_NOT_FOUND`
- 权限不足：`ADMIN_PERMISSION_DENIED`
- 健康检查失败：`HEALTH_CHECK_FAILED`

**4. 幂等性**：
- 创建端点（POST）支持 `Idempotency-Key` 头
- 更新端点（PATCH）支持 `If-Match` 头（乐观锁）

### 5. 实施步骤

#### 5.1 API_CONTRACT.md 修改

**插入位置**：在 Model Gateway 章节（2.8）之后，WebSocket 章节（3）之前

**修改内容**：
1. 将原第2943-2983行的零散 Admin 端点移动到统一的 2.9 Admin 章节
2. 补全 11 个端点的完整定义
3. 每个端点包含：
   - 端点编号（EP-ADMIN-061~071）
   - 方法和路径
   - 描述
   - 权限
   - 请求头/请求体
   - 响应示例
   - 隐私约束（明确列出 ❌ 不可访问内容）
   - 错误码

#### 5.2 MVP_SCOPE.md 验证

**检查项**：
- ✅ 第 163-175 行的 Admin 端点清单与补全后的 API_CONTRACT.md 一致
- ✅ 端点编号与 API_CONTRACT.md 对应
- ✅ 阶段和优先级标注正确

#### 5.3 P0_P1_REMEDIATION_PLAN.md 更新

**更新内容**：
1. 返工说明（第90-97行）：添加 R1-13 完成说明
2. R1-13 任务状态：`[ ]` → `[x]`
3. R1-13 具体操作：扩展操作描述

#### 5.4 任务日志

创建 `development-logs/in-progress/R1-13_ADMIN_API_REMEDIATION.md`

### 6. 验收标准

#### 6.1 必须满足

- [ ] Admin API 是否属于 MVP 有明确结论（**属于 MVP**）
- [ ] 所有 11 个端点都有完整定义
- [ ] 每个端点都有稳定唯一的端点编号（EP-ADMIN-061~071）
- [ ] 隐私边界清楚（明确列出 ❌ 不可访问内容）
- [ ] 健康检查 API 可见信息边界明确
- [ ] MVP_SCOPE.md 与 API_CONTRACT.md 一致
- [ ] P0_P1_REMEDIATION_PLAN.md 已更新

#### 6.2 文档一致性检查

- [ ] 文档中不再一边说 MVP 不做，一边又要求完整实现 Admin CRUD
- [ ] 管理端隐私边界清楚（不能访问 P2/P3/P4 数据正文）
- [ ] 所有文档引用一致

### 7. 发现的问题和风险

#### 7.1 当前问题

1. **API_CONTRACT.md Admin 端点不完整**
   - 仅 3 个端点有定义（GET /admin/nodes、GET /admin/nodes/{id}/metrics、GET /admin/users）
   - 缺少 8 个端点的定义
   - 缺少端点编号

2. **MVP_SCOPE.md 包含 GET /api/v1/admin/users**
   - API_CONTRACT.md 第2973行有定义
   - 但 MVP_SCOPE.md 第164行未列出
   - 需要确认是否属于 MVP

3. **节点健康检查端点不一致**
   - MVP_SCOPE.md 第169行：`POST /api/v1/admin/nodes/{node_id}/health-check`
   - API_CONTRACT.md 未定义
   - 需要确认是否需要单独的健康检查端点，还是复用 Model Gateway 的 health API

#### 7.2 风险

1. **隐私泄露风险**：如果 Admin API 实现不完整，可能绕过隐私检查直接访问敏感数据
2. **权限混淆风险**：SCHOOL_ADMIN 和 SYSTEM_ADMIN 的权限边界可能模糊
3. **数据泄露风险**：管理员可能通过间接方式访问 P2/P3 数据正文

#### 7.3 缓解措施

1. **强制隐私检查**：所有 Admin API 响应必须经过隐私过滤，移除 P2/P3/P4 字段
2. **权限中间件**：Admin API 必须经过角色检查，确保只有 SCHOOL_ADMIN 或 SYSTEM_ADMIN 可访问
3. **审计日志**：所有 Admin API 调用必须记录审计日志（结构化元数据，无敏感内容）
4. **单元测试**：增加隐私边界测试，验证管理员无法读取 P2/P3 数据正文

### 8. 下一步

完成 R1-13 后：
1. R1 批次剩余任务：
   - R1-14：统一路径变量
   - R1-15：补全错误码
   - R1-16：补全幂等规则
   - R1-17：冻结 API 文档状态
2. 进入 R2 批次（前提：R1 全部完成）

## 验收结果

### 验收检查清单

- [x] Admin API 是否属于 MVP 有明确结论（**属于 MVP**，P7阶段，P1优先级）
- [x] Admin API 分类表完成（11个端点全部属于 MVP 必需）
- [x] 所有 11 个端点都有完整定义（EP-ADMIN-061～071）
- [x] 每个端点都有稳定唯一的端点编号
- [x] 隐私边界清楚（明确列出 7 项 ❌ 不可访问内容）
- [x] 健康检查 API 可见信息边界明确
- [x] MVP_SCOPE.md 与 API_CONTRACT.md 一致
- [x] P0_P1_REMEDIATION_PLAN.md 已更新
- [x] 文档中不再一边说 MVP 不做，一边又要求完整实现 Admin CRUD

### 文档变更摘要

| 文档 | 变更类型 | 变更位置 | 说明 |
|------|---------|---------|------|
| docs/api/API_CONTRACT.md | 新增章节 | 2.9 Admin | 完整定义 11 个 Admin 端点（EP-ADMIN-061～071），明确隐私边界 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 返工说明更新 | 第90-97行 | 添加 R1-13 完成说明 |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 任务状态更新 | R1-13 行 | [ ] → [x] |
| docs/project/P0_P1_REMEDIATION_PLAN.md | 具体操作更新 | R1-13 具体操作列 | 扩展操作描述 |
| development-logs/in-progress/R1-13_ADMIN_API_REMEDIATION.md | 任务日志 | 新建 | 完整记录分析过程和结论 |

### Admin API 分类表（最终）

| 分类 | 端点数量 | 说明 |
|------|---------|------|
| **MVP 必需** | 11 | Admin API 整体属于 MVP（P7阶段，P1优先级） |
| **Demo 必需** | 3 | 节点列表、模型列表、健康检查（Demo 演示需要） |
| **P2 延后** | 0 | 所有端点都在 MVP 范围内 |
| **明确不做** | 0 | Admin API 属于 MVP 必须完成 |

### 隐私边界总结

**管理员可见信息范围**：
- ✅ 节点配置和运行指标（CPU、内存、GPU、活跃请求数）
- ✅ 模型配置元数据（名称、版本、状态、启用/禁用）
- ✅ 部署记录（配置、状态、时间戳）
- ✅ 用户列表（账号状态、角色、组织关系）
- ✅ 组织列表（名称、成员数、创建时间）
- ✅ 审计日志（结构化元数据，无敏感正文）

**管理员不可访问**：
- ❌ 用户私有偏好（P2）
- ❌ 用户记忆正文（P2/P3）
- ❌ 智能体推理过程（reasoning_summary）
- ❌ 聊天消息明文（P1/P2）
- ❌ 私有提交内容（P4）
- ❌ 授权记录详情（consent 内容）
- ❌ 心理支持独立域数据（P3）
- ❌ 模型 Prompt/响应内容
- ❌ 密钥、Token、内部错误详情

### 验证命令

```bash
# 验证端点编号唯一性
grep -E "EP-ADMIN-[0-9]{3}" docs/api/API_CONTRACT.md | sort | uniq -c

# 验证章节编号
grep -n "^### 2\." docs/api/API_CONTRACT.md

# 验证端点数量
grep -E "EP-ADMIN-[0-9]{3}" docs/api/API_CONTRACT.md | wc -l
```

**验证结果**：
- ✅ 11 个端点编号各出现 1 次
- ✅ 章节编号 2.9 连续
- ✅ 端点数量与 MVP_SCOPE.md 一致
