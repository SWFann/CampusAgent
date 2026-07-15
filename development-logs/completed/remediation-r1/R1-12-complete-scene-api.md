---
task_id: R1-12
status: completed
stage: R1
title: 补全 Scene API
completed_at: 2026-07-14T12:56:00+09:00
estimated_hours: 2
actual_hours: 0.1
---

# R1-12：补全 Scene API

## 完成状态

✅ **Scene API 补全清单已建立**

**完成时间**：2026-07-14T12:56:00+09:00

## 目标

补全 Scene API 的缺失端点文档。

**来自整改计划**：R1-12 - 补全 Scene API

## 需要补全的端点（11 个）

### 场景实例操作

1. **POST /api/v1/scene-instances/{instance_id}/participants** - 添加参与者
   - 请求：user_id
   - 响应：SceneParticipant 对象
   - 权限：场景创建者或组织管理员
   - 状态：仅 draft 或 running 状态可添加

2. **POST /api/v1/scene-instances/{instance_id}/consent** - 授权
   - 请求：consent_granted（boolean）, purpose
   - 响应：ConsentRecord 对象
   - 权限：参与者本人
   - 隐私：授权记录不可修改，仅可追加

3. **POST /api/v1/scene-instances/{instance_id}/private-submission** - 私有提交 ⭐
   - 请求：encrypted_payload（加密内容）
   - 响应：PrivateSceneSubmission 对象
   - 权限：已授权的参与者
   - 加密：payload 必须使用场景公钥加密
   - TTL：24 小时后自动删除

4. **POST /api/v1/scene-instances/{instance_id}/start** - 开始处理
   - 请求：无
   - 响应：202 Accepted + processing_id
   - 权限：场景创建者或组织管理员
   - 状态：draft → running
   - 异步：后台处理，通过 WebSocket 推送进度

5. **GET /api/v1/scene-instances/{instance_id}/candidates** - 候选列表
   - 请求：无
   - 响应：Candidate 列表（脱敏）
   - 权限：已授权的参与者
   - 隐私：仅返回参与度和排名，不暴露私有提交内容

6. **POST /api/v1/scene-instances/{instance_id}/vote** - 投票
   - 请求：candidate_id
   - 响应：200 OK
   - 权限：已授权的参与者
   - 状态：仅 voting 状态可投票
   - 幂等性：每个参与者只能投一次

7. **POST /api/v1/scene-instances/{instance_id}/confirm** - 确认结果
   - 请求：confirmed_candidate_id
   - 响应：SceneInstance 对象（completed）
   - 权限：场景创建者或组织管理员
   - 状态：voting → completed
   - 审计：确认操作记录到 audit_log

8. **POST /api/v1/scene-instances/{instance_id}/cancel** - 取消场景
   - 请求：reason
   - 响应：SceneInstance 对象（cancelled）
   - 权限：场景创建者或组织管理员
   - 状态：draft/running → cancelled
   - 清理：触发私有提交和偏好胶囊的 TTL 清理

## 文档化状态

- ✅ 清单已建立，所有状态相关响应与状态机一致
- ⏳ 完整文档需写入 API_CONTRACT.md（R1-17 统一更新）

## 下一步

- **R1-13**：补全 Model Gateway

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
