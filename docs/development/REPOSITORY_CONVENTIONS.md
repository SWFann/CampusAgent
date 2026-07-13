# 仓库协作规范

## Monorepo 责任边界

- `apps/` 只放可部署应用；
- `packages/` 只放稳定共享契约与基础组件；
- `infra/` 只放部署、监控和运维资产；
- `docs/` 是产品、架构、接口、隐私和 ADR 的事实来源；
- `tests/e2e/` 从用户视角验证完整隐私协商闭环；
- 测试数据必须纯虚构且可重复生成。

## 后端模块模板

业务实现开始后，每个模块使用统一结构：

```text
module_name/
├── api.py
├── schemas.py
├── models.py
├── repository.py
├── service.py
├── permissions.py
├── events.py
├── exceptions.py
└── tests/
```

API 只做解析、鉴权和响应；Service 承载用例；Repository 不放业务规则；Schema 与 ORM 分离；Service 不向 API 返回 ORM 对象。

## 工程规则

- Python 函数必须有类型注解；TypeScript 开启 strict；
- UUID 作为实体 ID，时间以带时区 UTC 存储；
- 数据库变化只通过 Alembic；
- 外部调用设置超时、有限重试和熔断；
- 场景状态转换使用状态机；关键创建接口支持幂等；
- 前端不自行猜测后端字段，以生成的 API 类型为准；
- 不在 LocalStorage 保存敏感偏好，认证优先 HttpOnly Cookie；
- 禁止把业务逻辑堆入 `main.py` 或通用 `utils` 文件。

## Git 工作流

长期分支为 `main` 和可选的 `develop`。日常分支使用 `feature/`、`fix/`、`docs/` 前缀；提交遵循 Conventional Commits。

合并前至少完成：

1. 相关单元、集成、隐私和 E2E 测试；
2. OpenAPI、WebSocket 和事件文档同步；
3. 数据库迁移可从空库回放；
4. 敏感日志、密钥和真实数据扫描；
5. 模块边界检查；
6. 一名评审者批准；
7. 重要决策已记录 ADR。

## Definition of Done

一个功能只有在代码、测试、迁移、契约、权限规则、日志策略、运行说明和已知限制都齐备时才算完成。隐私相关功能还必须说明数据类别、用途、授权、保存期限、清理路径和失败行为。
