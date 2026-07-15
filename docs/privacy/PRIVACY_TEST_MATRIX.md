# 隐私测试矩阵

> **版本**：v1.0  
> **基线日期**：2026-07-14  
> **状态**：已冻结  
> **维护者**：开发团队

## 1. 测试矩阵说明

本文档基于权限矩阵和威胁模型，定义完整的隐私测试用例。

**测试分类**：
- **授权测试**：验证允许的访问被正确授权
- **拒绝测试**：验证拒绝的访问被正确拦截
- **清理测试**：验证临时数据被正确清理
- **日志测试**：验证日志中无敏感内容

### 1.1 正式测试 ID 注册规则（R1-29 建立）

1. 本文件是正式测试 ID 唯一注册表。
2. 一个 ID 只能正式定义一次。
3. 原有 51 个 ID 不得删除、重编号或改变语义。
4. ST-001～ST-005 保留。
5. THREAT_MODEL 中 ST-01～ST-08 已删除，不得恢复 ST-09。
6. 新增前缀：
   - **PI**：Prompt Injection
   - **RP**：Replay/Idempotency
   - **MR**：Model Routing
   - **EN**：Edge Node
   - **FC**：Fail-Closed（R1-30 新增）
7. 定义状态 `defined`：测试场景和预期已文档化。
8. 执行状态 `not_run`：无执行证据。
9. 范围标记（如 `PT-001～PT-008`）包含首尾全部连续 ID；自动检查必须展开范围，不得按字符串匹配统计。

---

## 2. 主体×资源×动作矩阵

### 2.1 主体（测试角色）

| 主体ID | 全局角色 | 组织角色 | 说明 |
|--------|---------|---------|------|
| S-01 | STUDENT | OWNER | 宿舍发起人（林晓） |
| S-02 | STUDENT | MEMBER | 宿舍成员（陈宇） |
| S-03 | STUDENT | MEMBER | 宿舍成员（周宁） |
| S-04 | STUDENT | MEMBER | 宿舍成员（许然） |
| S-05 | TEACHER | - | 教师 |
| S-06 | COUNSELOR | - | 心理支持人员 |
| S-07 | ORG_ADMIN | - | 组织管理员 |
| S-08 | SCHOOL_ADMIN | - | 校方管理员 |
| S-09 | SYSTEM_ADMIN | - | 系统管理员 |

### 2.2 资源类型

| 资源ID | 资源类型 | 敏感等级 |
|--------|---------|---------|
| R-01 | User | P1 |
| R-02 | MemoryItem | P2/P3 |
| R-03 | PrivateSceneSubmission | **P4** |
| R-04 | PrivateCandidateEvaluation | **P4** |
| R-05 | Conversation | P1/P2 |
| R-06 | Message | P1 |
| R-07 | SceneInstance | P1 |
| R-08 | Agent | P1/P2 |

### 2.3 动作

| 动作ID | 动作 | 说明 |
|--------|------|------|
| A-01 | read | 读取 |
| A-02 | create | 创建 |
| A-03 | update | 更新 |
| A-04 | delete | 删除 |
| A-05 | list | 列表 |
| A-06 | search | 搜索 |

---

## 3. 核心隐私测试用例

### 3.1 私有提交访问控制（P4）

| 测试ID | 主体 | 资源 | 动作 | 预期结果 | 说明 |
|--------|------|------|------|---------|------|
| **PT-001** | S-02 | R-03 | A-01 | **拒绝** | A无法读取B的私有提交 |
| **PT-002** | S-03 | R-03 | A-01 | **拒绝** | 参与者C无法读取参与者D的提交 |
| **PT-003** | S-07 | R-03 | A-01 | **拒绝** | ORG_ADMIN无法读取 |
| **PT-004** | S-08 | R-03 | A-01 | **拒绝** | SCHOOL_ADMIN无法读取 |
| **PT-005** | S-09 | R-03 | A-01 | **拒绝** | SYSTEM_ADMIN也无法读取 |
| **PT-006** | S-01 | R-03 | A-01 | **允许** | 提交者可以读取自己的 |
| **PT-007** | 系统 | R-03 | A-04 | **允许** | 场景结束后系统清理 |
| **PT-008** | 系统 | R-04 | A-04 | **允许** | 场景结束后清理私有评价 |

**执行方式**：
- PT-001 到 PT-005：必须全部拒绝
- PT-006：提交者可以读取
- PT-007/PT-008：验证清理

---

### 3.2 记忆访问控制（P2/P3）

| 测试ID | 主体 | 资源 | 动作 | 预期结果 | 说明 |
|--------|------|------|------|---------|------|
| **PT-101** | S-02 | R-02 | A-01 | **拒绝** | B无法读取A的记忆 |
| **PT-102** | S-07 | R-02 | A-01 | **拒绝** | 管理员无法读取 |
| **PT-103** | S-08 | R-02 | A-01 | **拒绝** | 校方无法读取 |
| **PT-104** | S-09 | R-02 | A-01 | **拒绝** | 系统管理员也无法读取 |
| **PT-105** | S-01 | R-02 | A-01 | **允许** | 所有者可以读取自己的 |
| **PT-106** | S-01 | R-02 | A-02 | **允许** | 所有者可以创建 |
| **PT-107** | S-01 | R-02 | A-04 | **允许** | 所有者可以删除 |

