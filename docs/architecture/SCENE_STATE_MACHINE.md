# 场景状态机

> **版本**：v1.0  
> **基线日期**：2026-07-14  
> **状态**：已冻结，变更需 ADR  
> **维护者**：开发团队

## 1. 状态机概览

### 1.1 生命周期状态

```
DRAFT
  ↓ [creator]
WAITING_FOR_PARTICIPANTS
  ↓ [all invited]
WAITING_FOR_CONSENT
  ↓ [all consented]
WAITING_FOR_PRIVATE_INPUT
  ↓ [all submitted or timeout]
PROCESSING
  ↓ [processing complete]
CANDIDATES_READY
  ↓ [start voting]
VOTING
  ↓ [voting complete or timeout]
CONFIRMING
  ↓ [confirmed by authorized user]
COMPLETED

异常终态：
  ├─ CANCELLED（发起人取消）
  ├─ FAILED（处理失败）
  └─ EXPIRED（超时过期）
```

---

## 2. 状态定义

### 2.1 正常状态

| 状态 | 描述 | 允许操作 | 触发下一阶段 |
|------|------|---------|------------|
| `DRAFT` | 草稿，未发布 | 编辑、发布、删除 | 发布后 |
| `WAITING_FOR_PARTICIPANTS` | 等待参与者确认参与 | 邀请参与者、取消 | 所有参与者响应后 |
| `WAITING_FOR_CONSENT` | 等待参与者授权 | 撤销授权、取消 | 所有参与者授权后 |
| `WAITING_FOR_PRIVATE_INPUT` | 等待私有偏好提交 | 提交偏好、取消、退出 | 所有提交或超时后 |
| `PROCESSING` | 系统处理中 | 取消（失败时） | 处理完成或失败 |
| `CANDIDATES_READY` | 候选方案就绪 | 投票、取消 | 投票开始后 |
| `VOTING` | 投票中 | 投票、取消 | 投票完成或超时 |
| `CONFIRMING` | 等待确认 | 确认结果、取消 | 确认后 |
| `COMPLETED` | 已完成（终态） | 查看结果 | - |

### 2.2 异常终态

| 状态 | 描述 | 触发条件 | 清理策略 |
|------|------|---------|---------|
| `CANCELLED` | 发起人取消 | 发起人取消 | 立即清理临时数据 |
| `FAILED` | 处理失败 | 模型失败且无法降级 | 清理临时数据，保留审计 |
| `EXPIRED` | 超时过期 | 超过总时长未完成 | 清理临时数据，保留审计 |

---

## 3. 状态转换规则

### 3.1 合法转换矩阵

| 当前状态 | 目标状态 | 触发动作 | 发起者 | 条件 |
|---------|---------|---------|--------|------|
| DRAFT | WAITING_FOR_PARTICIPANTS | publish | 创建者 | 至少1名参与者 |
| DRAFT | - | delete | 创建者 | - |
| WAITING_FOR_PARTICIPANTS | WAITING_FOR_CONSENT | start_consent | 创建者 | 所有参与者已确认参与 |
| WAITING_FOR_PARTICIPANTS | CANCELLED | cancel | 创建者/群主 | - |
| WAITING_FOR_CONSENT | WAITING_FOR_PRIVATE_INPUT | start_private_input | 创建者 | 所有参与者已授权 |
| WAITING_FOR_CONSENT | CANCELLED | cancel | 创建者/群主 | - |
| WAITING_FOR_PRIVATE_INPUT | PROCESSING | start_processing | 系统自动 | 所有参与者已提交或超时 |
| WAITING_FOR_PRIVATE_INPUT | CANCELLED | cancel | 创建者/群主 | - |
| PROCESSING | CANDIDATES_READY | processing_complete | 系统自动 | 处理成功 |
| PROCESSING | FAILED | processing_failed | 系统自动 | 处理失败且无法降级 |
| CANDIDATES_READY | VOTING | start_voting | 创建者/群主 | - |
| CANDIDATES_READY | CANCELLED | cancel | 创建者/群主 | - |
| VOTING | CONFIRMING | voting_complete | 系统自动 | 投票完成或超时 |
| VOTING | CANCELLED | cancel | 创建者/群主 | - |
| CONFIRMING | COMPLETED | confirm | 群主/创建者 | 选择最终候选 |
| CONFIRMING | CANCELLED | cancel | 创建者/群主 | - |
| * | EXPIRED | expire | 系统自动 | 超过总时长 |

