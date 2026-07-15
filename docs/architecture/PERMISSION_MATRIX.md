# 角色权限矩阵

> **版本**：v1.0  
> **基线日期**：2026-07-14  
> **状态**：已冻结，变更需 ADR  
> **维护者**：开发团队

## 1. 概述

本文档定义 CampusAgent 的完整权限模型，包括：

- **全局角色**（GlobalRole）- 用户在系统中的基础权限
- **组织角色**（OrganizationRole）- 用户在特定组织内的权限
- **资源类型**（Resource Type）- 可访问的系统资源
- **动作类型**（Action Type）- 可执行的操作
- **权限矩阵**（Permission Matrix）- 角色对资源的访问规则
- **默认拒绝规则**（Default Deny）- 未明确授权的访问一律拒绝

**核心原则**：
- ✅ 默认拒绝（Default Deny）
- ✅ 最小权限（Least Privilege）
- ✅ 职责分离（Separation of Duties）
- ✅ 权限可审计（Auditable）

---

## 2. 角色定义

### 2.1 全局角色（GlobalRole）

全局角色是用户在系统中的基础身份，决定系统级权限。

| 角色标识 | 中文名 | 说明 | MVP范围 |
|---------|--------|------|---------|
| `STUDENT` | 学生 | 使用通讯、智能体、场景和个人记忆 | ✅ |
| `TEACHER` | 教师 | 创建课程组织、发布讨论、管理课程成员 | ✅ |
| `COUNSELOR` | 心理支持人员 | 管理被授权的支持场景，不可读取默认私有数据 | ✅ |
| `ORG_ADMIN` | 组织管理员 | 管理班级、社团、宿舍等指定组织 | ✅ |
| `SCHOOL_ADMIN` | 校方管理员 | 管理学校组织、账号、模型和节点 | ✅ |
| `SYSTEM_ADMIN` | 系统管理员 | 系统配置、运维和安全审计 | ✅ |

**说明**：
- 一个用户只能有一个全局角色
- 一个用户可以同时在多个组织中拥有不同组织角色
- 例如：全局 `STUDENT` + 社团 `OWNER` + 课程 `MEMBER`

---

### 2.2 组织角色（OrganizationRole）

组织角色是用户在特定组织内的权限，与全局角色独立。

| 角色标识 | 中文名 | 说明 | 继承关系 |
|---------|--------|------|---------|
| `OWNER` | 所有者 | 组织的最高权限，只能有一个 | 包含 ADMIN |
| `ADMIN` | 管理员 | 管理组织成员和设置 | 包含 MEMBER |
| `MEMBER` | 成员 | 组织成员，可参与组织活动 | 包含 GUEST |
| `GUEST` | 访客 | 只读访问，不可发言 | 无 |

**说明**：
- 一个用户可以同时是多个组织的不同角色
- 组织角色权限不跨组织继承
- 保护最后一个 Owner（不能退出或删除）

---

## 3. 资源类型（Resource Type）

| 资源标识 | 中文名 | 说明 | 隐私等级 |
|---------|--------|------|---------|
| `user` | 用户 | 用户账户和个人资料 | P1 |
| `agent` | 智能体 | 个人/组织智能体 | P1/P2 |
| `memory` | 记忆 | 个人记忆项 | P2/P3 |
| `organization` | 组织 | 学校/学院/班级/宿舍/社团 | P0/P1 |
| `conversation` | 会话 | 私聊/群聊/场景 | P1/P2 |
| `message` | 消息 | 普通消息/场景卡 | P1/P2 |
| `scene` | 场景 | 场景定义/实例 | P1/P2 |
| `private_submission` | 私有提交 | 场景私有偏好 | **P4** |
| `consent` | 授权记录 | 用户授权记录 | P2 |
| `node` | 节点 | 边缘计算节点 | P1 |
| `model` | 模型 | 模型配置 | P1 |
| `audit` | 审计日志 | 系统审计记录 | P1 |

**隐私等级说明**：
- **P0 公开**：组织名称等
- **P1 内部**：成员关系、配置信息
- **P2 私有**：饮食偏好、预算
- **P3 高敏感**：心理状态
- **P4 临时秘密**：原始场景输入

---

## 4. 动作类型（Action Type）