**四重检查**：
- owner_user_id = current_user.id
- purpose 明确
- category 允许
- consent 有效

---

### 3.3 群聊权限测试

| 测试ID | 主体 | 资源 | 动作 | 预期结果 | 说明 |
|--------|------|------|------|---------|------|
| **PT-201** | S-04 | R-06 | A-01 | **允许** | 参与者可读取群聊消息 |
| **PT-202** | S-04 | R-05 | A-05 | **允许** | 可列出参与的群聊 |
| **PT-203** | S-07 | R-06 | A-01 | **拒绝** | ORG_ADMIN 尝试读取会话聊天明文 → 拒绝；ORG_ADMIN 可管理会话元数据，但不能读取聊天正文 |
| **PT-204** | S-04 | R-03 | A-05 | **拒绝** | 普通消息接口查不到私有提交 |

---

### 3.4 管理后台权限测试

| 测试ID | 主体 | 资源 | 动作 | 预期结果 | 说明 |
|--------|------|------|------|---------|------|
| **PT-301** | S-08 | R-03 | A-01 | **拒绝** | 无私有偏好读取入口 |
| **PT-302** | S-08 | R-02 | A-01 | **拒绝** | 无记忆正文读取入口 |
| **PT-303** | S-08 | R-06 | A-01 | **拒绝** | 无聊天明文读取入口 |
| **PT-304** | S-08 | 用户列表 | A-05 | **允许** | 可查看用户列表 |
| **PT-305** | S-08 | 节点指标 | A-01 | **允许** | SCHOOL_ADMIN 可查看脱敏节点指标；不返回节点凭据；不返回 Prompt、模型输入或完整响应；不代表可以创建、修改、删除节点 |
| **PT-306** | S-09 | R-03 | A-01 | **拒绝** | 系统管理员同样无权限 |

---

## 4. 场景隐私测试

### 4.1 场景事件隐私

| 测试ID | 测试场景 | 预期结果 |
|--------|---------|---------|
| **ST-001** | 订阅场景事件，检查 `scene.updated` 事件 | 不含任何个人偏好 |
| **ST-002** | 订阅场景事件，检查 `scene.result.generated` 事件 | 不含个人偏好和辩论过程 |
| **ST-003** | 检查场景结果中的聚合理由 | 不指认具体成员 |
| **ST-004** | 检查私有提交是否进入消息表 | 不存在 |
| **ST-005** | 检查私有提交是否进入WebSocket | 不发送 |

---

### 4.2 场景清理测试

| 测试ID | 测试场景 | 预期结果 |
|--------|---------|---------|
| **CL-001** | 场景完成后查询 PrivateSceneSubmission | encrypted_payload 已删除 |
| **CL-002** | 场景完成后查询 PrivateSceneSubmission | capsule_payload 已删除 |
| **CL-003** | 场景完成后查询 PrivateCandidateEvaluation | 已删除或已过期 |
| **CL-004** | 场景完成后查询 SceneResult | 仍存在（最终结果保留） |
| **CL-005** | 场景取消后查询临时数据 | 已清理 |

**验证SQL**：
```sql
-- 验证原始偏好已删除
SELECT COUNT(*) FROM private_scene_submissions
WHERE scene_instance_id = 'xxx' AND deleted_at IS NULL;
-- 期望：0

-- 验证胶囊已删除
SELECT COUNT(*) FROM private_scene_submissions
WHERE scene_instance_id = 'xxx' AND capsule_payload IS NOT NULL;
-- 期望：0

-- 验证最终结果保留
SELECT COUNT(*) FROM scene_results
WHERE scene_instance_id = 'xxx';
-- 期望：1
```

---

## 5. 日志隐私测试

### 5.1 敏感内容扫描

| 测试ID | 扫描目标 | 期望发现 | 定义状态 | 执行状态 | 实际结果 |
|--------|---------|---------|---------|---------|---------|
| **LG-001** | 所有日志文件 | 无 "budget_max: 100" 等 | defined | not_run | — |
| **LG-002** | 所有日志文件 | 无 "不吃香菜" 等禁忌 | defined | not_run | — |
| **LG-003** | 所有日志文件 | 无完整 Prompt | defined | not_run | — |
| **LG-004** | 所有日志文件 | 无完整模型响应 | defined | not_run | — |
| **LG-005** | 所有日志文件 | 无思维链 | defined | not_run | — |

**扫描方式**：
- 自动扫描脚本
- 关键词匹配：budget、preference、restriction 等
- 人工审查关键日志

### 5.2 允许记录的元数据

| 测试ID | 记录内容 | 允许？ |
|--------|---------|-------|
| **LG-101** | `scene_id=xxx, user_id_hash=hash, payload_size=256` | ✅ |
| **LG-102** | `model=gpt-4, tokens=150, latency=2300ms` | ✅ |
| **LG-103** | `consent_granted=true, purpose=meal_planning` | ✅ |
| **LG-104** | `budget_max=100, cuisines=[日料]` | ❌ |