### 3.2 非法转换（必须拒绝）

| 非法转换 | 拒绝原因 |
|---------|---------|
| DRAFT → PROCESSING | 跳过必要步骤 |
| WAITING_FOR_PRIVATE_INPUT → COMPLETED | 未处理 |
| COMPLETED → 任何状态 | 终态不可逆 |
| CANCELLED → 任何状态 | 终态不可逆 |
| FAILED → 任何状态 | 终态，除非重试（需新实例） |

---

## 4. 动作权限

### 4.1 发起者权限

| 动作 | 允许发起者 | 前提条件 |
|------|----------|---------|
| publish | 创建者 | 至少1名参与者 |
| cancel | 创建者、群主 | 非终态 |
| confirm | 群主、创建者 | 在 CONFIRMING 阶段 |
| start_consent | 创建者 | 所有参与者确认参与 |
| start_private_input | 创建者 | 所有参与者授权 |
| start_voting | 创建者、群主 | CANDIDATES_READY |

### 4.2 参与者权限

| 动作 | 允许发起者 | 前提条件 |
|------|----------|---------|
| consent | 参与者本人 | WAITING_FOR_CONSENT |
| decline | 参与者本人 | WAITING_FOR_CONSENT |
| submit | 参与者本人 | WAITING_FOR_PRIVATE_INPUT |
| revoke_consent | 参与者本人 | 授权有效期内 |
| vote | 参与者本人 | VOTING |

---

## 5. 幂等性规则

### 5.1 幂等键

所有状态转换和提交操作支持 `Idempotency-Key`：

```python
async def transition(
    scene_id: UUID,
    target_state: str,
    idempotency_key: UUID
) -> SceneInstance:
    # 检查是否已处理
    existing = await transition_log.find_by_key(idempotency_key)
    if existing:
        return existing.result

    # 执行转换
    result = await do_transition(scene_id, target_state)

    # 记录幂等键
    await transition_log.create(
        key=idempotency_key,
        scene_id=scene_id,
        from_state=current_state,
        to_state=target_state,
        result=result
    )

    return result
```

### 5.2 幂等场景

| 操作 | 幂等键要求 | 重复请求处理 |
|------|----------|------------|
| 创建场景 | 必需 | 返回已创建场景 |
| 提交偏好 | 必需 | 返回已提交状态 |
| 投票 | 必需 | 返回已投票候选 |
| 确认结果 | 必需 | 返回已确认结果 |
| 状态转换 | 必需 | 返回当前状态 |

---

## 6. 超时策略

### 6.1 超时配置

| 阶段 | 超时时间 | 超时行为 |
|------|---------|---------|
| WAITING_FOR_PARTICIPANTS | 24小时 | 自动推进到下一阶段（已确认者继续） |
| WAITING_FOR_CONSENT | 24小时 | 标记未授权者为 REJECTED，继续 |
| WAITING_FOR_PRIVATE_INPUT | 48小时 | 标记未提交者，继续处理 |
| PROCESSING | 30分钟 | 降级到规则引擎或标记 FAILED |
| VOTING | 24小时 | 自动结束投票，使用当前结果 |
| CONFIRMING | 12小时 | 标记为 EXPIRED |
| 总时长 | 7天 | EXPIRED |

### 6.2 超时处理

```python
async def check_timeout(scene: SceneInstance):
    if scene.expires_at < now():
        await scene_service.expire(scene.id)
        await cleanup_service.cleanup(scene.id)
        await notification_service.notify(scene, "场景已过期")
```

---

## 7. 并发控制

### 7.1 乐观锁

