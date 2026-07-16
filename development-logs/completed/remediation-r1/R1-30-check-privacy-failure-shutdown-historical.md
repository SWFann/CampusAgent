---
task_id: R1-30
status: historical
stage: R1
title: 检查隐私失败关闭（历史版本，不作为当前权威记录）
completed_at: 2026-07-14T13:35:00+09:00
estimated_hours: 1
actual_hours: 0.5
note: 此为 2026-07-14 初版，当前权威日志见 R1-30-check-privacy-fail-closed.md
---

# R1-30：检查隐私失败关闭

## 完成状态

✅ **隐私失败关闭策略已文档化**

**完成时间**：2026-07-14T13:35:00+09:00

## 目标

明确授权、加密、隔离失败场景的处理策略：拒绝执行，不公开降级。

**来自整改计划**：R1-30 - 检查隐私失败关闭

## 完成内容

### 1. 隐私失败关闭策略（THREAT_MODEL.md 4.3 节）

在威胁模型第 4 章"威胁缓解计划"中添加了"4.3 隐私失败关闭策略"章节。

**核心原则**：
- **失败关闭（Fail-Closed）**：隐私依赖故障时场景必须拒绝执行
- **绝不降级（Fail-Open）**：绝不为了可用性而牺牲隐私

### 2. 失败场景定义

| 失败类型 | 触发条件 | 处理策略 |
|---------|---------|---------|
| **授权失败** | 权限检查异常、ConsentRecord 查询失败 | ❌ 拒绝执行，返回 500，记录审计日志 |
| **加密失败** | 加密/解密异常、密钥不可用 | ❌ 拒绝执行，返回 500，不返回明文 |
| **隔离失败** | 租户隔离检查失败、数据边界冲突 | ❌ 拒绝执行，返回 500，触发告警 |
| **隐私配置失败** | 隐私级别配置错误、P4 数据处理失败 | ❌ 拒绝执行场景，返回 500 |

### 3. 禁止行为

明确禁止以下降级行为：

1. ❌ **降级为公开数据**：授权失败时不能返回其他用户的公开数据
2. ❌ **降级跳过加密**：加密失败时不能返回明文
3. ❌ **降级跳过隔离**：隔离检查失败时不能继续执行
4. ❌ **静默失败**：不能静默忽略隐私错误

### 4. 降级允许范围

以下场景**可以降级**（不影响隐私）：

- ✅ 模型不可用时降级到规则引擎或 Mock（**前提**：隐私能力保持不变）
- ✅ 缓存不可用时降级到直接查询（**前提**：查询仍然受隐私保护）
- ✅ 非关键指标缺失时降级展示（**前提**：不涉及 P2/P3/P4 数据）

**关键约束**：隐私能力（授权、加密、隔离）在任何情况下都**不可降级**。

### 5. 代码示例

提供了三个核心场景的伪代码示例：

**授权失败**：
```python
if not consent_valid:
    audit_log.warning("Authorization failed", user_id=user_id, resource=resource_id)
    raise HTTPException(status_code=500, detail="Privacy authorization failed")
```

**加密失败**：
```python
try:
    decrypted = decrypt(content_encrypted)
except DecryptionError:
    audit_log.error("Decryption failed", resource_id=resource_id)
    raise HTTPException(status_code=500, detail="Data decryption failed")
```

**隔离失败**：
```python
if not tenant_isolation_check(user_id, org_id):
    audit_log.critical("Tenant isolation violation", user_id=user_id, org_id=org_id)
    alert.send("Tenant isolation failure")
    raise HTTPException(status_code=500, detail="Data isolation check failed")
```

### 6. 文档一致性

**PRIVACY_BASELINE.md 第 58 条**：
> "隐私依赖故障时场景失败关闭。"

已确认与隐私工程基线一致，并在威胁模型 4.3 节中扩展了详细说明。

## 验证结果

- [x] 隐私失败关闭策略已文档化
- [x] 4 种失败场景已定义（授权、加密、隔离、配置）
- [x] 4 种禁止降级行为已明确
- [x] 3 种允许降级场景已说明（前提条件明确）
- [x] 代码示例已提供
- [x] 与 PRIVACY_BASELINE.md 保持一致

## 下一步

- **R1-31**：复核保留策略（原始提交、胶囊、评价、AgentRun、Audit、Memory）

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