---

## 6. 授权撤销测试

| 测试ID | 测试场景 | 预期结果 |
|--------|---------|---------|
| **REV-001** | 撤销授权后，尝试提交私有偏好 | 拒绝 |
| **REV-002** | 撤销授权后，尝试读取记忆 | 拒绝 |
| **REV-003** | 撤销授权后，尝试访问场景 | 拒绝（或只读） |
| **REV-004** | 撤销授权后，立即生效 | 不接受旧的授权凭证 |

---

## 7. 数据导出测试

| 测试ID | 测试场景 | 预期结果 |
|--------|---------|---------|
| **EXP-001** | 用户导出自己的数据 | 包含自己的所有数据 |
| **EXP-002** | 用户导出时检查是否包含他人数据 | 不含他人数据 |
| **EXP-003** | 用户导出时检查是否包含私有提交 | 不含（除非自己） |

---

## 8. Prompt 注入测试（R1-29 新增）

| ID | 威胁 | 场景 | 预期结果 | 验证控制 | 阶段 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|---|---|
| **PI-001** | T-04 | 原始自由文本直接进入模型 | 拒绝或先最小化、结构化 | Prompt 最小化、结构化胶囊 | P3 | defined | not_run |
| **PI-002** | T-04 | 偏好胶囊包含注入指令 | 只作为数据，不改变系统规则 | 结构化输出、系统提示隔离 | P3 | defined | not_run |
| **PI-003** | T-04、T-03 | 响应包含系统提示、记忆正文或私有提交 | Schema/敏感字段检查拒绝 | 输出验证、Schema 校验 | P3 | defined | not_run |
| **PI-004** | T-04 | Schema 合法但包含成员指认、敏感语义或恶意 URL | 拒绝或安全重建 | 输出验证、字段白名单 | P3 | defined | not_run |
| **PI-005** | T-04、T-03 | 扫描注入请求和响应日志 | 无 Prompt、私有偏好、系统指令和完整响应 | 日志脱敏、敏感字段过滤 | P3 | defined | not_run |

---

## 9. 重放与幂等性测试（R1-29 新增）

| ID | 威胁 | 场景 | 预期结果 | 验证控制 | 阶段 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|---|---|
| **RP-001** | T-05 | 相同幂等键+相同请求体 | 同一结果，不重复副作用 | Idempotency-Key | P2 | defined | not_run |
| **RP-002** | T-05 | 相同幂等键+不同请求体 | IDEMPOTENCY_CONFLICT | 幂等冲突检测 | P2 | defined | not_run |
| **RP-003** | T-05 | 重复投票、确认或私有提交 | 无重复记录和非法状态转换 | 场景状态机 | P2 | defined | not_run |
| **RP-004** | T-05 | 轮换后旧 Refresh Token 重放 | 拒绝并按契约处理 token family | Token 轮换、重放检测 | P2 | defined | not_run |
| **RP-005** | T-05 | 并发使用同一幂等键 | 只产生一次副作用 | 幂等作用域锁定 | P2 | defined | not_run |

---

## 10. 模型路由测试（R1-29 新增）

| ID | 威胁 | 场景 | 预期结果 | 验证控制 | 阶段 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|---|---|
| **MR-001** | T-08 | P3/P4 原始正文路由外部模型 | 拒绝，不调用外部 Provider | 隐私上下文路由策略 | P2 | defined | not_run |
| **MR-002** | T-08 | ENABLE_EXTERNAL_MODEL=false | 不调用外部 Provider | 默认禁用外部模型 | P2 | defined | not_run |
| **MR-003** | T-08 | privacy_context 缺失、无效或授权撤销 | 失败关闭，不发送模型请求 | 隐私上下文校验、失败关闭 | P2 | defined | not_run |
| **MR-004** | T-08、T-09 | 本地节点失败 | 只降级到同等隐私能力的 Mock/规则引擎，不得降级外部模型或 HTTP | 安全降级策略 | P7 | defined | not_run |
| **MR-005** | T-08、T-03、T-09 | 模型网关日志扫描 | 无原始输入、Prompt、完整响应和节点凭据 | 日志脱敏、元数据记录 | P2 | defined | not_run |

---

## 11. 边缘节点测试（R1-29 新增）