| 动作标识 | 中文名 | 说明 | 是否需要授权 |
|---------|--------|------|------------|
| `create` | 创建 | 创建新资源 | 否 |
| `read` | 读取 | 读取资源内容 | **是** |
| `update` | 更新 | 修改资源 | 是 |
| `delete` | 删除 | 删除资源 | 是 |
| `list` | 列表 | 列出多个资源 | 视情况 |
| `search` | 搜索 | 搜索资源 | 视情况 |
| `execute` | 执行 | 执行操作 | 是 |
| `manage` | 管理 | 管理（如成员管理） | 是 |
| `admin` | 管理后台 | 系统管理操作 | 是 |

---

## 5. 全局角色权限矩阵

### 5.1 STUDENT（学生）

| 资源 | 创建 | 读取 | 更新 | 删除 | 列表 | 搜索 | 说明 |
|------|------|------|------|------|------|------|------|
| user | ❌ | 自己 | 自己 | ❌ | ❌ | ✅ 搜索用户 | 只能查看公开资料 |
| agent | ❌ | 自己 | 自己 | ❌ | ❌ | ❌ | 只能管理自己的智能体 |
| memory | ✅ | 自己+授权 | 自己+授权 | 自己+授权 | 自己 | ❌ | 通过Memory Service |
| organization | ❌ | 可见 | ❌ | ❌ | ✅ | ✅ | 可见性控制 |
| conversation | ✅ | 参与者 | 所有者 | 所有者 | 自己 | ❌ | 只能查看参与的会话 |
| message | ✅ | 会话内 | 自己 | 自己 | 会话内 | ❌ | 只能查看参与会话的消息 |
| scene | ✅ | 参与者 | 创建者 | 创建者 | 自己 | ❌ | 只能查看参与的场景 |
| private_submission | ✅ | **仅自己** | ❌ | ❌ | ❌ | ❌ | **核心隐私控制** |
| consent | ✅ | 自己 | 自己 | ❌ | 自己 | ❌ | 只能管理自己的授权 |
| node | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 学生无权限 |
| model | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 学生无权限 |
| audit | ❌ | 自己的记录 | ❌ | ❌ | 自己的记录 | ❌ | 只能查看自己的审计 |

**关键约束**：
- ❌ 不能读取他人的私有提交
- ❌ 不能读取他人的记忆正文
- ❌ 不能管理节点和模型

---

### 5.2 TEACHER（教师）

继承 STUDENT 权限，增加：

| 资源 | 额外权限 | 说明 |
|------|---------|------|
| organization | manage | 可创建课程组织 |
| conversation | manage | 可管理课程会话 |
| scene | execute | 可创建课堂讨论场景 |
| message | manage | 可管理课程消息 |

**关键约束**：
- ❌ 不能读取学生私有偏好
- ❌ 不能读取学生记忆正文
- ❌ 不能访问心理相关数据（P3）

---

### 5.3 COUNSELOR（心理支持人员）

继承 STUDENT 权限，增加：

| 资源 | 额外权限 | 说明 |
|------|---------|------|
| organization | manage | 可创建心理支持组织 |
| conversation | manage | 可管理支持会话 |
| scene | execute | 可创建情绪记录场景（需额外授权） |

**关键约束**：
- ❌ **默认不能读取 P3 数据**
- ❌ 不能读取学生私有偏好
- ✅ 只能访问用户明确授权的心理支持场景
- ✅ 心理数据独立域，需特殊权限

---

### 5.4 ORG_ADMIN（组织管理员）

| 资源 | 权限 | 说明 |
|------|------|------|
| user | list, search | 只能查看自己管理的组织成员 |
| organization | manage | 只能管理自己被授权的组织 |
| conversation | manage | 只能管理组织内的会话 |
| member | manage | 可管理组织成员（添加/移除/角色） |

**关键约束**：
- ❌ **不能读取用户私有偏好**
- ❌ **不能读取用户记忆正文**
- ❌ **不能读取私有提交**
- ❌ 只能管理被授权的特定组织

---

### 5.5 SCHOOL_ADMIN（校方管理员）

继承 ORG_ADMIN 权限，增加：

| 资源 | 额外权限 | 说明 |
|------|---------|------|
| organization | manage | 可管理全校组织 |
| user | list, search, manage | 可管理所有用户账号 |
| node | read, list, health-check | 可查看脱敏节点指标；不可创建、修改或删除节点（具体权限以 API_CONTRACT 端点声明为准） |
| model | manage | 可管理模型配置 |
| audit | read | 可查看系统审计日志（脱敏） |

