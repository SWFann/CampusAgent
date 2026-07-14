# MVP 范围定义

> **版本**：v1.0  
> **基线日期**：2026-07-13  
> **状态**：已冻结，变更需 ADR  
> **维护者**：开发团队

## 1. 范围概述

本文档定义 CampusAgent MVP（最小可行产品）的明确边界，区分：
- ✅ **MVP必须完成** - 比赛必须展示的能力
- 📦 **可展示但不完整** - 只展示设计，不在MVP中实现
- ❌ **明确不做** - 比赛阶段不实现

## 2. MVP 核心目标

**唯一需要完整可执行的场景**：
> 四名学生在不互相公开预算、禁忌和私人理由的前提下完成宿舍聚餐决策

**验证的核心命题**：
> 不暴露个人真实偏好，也能提高校园集体决策效率

## 3. 页面清单

### 3.1 必须完成（MVP）

| 页面 | 优先级 | 说明 | 验收标准 |
|------|--------|------|---------|
| **登录/注册** | P0 | 用户账号入口 | 可注册、登录、刷新令牌 |
| **首页** | P0 | 最近消息、待处理邀请、当前场景 | 显示场景进度和快速入口 |
| **消息列表** | P0 | 会话列表 | 私聊、群聊、场景会话 |
| **聊天窗口** | P0 | 实时消息、场景卡 | WebSocket实时、场景状态更新 |
| **联系人/组织树** | P0 | 搜索、组织浏览 | 可见性控制生效 |
| **智能体中心** | P0 | 配置、权限、最近调用 | 可修改代理等级和场景权限 |
| **记忆中心** | P0 | 记忆列表、访问记录 | 可查看、修改、删除记忆 |
| **场景中心** | P0 | 场景列表 | 聚餐可用，其余标注"即将上线" |
| **私有偏好页** | P0 ⭐ | **核心页面** | 隐私说明、表单提交、不进入聊天 |
| **聚餐结果页** | P0 ⭐ | **核心页面** | 候选、匹配分、投票、确认 |
| **审计日志页** | P0 | 用户可查自己的访问记录 | 结构化记录，无敏感内容 |
| **管理后台-用户** | P1 | 用户列表、状态管理 | 无私有偏好读取入口 |
| **管理后台-组织** | P1 | 组织树、成员管理 | 可见性控制 |
| **管理后台-模型** | P1 | 模型配置列表 | 只展示配置，不展示敏感调用 |
| **管理后台-节点** | P1 | 节点状态、健康检查 | 只展示运行指标 |
| **管理后台-监控** | P1 | 指标面板 | 脱敏指标，不含敏感标签 |

**优先级说明**：
- **P0**：必须在 P10 完成前交付
- **P1**：必须在 P13 交付前完成

### 3.2 可展示但不完整（非MVP）

| 页面 | 处理方式 | 说明 |
|------|---------|------|
| **课堂讨论** | 展示卡 + "即将上线" | 只展示场景设计，不实现功能 |
| **社团策划** | 展示卡 + "即将上线" | 同上 |
| **学习小组** | 展示卡 + "即将上线" | 同上 |
| **新生助手** | 展示卡 + "即将上线" | 同上 |
| **情绪记录** | 展示卡 + "概念展示" | 展示设计理念，不实现功能 |

**展示要求**：
- 可点击进入设计说明页
- 明确标注"概念"或"即将上线"
- 不伪装为可用功能
- 不提供功能入口

### 3.3 明确不做（非MVP）

| 页面/功能 | 原因 |
|----------|------|
| 移动端原生应用 | 只做 Web |
| 完整教务系统 | 超出范围 |
| 自动心理诊断 | 隐私风险过高 |
| 全量聊天情绪监控 | 隐私风险过高 |
| 课程选课系统 | 超出范围 |
| 成绩管理 | 超出范围 |
| 支付系统 | 高风险，MVP不开放 |
| 第三方应用市场 | 超出范围 |

## 4. API 端点清单

### 4.1 必须完成（MVP）

基于词汇表和模块边界，MVP 必须实现的 API：

#### Auth（P3阶段）
- ✅ `POST /api/v1/auth/register` - 注册
- ✅ `POST /api/v1/auth/login` - 登录
- ✅ `POST /api/v1/auth/refresh` - 刷新令牌
- ✅ `POST /api/v1/auth/logout` - 注销
- ✅ `GET /api/v1/auth/me` - 当前用户信息