| ID | 威胁 | 场景 | 预期结果 | 验证控制 | 阶段 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|---|---|
| **EN-001** | T-09 | 非 SYSTEM_ADMIN 执行 Node POST/PATCH/DELETE | ADMIN_PERMISSION_DENIED，无写入 | 节点管理权限 | P7 | defined | not_run |
| **EN-002** | T-09 | 生产提交 HTTP endpoint | INVALID_ENDPOINT，不连接 | 安全传输、HTTPS 强制 | P7 | defined | not_run |
| **EN-003** | T-09 | loopback、link-local、metadata、multicast、unspecified 地址 | INVALID_ENDPOINT | SSRF 防护、地址校验 | P7 | defined | not_run |
| **EN-004** | T-09 | DNS 解析或重定向指向禁止地址 | 拒绝，防 DNS rebinding | DNS 重新校验、重定向禁止 | P7 | defined | not_run |
| **EN-005** | T-09 | 缺失、无效、过期、撤销或错误作用域凭据 | 节点认证失败 | 节点身份认证 | P7 | defined | not_run |
| **EN-006** | T-09、T-08 | 发给节点的请求包含非最小化数据或 P3/P4 原文 | 拒绝 | 数据最小化、隐私上下文 | P7 | defined | not_run |
| **EN-007** | T-09、T-04 | 节点返回缺字段、错误类型、未知字段或非法枚举 | Schema 检查拒绝或安全降级 | 输出验证、Schema 校验 | P7 | defined | not_run |
| **EN-008** | T-09 | 节点访问 PostgreSQL、Redis、业务 API 或未授权外部地址 | 网络策略拒绝 | 网络隔离 | P7 | defined | not_run |
| **EN-009** | T-09、T-03 | 扫描数据库、API、日志、错误、指标和备份 | 凭据加密存储且不泄露；无 Prompt、输入正文和完整响应 | 凭据保护、日志脱敏 | P7 | defined | not_run |
| **EN-010** | T-09 | 隔离、禁用或熔断节点继续领取任务 | 不再接收任务 | 健康和异常处理、隔离 | P7 | defined | not_run |
| **EN-011** | T-09 | 凭据轮换后使用旧凭据 | 拒绝 | 凭据轮换、撤销 | P7 | defined | not_run |
| **EN-012** | T-09、T-04 | 节点返回恶意 URL、工具调用、成员指认、私有偏好或操纵内容 | 输出验证拒绝 | 输出验证、字段白名单 | P7 | defined | not_run |

---

## 12. 隐私失败关闭测试（R1-30）

| ID | 场景 | 预期结果 | 验证控制 | 阶段 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|---|
| **FC-001** | 权限检查失败（用户访问他人 Memory/Conversation/Scene、管理员读 P2/P3 正文、非 SYSTEM_ADMIN 执行 Node 写操作） | 拒绝，不返回敏感数据 | 授权失败关闭 | P2 | defined | not_run |
| **FC-002** | 授权撤销或 consent_scope 失效（consent_scope 缺失/过期/无效、Agent 使用旧授权） | 拒绝继续处理，不调用模型 | 授权撤销失败关闭 | P2 | defined | not_run |
| **FC-003** | P2/P3/P4 解密失败（KMS 不可用、加密字段损坏、key_id 不匹配） | 停止处理，不返回密文或部分明文 | 解密失败关闭 | P2 | defined | not_run |
| **FC-004** | tenant/org/scene/owner 不一致（organization_id 不匹配、conversation_id 与 user_id 不匹配） | 拒绝跨边界访问 | 隔离失败关闭 | P2 | defined | not_run |
| **FC-005** | privacy_context 缺失或非法（data_classification/purpose/retention/consent_scope/allowed_outputs 缺失） | 失败关闭，不调用模型或节点 | 隐私上下文失败关闭 | P3 | defined | not_run |
| **FC-006** | 本地模型或节点不可用（ENABLE_EXTERNAL_MODEL=false、外部 Provider 不满足隐私要求） | P3/P4 不公开降级到外部模型 | 模型路由失败关闭 | P7 | defined | not_run |
| **FC-007** | Prompt 或模型输出校验失败（Prompt 含 P3/P4 原文、输出含私密字段/成员指认/恶意 URL） | 拒绝或安全重建，不推送非法输出 | 输出校验失败关闭 | P3/P7 | defined | not_run |
| **FC-008** | WebSocket 认证、Origin 或订阅授权失败（access_token 缺失/过期、Origin 不匹配、订阅未授权） | 握手/订阅失败，不推送事件 | WebSocket 失败关闭 | P5 | defined | not_run |
| **FC-009** | 幂等冲突或重放（相同 Idempotency-Key 不同请求体、重复私有提交/投票/确认、旧 refresh token 重放） | 拒绝冲突，不产生重复副作用 | 重放失败关闭 | P2 | defined | not_run |
| **FC-010** | Edge Node 凭据、endpoint、Schema 或隔离失败（凭据无效/过期、endpoint 为 HTTP、指向禁止地址、返回非法 Schema） | 拒绝连接/拒绝结果/隔离节点 | 边缘节点失败关闭 | P7 | defined | not_run |
| **FC-011** | 安全关键审计写入失败（权限拒绝事件审计失败、Node 写操作审计失败、Model Gateway 隐私路由审计失败） | 高风险写操作失败关闭或告警 | 审计失败关闭 | P8 | defined | not_run |
| **FC-012** | 临时私有数据清理失败（Scene 结束后清理失败、私有胶囊删除失败、导出文件过期删除失败） | 标记失败并阻止后续读取，TTL 细节留 R1-31 | 清理失败关闭 | P8/P12 | defined | not_run |

---

## 13. 保留策略测试（R1-31 新增）

以下 10 个测试验证数据保留策略（TTL、清理触发、删除方法、可恢复性、可导出性）是否与 `DATA_INVENTORY.md §13 数据保留策略矩阵（R1-31 权威口径）` 一致。