```python
async def transition(scene_id: UUID, target_state: str):
    scene = await scene_repo.get(scene_id)

    # 乐观锁检查
    updated = await scene_repo.update_if_version(
        scene_id=scene_id,
        version=scene.version,
        status=target_state
    )

    if not updated:
        raise ConcurrentModificationError("场景状态已被其他请求修改")
```

### 7.2 防止竞态条件

| 场景 | 保护机制 |
|------|---------|
| 同时提交偏好 | 乐观锁，后提交者失败 |
| 同时投票 | 幂等键，重复投票不增加计数 |
| 同时确认 | 乐观锁，先确认者成功 |

---

## 8. 状态机实现

### 8.1 状态机类

```python
from enum import Enum
from typing import Dict, List, Tuple

class SceneState(Enum):
    DRAFT = "DRAFT"
    WAITING_FOR_PARTICIPANTS = "WAITING_FOR_PARTICIPANTS"
    WAITING_FOR_CONSENT = "WAITING_FOR_CONSENT"
    WAITING_FOR_PRIVATE_INPUT = "WAITING_FOR_PRIVATE_INPUT"
    PROCESSING = "PROCESSING"
    CANDIDATES_READY = "CANDIDATES_READY"
    VOTING = "VOTING"
    CONFIRMING = "CONFIRMING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"

class SceneStateMachine:
    VALID_TRANSITIONS: Dict[SceneState, List[Tuple[SceneState, str]]] = {
        SceneState.DRAFT: [
            (SceneState.WAITING_FOR_PARTICIPANTS, "publish"),
        ],
        SceneState.WAITING_FOR_PARTICIPANTS: [
            (SceneState.WAITING_FOR_CONSENT, "start_consent"),
            (SceneState.CANCELLED, "cancel"),
        ],
        # ... 其他转换
    }

    TERMINAL_STATES = {
        SceneState.COMPLETED,
        SceneState.CANCELLED,
        SceneState.FAILED,
        SceneState.EXPIRED
    }

    @classmethod
    def can_transition(cls, from_state: SceneState, to_state: SceneState) -> bool:
        """检查转换是否合法"""
        if from_state in cls.TERMINAL_STATES:
            return False

        allowed = cls.VALID_TRANSITIONS.get(from_state, [])
        return any(to == to_state for to, _ in allowed)

    @classmethod
    def is_terminal(cls, state: SceneState) -> bool:
        """是否为终态"""
        return state in cls.TERMINAL_STATES
```

---

## 9. 测试要求

### 9.1 状态机测试

```python
def test_valid_transitions():
    """测试合法转换"""
    assert SceneStateMachine.can_transition(
        SceneState.DRAFT,
        SceneState.WAITING_FOR_PARTICIPANTS
    ) == True

def test_invalid_transition():
    """测试非法转换"""
    assert SceneStateMachine.can_transition(
        SceneState.COMPLETED,
        SceneState.DRAFT
    ) == False

def test_terminal_state():
    """测试终态"""
    assert SceneStateMachine.is_terminal(SceneState.COMPLETED) == True
    assert SceneStateMachine.is_terminal(SceneState.DRAFT) == False
```

### 9.2 集成测试场景

| 测试ID | 场景 | 预期结果 |
|--------|------|---------|
| STM-01 | 正常完成流程 | DRAFT → COMPLETED |
| STM-02 | 发起人取消 | DRAFT → CANCELLED |
| STM-03 | 处理失败 | PROCESSING → FAILED |
| STM-04 | 超时过期 | 超过TTL → EXPIRED |
| STM-05 | 非法转换 | 拒绝非法状态跳转 |
| STM-06 | 并发转换 | 乐观锁保护 |

---

## 10. 相关文档

- [用户旅程](../product/USER_JOURNEY.md)
- [MVP范围定义](../product/MVP_SCOPE.md)

---

**下一步**：P0-09（草拟HTTP契约）
**变更记录**：
| 日期 | 变更内容 | 变更人 |
|------|---------|--------|
| 2026-07-14 | 初始版本 | - |