#### User（P3阶段）
- ✅ `GET /api/v1/users/{user_id}` - 用户详情
- ✅ `PATCH /api/v1/users/{user_id}` - 更新用户资料
- ✅ `GET /api/v1/users/{user_id}/organizations` - 用户组织列表
- ✅ `GET /api/v1/users/{user_id}/agent` - 用户智能体

#### Organization（P4阶段）
- ✅ `POST /api/v1/organizations` - 创建组织
- ✅ `GET /api/v1/organizations` - 组织列表
- ✅ `GET /api/v1/organizations/{org_id}` - 组织详情
- ✅ `PATCH /api/v1/organizations/{org_id}` - 更新组织
- ✅ `DELETE /api/v1/organizations/{org_id}` - 删除组织
- ✅ `POST /api/v1/organizations/{org_id}/members` - 添加成员
- ✅ `GET /api/v1/organizations/{org_id}/members` - 成员列表
- ✅ `PATCH /api/v1/organizations/{org_id}/members/{user_id}` - 更新成员角色
- ✅ `DELETE /api/v1/organizations/{org_id}/members/{user_id}` - 移除成员
- ✅ `POST /api/v1/organizations/{org_id}/join` - 加入组织
- ✅ `POST /api/v1/organizations/{org_id}/leave` - 退出组织

#### Directory（P4阶段）
- ✅ `GET /api/v1/directory/search` - 搜索用户/组织
- ✅ `GET /api/v1/directory/tree` - 组织树
- ✅ `GET /api/v1/directory/recommended` - 推荐（占位）

#### Conversation（P5阶段）
- ✅ `POST /api/v1/conversations` - 创建会话
- ✅ `GET /api/v1/conversations` - 会话列表
- ✅ `GET /api/v1/conversations/{conv_id}` - 会话详情
- ✅ `PATCH /api/v1/conversations/{conv_id}` - 更新会话
- ✅ `POST /api/v1/conversations/{conv_id}/participants` - 添加参与者
- ✅ `DELETE /api/v1/conversations/{conv_id}/participants/{participant_id}` - 移除参与者
- ✅ `GET /api/v1/conversations/{conv_id}/messages` - 消息列表
- ✅ `POST /api/v1/conversations/{conv_id}/messages` - 发送消息
- ✅ `DELETE /api/v1/messages/{message_id}` - 删除消息

#### Agent（P6阶段）
- ✅ `GET /api/v1/agents/me` - 我的智能体
- ✅ `PATCH /api/v1/agents/me` - 更新智能体配置
- ✅ `POST /api/v1/agents/me/chat` - 与智能体对话
- ✅ `GET /api/v1/agents/me/permissions` - 查看权限
- ✅ `PATCH /api/v1/agents/me/permissions` - 修改权限
- ✅ `GET /api/v1/agents/me/runs` - 执行历史

#### Memory（P6阶段）
- ✅ `GET /api/v1/memories` - 记忆列表
- ✅ `POST /api/v1/memories` - 创建记忆
- ✅ `GET /api/v1/memories/{memory_id}` - 记忆详情
- ✅ `PATCH /api/v1/memories/{memory_id}` - 更新记忆
- ✅ `DELETE /api/v1/memories/{memory_id}` - 删除记忆
- ✅ `GET /api/v1/memories/access-log` - 访问记录
- ✅ `POST /api/v1/memories/export` - 导出记忆

#### Scene（P8-P9阶段）
- ✅ `GET /api/v1/scenes` - 场景列表
- ✅ `GET /api/v1/scenes/{scene_key}` - 场景详情
- ✅ `POST /api/v1/scene-instances` - 创建场景实例
- ✅ `GET /api/v1/scene-instances/{instance_id}` - 场景详情
- ✅ `POST /api/v1/scene-instances/{instance_id}/participants` - 添加参与者
- ✅ `POST /api/v1/scene-instances/{instance_id}/consent` - 授权
- ✅ `POST /api/v1/scene-instances/{instance_id}/private-submission` - **私有提交** ⭐
- ✅ `POST /api/v1/scene-instances/{instance_id}/start` - 开始处理
- ✅ `GET /api/v1/scene-instances/{instance_id}/candidates` - 候选列表
- ✅ `POST /api/v1/scene-instances/{instance_id}/vote` - 投票
- ✅ `POST /api/v1/scene-instances/{instance_id}/confirm` - 确认结果
- ✅ `POST /api/v1/scene-instances/{instance_id}/cancel` - 取消场景