| 测试 ID | 测试场景 | 预期结果 | 检测的威胁 | 阶段 | 定义状态 | 执行状态 |
|---------|---------|---------|-----------|------|---------|---------|
| **RT-001** | Scene 结束后临时私有数据（私有提交内容、Agent 中间记忆、WebSocket 临时缓冲）是否在规定时间内被删除 | Scene 终止后立即删除，TTL 兜底 24h | T-01、T-07 | P8 | defined | not_run |
| **RT-002** | 私有胶囊删除是否真正删除且不可恢复 | 物理删除，删除后 404，不可恢复 | T-07 | P8 | defined | not_run |
| **RT-003** | 导出文件过期删除是否生效 | 生成后 24h 自动删除，过期后 404 | T-07 | P8 | defined | not_run |
| **RT-004** | AgentRun 记录保留 180 天后是否自动删除 | 180 天后自动删除，删除前不影响查询 | T-07 | P12 | defined | not_run |
| **RT-005** | AuditLog 保留 180 天后是否自动删除 | 180 天后自动删除，删除前可查询 | T-07 | P12 | defined | not_run |
| **RT-006** | Memory 记录在用户/组织删除后是否级联删除 | 用户删除触发 Memory 级联删除，组织删除触发组织 Memory 级联删除 | T-03、T-04、T-08 | P12 | defined | not_run |
| **RT-007** | 评价数据在评价关闭后是否按策略归档/删除 | 关闭后归档 180 天，到期删除 | T-03、T-06、T-09 | P12 | defined | not_run |
| **RT-008** | Token/Session 在过期或撤销后是否立即失效 | 过期后立即拒绝，撤销后立即拒绝，不可重放 | T-02、T-05 | P5 | defined | not_run |
| **RT-009** | 审计日志、AgentRun 记录是否可导出 | 管理员可导出，普通用户不可导出审计日志 | T-01、T-06、T-08 | P12 | defined | not_run |
| **RT-010** | 日志脱敏后是否可安全导出 | 日志导出前脱敏，脱敏后不含 P3/P4 字段 | T-03、T-09 | P12 | defined | not_run |

---

## 14. 威胁—控制—测试追踪矩阵（R1-31 更新）

### 14.1 正向映射：威胁 → 测试

| 威胁 | 风险 | 计划控制 | 测试 ID | 阶段 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|---|
| T-01 | 严重 | 权限矩阵、所有权验证、API 层检查、Repository 过滤 | PT-001、PT-002、PT-003、PT-004、PT-005、PT-006、PT-007、PT-008、ST-004、ST-005、REV-001、FC-001、FC-002、FC-003、FC-004、FC-008、FC-012、RT-001、RT-009 | P2/P3 | defined | not_run |
| T-02 | 高 | MemoryService 四重检查、模块边界、加密存储 | PT-101、PT-102、PT-103、PT-104、PT-105、PT-106、PT-107、REV-002、FC-001、FC-002、FC-003、FC-004、RT-008 | P2 | defined | not_run |
| T-03 | 高 | 敏感日志过滤、禁止记录、只记录元数据、配置 | LG-001、LG-002、LG-003、LG-004、LG-005、LG-101、LG-102、LG-103、LG-104、PI-003、PI-005、MR-005、EN-009、FC-003、FC-006、FC-007、FC-010、FC-011、RT-006、RT-007、RT-010 | P2/P3 | defined | not_run |
| T-04 | 高 | 最小化胶囊、Prompt 模板、输出验证、路由策略 | PI-001、PI-002、PI-003、PI-004、PI-005、EN-007、EN-012、FC-005、FC-006、FC-007、FC-010、RT-006 | P3 | defined | not_run |
| T-05 | 中 | 幂等性、Token 轮换、场景状态机、限流 | RP-001、RP-002、RP-003、RP-004、RP-005、REV-004、FC-002、FC-009、RT-008 | P2 | defined | not_run |
| T-06 | 高 | 权限矩阵、所有权检查、Repository 过滤 | PT-001、PT-002、PT-003、PT-004、PT-005、PT-006、PT-101、PT-102、PT-103、PT-104、PT-105、PT-106、PT-107、PT-201、PT-202、PT-203、PT-204、PT-301、PT-302、PT-303、PT-304、PT-305、PT-306、REV-003、EXP-001、EXP-002、EXP-003、FC-001、FC-003、FC-004、FC-008、FC-011、RT-005、RT-007、RT-009 | P2 | defined | not_run |
| T-07 | 中 | 立即清理、TTL 兜底、数据库加密、备份策略 | PT-007、PT-008、CL-001、CL-002、CL-003、CL-004、CL-005、FC-012、RT-001、RT-002、RT-003、RT-004、RT-005 | P3 | defined | not_run |
| T-08 | 高 | 默认禁用外部模型、路由策略、统一网关、隐私上下文 | MR-001、MR-002、MR-003、MR-004、MR-005、ST-001、ST-002、ST-003、ST-004、ST-005、EN-006、FC-002、FC-005、FC-006、FC-007、FC-008、FC-010、RT-006、RT-009 | P2/P7 | defined | not_run |
| T-09 | 高 | 节点管理权限、身份认证、凭据保护、安全传输、SSRF 防护、网络隔离、数据最小化、输出验证、健康异常处理、供应链 | EN-001、EN-002、EN-003、EN-004、EN-005、EN-006、EN-007、EN-008、EN-009、EN-010、EN-011、EN-012、MR-004、MR-005、PT-305、FC-001、FC-004、FC-005、FC-006、FC-007、FC-010、FC-011、RT-007、RT-010 | P7 | defined | not_run |

