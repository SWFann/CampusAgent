---
task_id: REALTIME-AGENT-DINNER
status: completed
started_at: 2026-07-18T23:30:00+08:00
completed_at: 2026-07-19T00:15:00+08:00
---

# 实时群聊与智能体聚餐投票

## 目标

- 让场景公共消息进入统一实时事件链路；
- 将宿舍聚餐改为群聊中的可展开投票消息；
- 使用 StepFun Search 和 `step-3.7-flash` 生成有来源的真实推荐；
- 支持多次、每次 1–10 轮的智能体协商和场景内记忆；
- 仅允许发起人关闭投票或结束聚餐。

## 实现摘要

- 新增 StepFun 真实搜索与证据约束适配器，候选必须引用搜索返回的 HTTPS 来源；
- 删除聊天聚餐辅助流程中的固定虚构餐厅；
- 新增统一系统消息写入服务，事务提交后发布 `MessageCreated`；
- 群聊输入区新增“宿舍聚餐”按钮，场景以消息卡片和弹窗呈现；
- 增加城市、校区/出发地点、私密补充需求、来源链接和到店前确认提示；
- 增加反对/请求下一次协商、发起人关闭投票和结束场景操作；
- API Key 仅通过服务端环境变量读取，未写入仓库。

## 验证结果

- `ruff check apps/api --no-cache`：通过；
- `mypy apps/api/src apps/api/tests --no-incremental`：332 个源文件通过；
- `pytest apps/api/tests/unit apps/api/tests/integration`：1389 项通过；
- Web `typecheck`：通过；
- Web `lint`：通过；
- Web Jest：115 项通过；
- Web production build：通过；
- `scripts/security/check_no_secrets.py`：扫描 819 个文件，无真实密钥。

## 安全说明

需求对话中暴露的旧 Key 未被使用或保存。部署前必须在 StepFun 控制台轮换，并通过 `MODEL_GATEWAY_API_KEY` 注入新 Key。