#### Model Gateway（内部，P7阶段）
- ✅ `POST /internal/v1/model/chat` - 模型调用（内部）
- ✅ `POST /internal/v1/model/embedding` - 嵌入向量（内部）
- ✅ `GET /internal/v1/model/health` - 健康检查（内部）

#### Admin（P7阶段）
- ✅ `POST /api/v1/admin/nodes` - 创建节点
- ✅ `GET /api/v1/admin/nodes` - 节点列表
- ✅ `GET /api/v1/admin/nodes/{node_id}` - 节点详情
- ✅ `PATCH /api/v1/admin/nodes/{node_id}` - 更新节点
- ✅ `DELETE /api/v1/admin/nodes/{node_id}` - 删除节点
- ✅ `POST /api/v1/admin/nodes/{node_id}/health-check` - 健康检查
- ✅ `GET /api/v1/admin/nodes/{node_id}/metrics` - 节点指标
- ✅ `POST /api/v1/admin/models` - 创建模型
- ✅ `GET /api/v1/admin/models` - 模型列表
- ✅ `POST /api/v1/admin/deployments` - 创建部署
- ✅ `GET /api/v1/admin/deployments` - 部署列表

**总计**：62 个 MVP 端点

### 4.2 可展示但不完整（非MVP）

| 端点 | 处理方式 |
|------|---------|
| 课堂讨论相关 API | 不实现，仅文档占位 |
| 社团策划相关 API | 不实现，仅文档占位 |
| 学习小组匹配 API | 不实现，仅文档占位 |
| 新生助手 API | 不实现，仅文档占位 |
| 情绪记录 API | 不实现，仅文档占位 |
| 支付/报名 API | 不实现，明确说明MVP不开放L4 |

### 4.3 明确不做（非MVP）

- ❌ 第三方 OAuth 集成（只做邮箱/学号）
- ❌ 双因素认证（2FA）
- ❌ 短信验证
- ❌ 文件上传/存储（MVP用URL）
- ❌ 富文本编辑器（只做纯文本）
- ❌ 多租户架构
- ❌ 微服务拆分

## 5. 场景清单

### 5.1 必须完成（MVP）

| 场景 | 场景Key | 优先级 | 说明 |
|------|---------|--------|------|
| **宿舍聚餐协商** | `meal_planning` | P0 ⭐ | 唯一需要完整可执行的场景 |

**聚餐场景必须验证的核心流程**：
1. 场景创建和参与者邀请
2. L2 授权确认
3. 私有偏好提交
4. 偏好胶囊生成
5. 候选餐厅生成
6. 私有评分和聚合
7. 投票和确认
8. 临时数据清理
9. 长期记忆二次确认

### 5.2 可展示但不完整（非MVP）

| 场景 | 场景Key | 处理方式 |
|------|---------|---------|
| 课堂讨论 | `class_discussion` | 场景卡片 + 设计说明 |
| 社团活动策划 | `club_planning` | 场景卡片 + 设计说明 |
| 学习小组匹配 | `study_group` | 场景卡片 + 设计说明 |
| 新生校园助手 | `freshman_helper` | 场景卡片 + 设计说明 |
| 情绪记录 | `emotion_journal` | 场景卡片 + 概念展示 |

**展示要求**：
- 场景中心显示卡片
- 标注"即将上线"或"概念展示"
- 点击显示设计文档
- **不提供功能入口**

### 5.3 明确不做（非MVP）

- ❌ 完整教务系统集成
- ❌ 课程表自动同步
- ❌ 成绩查询
- ❌ 图书馆系统集成
- ❌ 校园卡/支付集成
- ❌ 门禁系统集成
- ❌ 自动心理诊断

## 6. 管理能力清单

### 6.1 必须完成（MVP）

| 能力 | 优先级 | 说明 | 隐私约束 |
|------|--------|------|---------|
| **用户管理** | P1 | 列表、创建、禁用、删除 | 无私有内容读取入口 |
| **组织管理** | P1 | 组织树、成员管理 | 可见性控制生效 |
| **模型管理** | P1 | 模型配置、启用/禁用 | 只展示配置元数据 |
| **节点管理** | P1 | 节点注册、健康检查 | 只展示运行指标 |
| **运行监控** | P1 | 请求量、延迟、错误率 | **脱敏**，不含敏感标签 |
| **安全审计** | P1 | 审计日志查询 | 结构化元数据，无敏感正文 |