### 14.2 反向映射：测试 → 威胁

| 测试 ID/范围 | 威胁 | 验证控制 | 定义章节 | 定义状态 | 执行状态 |
|---|---|---|---|---|---|
| PT-001 | T-01、T-06 | 权限矩阵、所有权验证 | §3.1 | defined | not_run |
| PT-002 | T-01、T-06 | 权限矩阵、所有权验证 | §3.1 | defined | not_run |
| PT-003 | T-01、T-06 | 权限矩阵、所有权验证 | §3.1 | defined | not_run |
| PT-004 | T-01、T-06 | 权限矩阵、所有权验证 | §3.1 | defined | not_run |
| PT-005 | T-01、T-06 | 权限矩阵、所有权验证 | §3.1 | defined | not_run |
| PT-006 | T-01、T-06 | 所有权验证 | §3.1 | defined | not_run |
| PT-007 | T-01、T-07 | 系统清理 | §3.1 | defined | not_run |
| PT-008 | T-01、T-07 | 系统清理 | §3.1 | defined | not_run |
| PT-101 | T-02、T-06 | MemoryService 四重检查 | §3.2 | defined | not_run |
| PT-102 | T-02、T-06 | MemoryService 四重检查 | §3.2 | defined | not_run |
| PT-103 | T-02、T-06 | MemoryService 四重检查 | §3.2 | defined | not_run |
| PT-104 | T-02、T-06 | MemoryService 四重检查 | §3.2 | defined | not_run |
| PT-105 | T-02、T-06 | 所有权验证 | §3.2 | defined | not_run |
| PT-106 | T-02、T-06 | 所有权验证 | §3.2 | defined | not_run |
| PT-107 | T-02、T-06 | 所有权验证 | §3.2 | defined | not_run |
| PT-201 | T-06 | 群聊权限 | §3.3 | defined | not_run |
| PT-202 | T-06 | 群聊权限 | §3.3 | defined | not_run |
| PT-203 | T-06 | 群聊权限、ORG_ADMIN 边界 | §3.3 | defined | not_run |
| PT-204 | T-06 | 私有提交隔离 | §3.3 | defined | not_run |
| PT-301 | T-06 | 管理后台权限 | §3.4 | defined | not_run |
| PT-302 | T-06 | 管理后台权限 | §3.4 | defined | not_run |
| PT-303 | T-06 | 管理后台权限 | §3.4 | defined | not_run |
| PT-304 | T-06 | 管理后台权限 | §3.4 | defined | not_run |
| PT-305 | T-06、T-09 | SCHOOL_ADMIN 脱敏指标边界 | §3.4 | defined | not_run |
| PT-306 | T-06 | 管理后台权限 | §3.4 | defined | not_run |
| ST-001 | T-08 | 场景事件隐私 | §4.1 | defined | not_run |
| ST-002 | T-08 | 场景事件隐私 | §4.1 | defined | not_run |
| ST-003 | T-08 | 场景事件隐私 | §4.1 | defined | not_run |
| ST-004 | T-01、T-08 | 场景事件隐私、私有提交隔离 | §4.1 | defined | not_run |
| ST-005 | T-01、T-08 | 场景事件隐私、私有提交隔离 | §4.1 | defined | not_run |
| CL-001 | T-07 | 清理测试 | §4.2 | defined | not_run |
| CL-002 | T-07 | 清理测试 | §4.2 | defined | not_run |
| CL-003 | T-07 | 清理测试 | §4.2 | defined | not_run |
| CL-004 | T-07 | 清理测试 | §4.2 | defined | not_run |
| CL-005 | T-07 | 清理测试 | §4.2 | defined | not_run |
| LG-001 | T-03 | 日志隐私 | §5.1 | defined | not_run |
| LG-002 | T-03 | 日志隐私 | §5.1 | defined | not_run |
| LG-003 | T-03 | 日志隐私 | §5.1 | defined | not_run |
| LG-004 | T-03 | 日志隐私 | §5.1 | defined | not_run |
| LG-005 | T-03 | 日志隐私 | §5.1 | defined | not_run |
| LG-101 | T-03 | 允许记录的元数据 | §5.2 | defined | not_run |
| LG-102 | T-03 | 允许记录的元数据 | §5.2 | defined | not_run |
| LG-103 | T-03 | 允许记录的元数据 | §5.2 | defined | not_run |
| LG-104 | T-03 | 允许记录的元数据 | §5.2 | defined | not_run |
| REV-001 | T-01 | 授权撤销 | §6 | defined | not_run |
| REV-002 | T-02 | 授权撤销 | §6 | defined | not_run |
| REV-003 | T-06 | 授权撤销 | §6 | defined | not_run |
| REV-004 | T-05 | 授权撤销、Token 轮换 | §6 | defined | not_run |
| EXP-001 | T-06 | 数据导出 | §7 | defined | not_run |
| EXP-002 | T-06 | 数据导出 | §7 | defined | not_run |
| EXP-003 | T-06 | 数据导出 | §7 | defined | not_run |
| PI-001 | T-04 | Prompt 最小化 | §8 | defined | not_run |
| PI-002 | T-04 | 系统提示隔离 | §8 | defined | not_run |
| PI-003 | T-04、T-03 | 输出验证、日志脱敏 | §8 | defined | not_run |
| PI-004 | T-04 | 输出验证 | §8 | defined | not_run |
| PI-005 | T-04、T-03 | 日志脱敏 | §8 | defined | not_run |
| RP-001 | T-05 | 幂等性 | §9 | defined | not_run |
| RP-002 | T-05 | 幂等冲突检测 | §9 | defined | not_run |
| RP-003 | T-05 | 场景状态机 | §9 | defined | not_run |
| RP-004 | T-05 | Token 轮换、重放检测 | §9 | defined | not_run |
| RP-005 | T-05 | 幂等作用域锁定 | §9 | defined | not_run |
| MR-001 | T-08 | 隐私上下文路由策略 | §10 | defined | not_run |
| MR-002 | T-08 | 默认禁用外部模型 | §10 | defined | not_run |
| MR-003 | T-08 | 隐私上下文校验、失败关闭 | §10 | defined | not_run |
| MR-004 | T-08、T-09 | 安全降级策略 | §10 | defined | not_run |
| MR-005 | T-08、T-03、T-09 | 日志脱敏 | §10 | defined | not_run |
| EN-001 | T-09 | 节点管理权限 | §11 | defined | not_run |
| EN-002 | T-09 | 安全传输 | §11 | defined | not_run |
| EN-003 | T-09 | SSRF 防护 | §11 | defined | not_run |
| EN-004 | T-09 | DNS 重新校验 | §11 | defined | not_run |
| EN-005 | T-09 | 节点身份认证 | §11 | defined | not_run |
| EN-006 | T-09、T-08 | 数据最小化 | §11 | defined | not_run |
| EN-007 | T-09、T-04 | 输出验证 | §11 | defined | not_run |
| EN-008 | T-09 | 网络隔离 | §11 | defined | not_run |
| EN-009 | T-09、T-03 | 凭据保护、日志脱敏 | §11 | defined | not_run |
| EN-010 | T-09 | 健康和异常处理 | §11 | defined | not_run |
| EN-011 | T-09 | 凭据轮换 | §11 | defined | not_run |
| EN-012 | T-09、T-04 | 输出验证 | §11 | defined | not_run |
| FC-001 | T-01、T-02、T-06、T-09 | 授权失败关闭 | §12 | defined | not_run |
| FC-002 | T-01、T-02、T-05、T-08 | 授权撤销失败关闭 | §12 | defined | not_run |
| FC-003 | T-01、T-02、T-03、T-06 | 解密失败关闭 | §12 | defined | not_run |
| FC-004 | T-01、T-02、T-06、T-09 | 隔离失败关闭 | §12 | defined | not_run |
| FC-005 | T-04、T-08、T-09 | 隐私上下文失败关闭 | §12 | defined | not_run |
| FC-006 | T-03、T-04、T-08、T-09 | 模型路由失败关闭 | §12 | defined | not_run |
| FC-007 | T-03、T-04、T-08、T-09 | 输出校验失败关闭 | §12 | defined | not_run |
| FC-008 | T-01、T-06、T-08 | WebSocket 失败关闭 | §12 | defined | not_run |
| FC-009 | T-05 | 重放失败关闭 | §12 | defined | not_run |
| FC-010 | T-03、T-04、T-08、T-09 | 边缘节点失败关闭 | §12 | defined | not_run |
| FC-011 | T-03、T-06、T-09 | 审计失败关闭 | §12 | defined | not_run |
| FC-012 | T-01、T-07 | 清理失败关闭 | §12 | defined | not_run |
| RT-001 | T-01、T-07 | 临时私有数据删除验证 | §13 | defined | not_run |
| RT-002 | T-07 | 私有胶囊删除验证 | §13 | defined | not_run |
| RT-003 | T-07 | 导出文件过期删除验证 | §13 | defined | not_run |
| RT-004 | T-07 | AgentRun 保留期限验证 | §13 | defined | not_run |
| RT-005 | T-06、T-07 | AuditLog 保留期限验证 | §13 | defined | not_run |
| RT-006 | T-03、T-04、T-08 | Memory 级联删除验证 | §13 | defined | not_run |
| RT-007 | T-03、T-06、T-09 | 评价数据归档/删除验证 | §13 | defined | not_run |
| RT-008 | T-02、T-05 | Token/Session 失效验证 | §13 | defined | not_run |
| RT-009 | T-01、T-06、T-08 | 审计日志导出验证 | §13 | defined | not_run |
| RT-010 | T-03、T-09 | 日志脱敏导出验证 | §13 | defined | not_run |

