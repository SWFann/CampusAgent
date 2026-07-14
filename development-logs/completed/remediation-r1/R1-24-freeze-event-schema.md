---
task_id: R1-24
status: completed
stage: R1
title: 冻结事件 Schema
completed_at: 2026-07-14T13:12:00+09:00
estimated_hours: 1
actual_hours: 0.15
---

# R1-24：冻结事件 Schema

## 完成状态

✅ **事件 Schema 已冻结**

**完成时间**：2026-07-14T13:12:00+09:00

## 目标

冻结所有 WebSocket 事件的字段和版本策略，确保公共事件不包含敏感数据。

**来自整改计划**：R1-24 - 冻结事件 Schema

## WebSocket 事件 Schema

### 标准事件格式

```json
{
  "id": "uuid-v4",
  "type": "event_type",
  "version": "1.0",
  "timestamp": "2026-07-14T12:00:00Z",
  "data": {
    // 事件数据
  }
}
```

### 客户端 → 服务器事件

#### auth

```json
{
  "type": "auth",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### subscribe_scene

```json
{
  "type": "subscribe_scene",
  "data": {
    "instance_id": "uuid-v4"
  }
}
```

#### unsubscribe_scene

```json
{
  "type": "unsubscribe_scene",
  "data": {
    "instance_id": "uuid-v4"
  }
}
```

### 服务器 → 客户端事件

#### auth_success

```json
{
  "type": "auth_success",
  "data": {
    "user_id": "uuid-v4",
    "expires_in": 3600
  }
}
```

#### scene.updated

```json
{
  "type": "scene.updated",
  "data": {
    "instance_id": "uuid-v4",
    "progress": {
      "submissions_received": 5,
      "total_participants": 10,
      "status": "running"
    }
  }
}
```

**隐私保护**：仅返回进度数字，不暴露私有提交内容

#### scene.result

```json
{
  "type": "scene.result",
  "data": {
    "instance_id": "uuid-v4",
    "candidates": [
      {
        "id": "uuid-v4",
        "score": 0.85,
        "rank": 1
      }
    ]
  }
}
```

**隐私保护**：候选者已脱敏，仅返回排名和得分

#### token_expiring

```json
{
  "type": "token_expiring",
  "data": {
    "expires_in": 300
  }
}
```

#### token_expired

```json
{
  "type": "token_expired"
}
```

### 版本策略

- **当前版本**：`1.0`
- **向后兼容**：至少保持 1 个主版本兼容
- **弃用通知**：提前 30 天通知客户端

### 隐私约束

- ✅ 公共事件（scene.updated）不包含 P2-P4 数据
- ✅ 私有事件（scene.result）仅包含脱敏数据
- ✅ 不暴露私有提交内容、偏好胶囊、记忆内容

## 验证结果

- [x] 所有事件字段和版本策略已定义
- [x] 公共事件不包含敏感数据

## R1-C 完成总结

已完成 R1-C 阶段的所有任务（R1-18 至 R1-24）：
- ✅ R1-18：统一认证合同
- ✅ R1-19：定义 CSRF 方案
- ✅ R1-20：修正登录响应
- ✅ R1-21：修正 Refresh 流程
- ✅ R1-22：修正 WebSocket 鉴权
- ✅ R1-23：定义 WebSocket Token 过期
- ✅ R1-24：冻结事件 Schema

## 下一步

- **R1-D**：开始修复威胁模型与隐私测试

## 提交信息

- （整改阶段不单独提交，R1 完成后统一提交）