**关键约束**：
- ✅ 管理员可以管理模型、节点、用户、组织
- ❌ 管理员**不能**读取用户私有偏好
- ❌ 管理员**不能**读取个人记忆正文
- ❌ 管理员**不能**查看智能体辩论过程
- ❌ 管理员**不能**访问聊天明文

### 6.2 可展示但不完整（非MVP）

| 能力 | 处理方式 |
|------|---------|
| 推荐联系人算法 | 只做简单规则，不做复杂推荐 |
| 数据导出（批量） | 只支持个人数据导出 |
| 组织审批流 | 简化处理，手动审批 |
| 复杂统计报表 | 只做基础指标 |

### 6.3 明确不做（非MVP）

- ❌ 自动化风险画像
- ❌ 学生行为分析
- ❌ 聊天内容监控
- ❌ 心理状态自动评估
- ❌ 成绩/出勤率统计
- ❌ 违规行为自动检测

## 7. 范围压缩顺序

> 如果比赛截止时间不足，按以下顺序裁剪。**越靠前越先裁**。

### 7.1 可裁剪项

**第1优先级（先裁）**：
1. MinIO、Prometheus/Grafana/DCGM 的真实部署
   - 保留接口和轻量指标
   - 不部署完整监控栈

2. 外部真实模型和真实边缘 GPU 节点
   - 保留 Mock、规则引擎
   - 保留模拟指标
   - 不依赖真实硬件

3. 推荐联系人、复杂审批、资料导出等非演示能力
   - 简化推荐算法
   - 手动审批代替流程

4. 课堂、社团、学习小组、新生助手和情绪记录的展示页细节
   - 只保留场景卡
   - 不实现交互

5. 复杂 Agent 对话和长期个性化
   - 只保留场景所需的个人 Agent、授权和记忆
   - 不做长期记忆学习

6. Refresh Token 高级轮换
   - 简化为安全、明确、测试过的 MVP 策略

### 7.2 不可裁剪项

**以下功能是硬约束，即使在时间不足时也不能砍**：

| 能力 | 原因 |
|------|------|
| ✅ 认证与基本 RBAC | 安全基础 |
| ✅ 私有提交隔离 | **核心隐私控制** |
| ✅ 字段加密 | **核心隐私控制** |
| ✅ 逐场景授权 | **核心隐私控制** |
| ✅ 管理员拒绝 | **核心隐私控制** |
| ✅ 日志脱敏 | **核心隐私控制** |
| ✅ 不保存思维链 | **核心隐私控制** |
| ✅ 人工确认 | **核心隐私控制** |
| ✅ TTL 清理 | **核心隐私控制** |
| ✅ Mock/规则备用 | **演示可用性** |
| ✅ 核心隐私 E2E | **演示可信度** |

## 8. 验收标准

### 8.1 MVP 完成标志

- [ ] 四名学生可以注册并登录
- [ ] 可以创建宿舍组织和群聊
- [ ] 每人可以提交私有偏好
- [ ] 群聊不展示个人偏好
- [ ] 系统生成3个候选餐厅
- [ ] 用户可以投票和确认
- [ ] 场景结束后临时数据被清理
- [ ] 管理员后台无私有内容读取入口

### 8.2 演示验证标志

- [ ] 5分钟内完成完整演示
- [ ] 可证明 A 看不到 B 的偏好
- [ ] 可证明管理员看不到私有内容
- [ ] 可证明辩论过程不保存
- [ ] 可证明临时数据被清理
- [ ] 可断网完成核心流程（Mock模式）

## 9. 范围变更规则

### 9.1 允许的变更

在以下条件下可以调整范围：
1. 通过 ADR 记录变更原因
2. 不影响核心隐私控制
3. 不影响聚餐场景完整性
4. 团队评审通过

### 9.2 禁止的变更

- ❌ 在未评估隐私影响的情况下扩展场景
- ❌ 为方便演示给管理员开放私有数据
- ❌ 跳过私有提交隔离
- ❌ 跳过字段加密
- ❌ 跳过权限测试

## 10. 相关文档

- [完整项目计划书](../product/CampusAgent_Project_Plan.md)
- [架构与模块边界](../architecture/MODULE_BOUNDARIES.md)
- [Demo 规范与验收](../demo/DEMO_SPEC.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)
- [开发计划表](../development/DEVELOPMENT_PLAN.md)

---

**下一步**：P0-03（绘制用户旅程，依赖本文件）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-13 | 初始版本 | - |
