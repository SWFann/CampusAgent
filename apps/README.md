# Apps

可部署应用目录。当前只有结构说明，尚未生成业务工程。

- `web/`：学生、教师和管理员使用的 Next.js Web 应用。
- `api/`：FastAPI 模块化单体、WebSocket Hub 和后台任务入口。

应用不得直接共享内部实现；跨应用契约通过 OpenAPI、WebSocket 事件和 `packages/` 中的生成物传递。