### 14.3 统计汇总

| 指标 | 值 |
|---|---|
| 威胁总数 | 9（T-01～T-09） |
| 有测试的威胁 | 9 |
| 无测试的威胁 | 0 |
| 严重/高风险有测试 | 7/7 |
| 正式测试定义总数 | 100 |
| 有映射的测试 | 100 |
| 无映射的测试 | 0 |
| 未定义测试引用 | 0 |
| 重复定义 | 0 |
| 定义状态 | defined=100 |
| 执行状态 | not_run=100 |

### 14.4 严重/高风险拒绝/失败关闭/泄露检测/保留策略覆盖

| 威胁 | 风险 | 覆盖类型 |
|---|---|---|
| T-01 | 严重 | 拒绝测试（PT-001～PT-005）、隔离测试（ST-004、ST-005）、失败关闭测试（FC-001、FC-002、FC-003、FC-004、FC-008、FC-012）、保留策略测试（RT-001、RT-009） |
| T-02 | 高 | 拒绝测试（PT-101～PT-104）、失败关闭测试（FC-001、FC-002、FC-003、FC-004）、保留策略测试（RT-008） |
| T-03 | 高 | 泄露检测测试（LG-001～LG-005、PI-005、MR-005、EN-009）、失败关闭测试（FC-003、FC-006、FC-007、FC-010、FC-011）、保留策略测试（RT-006、RT-007、RT-010） |
| T-04 | 高 | 拒绝测试（PI-001～PI-005、EN-007、EN-012）、失败关闭测试（FC-005、FC-006、FC-007、FC-010）、保留策略测试（RT-006） |
| T-06 | 高 | 拒绝测试（PT-001～PT-006、PT-101～PT-107、PT-201～PT-204、PT-301～PT-306）、失败关闭测试（FC-001、FC-003、FC-004、FC-008、FC-011）、保留策略测试（RT-005、RT-007、RT-009） |
| T-08 | 高 | 拒绝/失败关闭测试（MR-001～MR-005、EN-006、FC-002、FC-005、FC-006、FC-007、FC-008、FC-010）、保留策略测试（RT-006、RT-009） |
| T-09 | 高 | 拒绝/失败关闭/泄露检测测试（EN-001～EN-012、MR-004、MR-005、FC-001、FC-004、FC-005、FC-006、FC-007、FC-010、FC-011）、保留策略测试（RT-007、RT-010） |

