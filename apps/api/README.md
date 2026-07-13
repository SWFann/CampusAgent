# API App（待实现）

计划采用 FastAPI 模块化单体。模块包括 `auth`、`users`、`organizations`、`directory`、`conversations`、`agents`、`memories`、`scenes`、`model_gateway`、`nodes`、`notifications`、`audit`、`admin` 和隔离的 `wellbeing` 域。

每个业务模块应按 API、Schema、Model、Repository、Service、Permission、Event、Exception 和 Tests 分层；模块之间禁止直接导入 ORM Model。