**关键约束**：
- ❌ **不能读取 P2/P3 数据正文**（包括私有偏好、记忆、聊天）
- ✅ 只能查看脱敏的系统指标
- ✅ 只能查看结构化审计元数据（无敏感内容）
- ✅ 不能访问心理支持独立域

---

### 5.6 SYSTEM_ADMIN（系统管理员）

继承 SCHOOL_ADMIN 权限，增加：

| 资源 | 额外权限 | 说明 |
|------|---------|------|
| system | manage | 系统配置、运维 |
| audit | manage | 审计配置、日志管理 |
| all | read（脱敏） | 可读取所有资源的结构化元数据 |

**关键约束**：
- ❌ **即使 SYSTEM_ADMIN 也不能读取 P2/P3 正文**
- ❌ 不能绕过授权检查
- ✅ 受数据目的和权限约束
- ✅ 所有操作可审计

---

## 6. 组织角色权限矩阵

### 6.1 OWNER（所有者）

| 动作 | 权限 | 说明 |
|------|------|------|
| 修改组织信息 | ✅ | 名称、描述等 |
| 删除组织 | ✅ | 受保护（不能删除最后一个组织） |
| 添加成员 | ✅ | 邀请/审批 |
| 移除成员 | ✅ | 包括 ADMIN |
| 修改成员角色 | ✅ | 可降级 OWNER 为 ADMIN（需确认） |
| 转让所有权 | ✅ | 必须指定新 OWNER |
| 退出组织 | ❌ | 必须转让所有权或删除组织 |

**保护机制**：
- 一个组织只能有一个 OWNER
- 退出或删除前必须转让所有权
- 转让需要新 OWNER 确认

---

### 6.2 ADMIN（管理员）

继承 MEMBER 权限，增加：

| 动作 | 权限 | 说明 |
|------|------|------|
| 修改组织信息 | ✅ | 不能修改所有者 |
| 添加成员 | ✅ | 可邀请 |
| 移除成员 | ✅ | 不能移除 OWNER |
| 修改成员角色 | ✅ | 只能降级，不能升级为 OWNER |

---

### 6.3 MEMBER（成员）

继承 GUEST 权限，增加：

| 动作 | 权限 | 说明 |
|------|------|------|
| 在组织内发言 | ✅ | 在组织会话中 |
| 创建组织会话 | ✅ | 符合组织策略 |
| 参与组织场景 | ✅ | 如被邀请 |

---

### 6.4 GUEST（访客）

| 动作 | 权限 | 说明 |
|------|------|------|
| 查看组织公开信息 | ✅ | 名称、公开成员列表 |
| 查看组织会话 | ❌ | 不能查看 |
| 发言 | ❌ | 不能发言 |

---

## 7. 特殊权限规则

### 7.1 私有提交访问（核心隐私控制）

| 角色 | 读取私有提交 | 说明 |
|------|------------|------|
| STUDENT | **仅自己** | owner_user_id = 当前用户 |
| TEACHER | ❌ | 无权限 |
| COUNSELOR | ❌ | 无权限（除非明确授权） |
| ORG_ADMIN | ❌ | **无权限** |
| SCHOOL_ADMIN | ❌ | **无权限** |
| SYSTEM_ADMIN | ❌ | **无权限** |

**规则**：
- 私有提交只能通过 Scene API 读取
- 只能读取自己的提交
- 任何管理角色都不能读取

---

### 7.2 记忆访问

| 角色 | 读取记忆 | 条件 |
|------|---------|------|
| STUDENT | ✅ | 自己的记忆，通过 Memory Service |
| 其他角色 | ❌ | 除非用户明确授权分享 |

**规则**：
- 必须通过 MemoryService.query()
- 必须满足：owner + purpose + category + consent
- 任何角色不能绕过 MemoryService

---

### 7.3 智能体配置访问

| 角色 | 读取配置 | 读取私有配置 | 说明 |
|------|---------|------------|------|
| 智能体所有者 | ✅ | ✅ | 可查看加密的私有配置 |
| SYSTEM_ADMIN | ✅ | ❌ | 只能查看公开配置 |
| 其他角色 | ❌ | ❌ | 无权限 |

**私有配置**：
- `private_config_encrypted` 字段
- 只有所有者和管理员可查看
- 管理员不能解密

---

### 7.4 审计日志访问