---

## 15. 执行要求

### 15.1 测试时机

| 测试类型 | 执行时机 |
|---------|---------|
| 授权/拒绝测试 | 每阶段结束 |
| 清理测试 | P8后必跑，P12前全量 |
| 日志扫描 | P12前全量 |
| WebSocket测试 | P5后必跑 |
| E2E隐私测试 | P11后必跑，P12前三次 |
| 保留策略测试 | P12前全量 |

### 15.2 测试数据

- 使用固定虚构数据
- 不得使用真实个人信息
- 每次测试前重置数据库

### 15.3 失败标准

以下情况必须阻止发布：
- ❌ PT-001 到 PT-005 任意一个失败（可读取他人私有提交）
- ❌ PT-101 到 PT-104 任意一个失败（可读取他人记忆）
- ❌ CL-001 到 CL-003 任意一个失败（临时数据未清理）
- ❌ LG-001 到 LG-005 任意一个失败（日志泄露）
- ❌ REV-001 到 REV-004 任意一个失败（撤销不生效）
- ❌ FC-001 到 FC-012 任意一个失败（隐私失败关闭未生效）
- ❌ RT-001 到 RT-010 任意一个失败（保留策略未生效）

---

## 16. 相关文档

- [角色权限矩阵](../architecture/PERMISSION_MATRIX.md)
- [威胁模型](../security/THREAT_MODEL.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)

---

**下一步**：P2 阶段执行测试
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
| 2026-07-15 | R1-29 新增 27 个正式测试定义（PI/RP/MR/EN），建立威胁—控制—测试双向追踪矩阵；修正 PT-203、PT-305、LG 表；定义状态 defined、执行状态 not_run；总计 78 个唯一测试定义 | - |
| 2026-07-15 | R1-30 新增 12 个隐私失败关闭测试定义（FC-001～FC-012），建立失败关闭场景矩阵；更新双向追踪矩阵加入 FC 测试；追踪矩阵从 §12 重新编号为 §13，执行要求从 §13 编号为 §14，相关文档从 §14 编号为 §15；定义状态 defined、执行状态 not_run；总计 90 个唯一测试定义 | - |
| 2026-07-15 | R1-31 新增 10 个保留策略测试定义（RT-001～RT-010），验证 TTL、清理触发、删除方法、可恢复性、可导出性；更新双向追踪矩阵加入 RT 测试；追踪矩阵从 §13 重新编号为 §14，执行要求从 §14 编号为 §15，相关文档从 §15 编号为 §16；保留策略权威口径见 DATA_INVENTORY.md §13；定义状态 defined、执行状态 not_run；总计 100 个唯一测试定义 | - |
