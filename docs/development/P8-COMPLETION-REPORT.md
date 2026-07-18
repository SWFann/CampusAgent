# P8 Completion Report

> 阶段：P8 场景核心与插件框架
>
> 完成提交：`17b1005 feat(scenes): complete P8 scene core and plugin framework`

## 1. 完成范围

P8 已完成场景核心框架：ScenePlugin Protocol、场景注册表、场景数据模型、私有提交模型、状态机、参与和授权、私有提交 API、执行协调器、公开场景事件、投票与确认框架、取消/过期、清理编排、边界测试插件和场景框架测试。

## 2. 核心交付物

### 后端源码

- `apps/api/src/modules/scenes/plugin_protocol.py`
- `apps/api/src/modules/scenes/registry.py`
- `apps/api/src/modules/scenes/models.py`
- `apps/api/src/modules/scenes/privacy.py`
- `apps/api/src/modules/scenes/state_machine.py`
- `apps/api/src/modules/scenes/repository.py`
- `apps/api/src/modules/scenes/service.py`
- `apps/api/src/modules/scenes/coordinator.py`
- `apps/api/src/modules/scenes/events.py`
- `apps/api/src/modules/scenes/cleanup.py`
- `apps/api/src/modules/scenes/api.py`
- `apps/api/src/modules/scenes/test_plugins.py`
- `apps/api/alembic/versions/0007_scene_core_tables.py`

### 测试

- `apps/api/tests/unit/test_scene_plugin_protocol.py`
- `apps/api/tests/unit/test_scene_registry.py`
- `apps/api/tests/unit/test_scene_models.py`
- `apps/api/tests/unit/test_scene_state_machine.py`
- `apps/api/tests/unit/test_scene_participation.py`
- `apps/api/tests/unit/test_scene_privacy.py`
- `apps/api/tests/unit/test_scene_coordinator.py`
- `apps/api/tests/unit/test_scene_public_events.py`
- `apps/api/tests/unit/test_scene_voting.py`
- `apps/api/tests/unit/test_scene_cancel_expire.py`
- `apps/api/tests/unit/test_scene_cleanup.py`
- `apps/api/tests/unit/test_scene_boundary_plugin.py`
- `apps/api/tests/integration/test_scene_core_flow.py`

## 3. 验收摘要

- ScenePlugin Protocol 定义场景输入校验、私有胶囊、候选、评价、聚合、公开结果和清理接口。
- 场景注册表按 `scene_key + version` 管理插件，支持启停和能力查询。
- 私有提交使用加密 payload、最小胶囊、过期时间和软删除字段。
- 状态机覆盖合法转换、异常终态、重复请求和并发锁语义。
- 公开场景事件只包含阶段、提交人数、候选和公共结果，不包含私有偏好。
- 清理编排支持立即清理和最长 24 小时兜底。
- 边界测试插件覆盖跨用户读取、非法状态跳转、敏感字段返回并断言拒绝。

## 4. 验证摘要

- P8 专项测试：130 passed
- 当前最终 RC 验证以 P13 报告为准：1473 API tests passed，115 frontend tests passed

## 5. 边界声明

- 未实现具体业务场景；P9 在 P8 框架上实现宿舍聚餐。
- 未修改 P0/P1 冻结契约语义。
- 未引入真实密钥。
- 私有提交原文不进入公开事件、WebSocket 或管理后台。