| 角色 | 读取审计 | 可读取内容 |
|------|---------|----------|
| STUDENT | ✅ | 自己的记录 |
| TEACHER | ✅ | 自己相关的记录 |
| COUNSELOR | ✅ | 自己相关的记录 |
| ORG_ADMIN | ✅ | 自己管理的组织相关记录 |
| SCHOOL_ADMIN | ✅ | 系统级记录（脱敏） |
| SYSTEM_ADMIN | ✅ | 所有记录（脱敏） |

**审计内容规则**：
- ✅ actor_id, action, resource_type, resource_id, purpose, result, timestamp, request_id
- ❌ **不包含敏感内容本身**
- ❌ 不包含原始偏好、聊天明文、记忆正文

---

## 8. 默认拒绝规则

### 8.1 全局默认拒绝

所有访问请求**默认拒绝**，除非：
1. 角色明确拥有该权限
2. 资源可见性允许
3. 授权记录有效（ConsentRecord.granted = true）

### 8.2 拒绝优先级

```
1. 检查认证（是否登录）
2. 检查角色（是否有全局角色）
3. 检查资源可见性（公开/内部/私有）
4. 检查组织成员资格（如果是组织资源）
5. 检查权限矩阵（是否有明确权限）
6. 检查授权记录（ConsentRecord）
7. 检查所有权（owner_user_id）
8. 拒绝访问
```

### 8.3 拒绝响应

```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "没有权限执行此操作",
    "details": {
      "required_role": "OWNER",
      "user_role": "MEMBER"
    }
  },
  "request_id": "req_xxx"
}
```

**约束**：
- ❌ 不泄露用户是否存在
- ❌ 不泄露资源是否存在（如果用户无权访问）
- ✅ 统一错误码：`PERMISSION_DENIED`

---

## 9. 权限检查流程

### 9.1 读取权限检查

```python
def check_read_permission(
    actor: User,
    resource_type: str,
    resource: Any,
    purpose: str = None
) -> bool:
    # 1. 认证检查
    if not actor.is_authenticated:
        raise PermissionDenied("未登录")

    # 2. 角色检查
    if not has_role(actor, resource_type, "read"):
        raise PermissionDenied("角色无权读取")

    # 3. 资源可见性检查
    if not check_visibility(actor, resource):
        raise PermissionDenied("资源不可见")

    # 4. 所有权检查
    if is_owner(actor, resource):
        return True

    # 5. 组织成员检查
    if is_org_member(actor, resource):
        return True

    # 6. 授权记录检查（P2/P3资源）
    if resource.sensitivity_level in [P2_PRIVATE, P3_SENSITIVE]:
        consent = check_consent(actor, resource_type, resource.id, purpose)
        if not consent or not consent.granted:
            raise PermissionDenied("未授权")

    # 7. 默认拒绝
    raise PermissionDenied("无权访问")
```

---

### 9.2 写入权限检查

```python
def check_write_permission(
    actor: User,
    resource_type: str,
    resource: Any,
    action: str  # create, update, delete
) -> bool:
    # 1. 认证检查
    if not actor.is_authenticated:
        raise PermissionDenied("未登录")

    # 2. 管理员检查
    if actor.global_role in [SYSTEM_ADMIN, SCHOOL_ADMIN]:
        # 仍需检查资源可见性和授权
        pass

    # 3. 所有者检查
    if is_owner(actor, resource):
        return True

    # 4. 权限矩阵检查
    if not has_permission(actor, resource_type, action):
        raise PermissionDenied("角色无权写入")

    # 5. 组织角色检查
    if is_org_admin(actor, resource):
        return True

    # 6. 默认拒绝
    raise PermissionDenied("无权修改")
```

---

## 10. 特殊权限场景

### 10.1 场景参与者权限

| 动作 | 场景创建者 | 场景参与者 | 群主 | 说明 |
|------|-----------|-----------|------|------|
| 查看场景 | ✅ | ✅ | ✅ | 参与者可查看 |
| 修改场景 | ✅ | ❌ | ✅ | 只有创建者可修改 |
| 取消场景 | ✅ | ❌ | ✅ | 创建者和群主 |
| 提交私有偏好 | ✅ | ✅ | ❌ | 参与者可提交，但只能看自己的 |
| 查看他人私有偏好 | ❌ | ❌ | ❌ | **核心隐私控制** |

---

### 10.2 智能体权限

| 动作 | 智能体所有者 | SYSTEM_ADMIN | 说明 |
|------|------------|-------------|------|
| 查看智能体 | ✅ | ✅（仅公开信息） | |
| 修改配置 | ✅ | ❌ | |
| 查看执行历史 | ✅ | ✅（脱敏） | |
| 查看私有配置 | ✅ | ❌ | `private_config_encrypted` |

---

### 10.3 模型节点权限

| 动作 | SCHOOL_ADMIN | SYSTEM_ADMIN | 说明 |
|------|-------------|-------------|------|
| 查看节点列表 | ✅ | ✅ | |
| 查看节点指标 | ✅（脱敏） | ✅（脱敏） | 不返回凭据、Prompt、模型输入或完整响应 |
| 健康检查 | ✅ | ✅ | |
| 创建节点 | ❌ | ✅ | 仅 SYSTEM_ADMIN |
| 修改节点配置 | ❌ | ✅ | 仅 SYSTEM_ADMIN |
| 删除节点 | ❌ | ✅ | 仅 SYSTEM_ADMIN |
| 查看模型配置 | ✅ | ✅ | |
| 查看调用详情 | ❌ | ❌ | 即使是管理员也不能查看 |

---

## 11. 权限测试矩阵

基于本矩阵生成的测试用例：

### 11.1 越权测试

| 测试ID | 描述 | 预期结果 |
|--------|------|---------|
| PT-001 | 学生A读取学生B的私有提交 | 拒绝 |
| PT-002 | ORG_ADMIN读取成员私有偏好 | 拒绝 |
| GUEST读取群聊消息 | GUEST读取群聊消息 | 拒绝 |
| PT-004 | TEACHER读取学生记忆正文 | 拒绝 |
| PT-005 | SCHOOL_ADMIN读取私有提交 | 拒绝 |
| PT-006 | SYSTEM_ADMIN绕过MemoryService | 拒绝 |

### 11.2 授权测试

| 测试ID | 描述 | 预期结果 |
|--------|------|---------|
| PT-101 | 用户读取自己的记忆 | 允许 |
| PT-102 | OWNER管理组织成员 | 允许 |
| PT-103 | 参与者提交私有偏好 | 允许 |
| PT-104 | 参与者查看场景结果 | 允许 |

### 11.3 边界测试

| 测试ID | 描述 | 预期结果 |
|--------|------|---------|
| PT-201 | 最后一个OWNER退出组织 | 拒绝 |
| PT-202 | MEMBER升级为OWNER | 拒绝 |
| PT-203 | GUEST发送消息 | 拒绝 |
| PT-204 | 未授权访问私有资源 | 拒绝 |

---

## 12. 实现建议

### 12.1 权限服务设计

```python
class PermissionService:
    """权限服务"""

    def check_permission(
        self,
        actor: User,
        action: str,
        resource_type: str,
        resource_id: UUID,
        purpose: str = None
    ) -> PermissionResult:
        """
        检查权限

        Returns:
            PermissionResult(granted=True/False, reason=...)
        """
        pass

    def filter_visible_resources(
        self,
        actor: User,
        resource_type: str,
        resources: List[Any]
    ) -> List[Any]:
        """过滤用户可见的资源"""
        pass
```

### 12.2 装饰器使用

```python
@require_permission("read", "memory")
async def get_memory(request: Request, memory_id: UUID):
    memory = await memory_service.get(memory_id)
    return memory
```

### 12.3 API层检查

```python
@router.get("/memories/{memory_id}")
async def get_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
    permission_service: PermissionService = Depends()
):
    # 权限检查
    result = permission_service.check_permission(
        actor=current_user,
        action="read",
        resource_type="memory",
        resource_id=memory_id,
        purpose="view_memory"
    )

    if not result.granted:
        raise HTTPException(status_code=403, detail=result.reason)

    # 业务逻辑
    memory = await memory_service.get(memory_id)
    return memory
```

---

## 13. 相关文档

- [领域词汇表](../domain/DOMAIN_VOCABULARY.md)
- [完整项目计划书](../product/CampusAgent_Project_Plan.md)
- [隐私工程基线](../privacy/PRIVACY_BASELINE.md)
- [用户旅程](../product/USER_JOURNEY.md)

---

**下一步**：P0-05（建立数据清单）、P0-09（草拟HTTP契约）、P0-11（隐私测试矩阵）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
