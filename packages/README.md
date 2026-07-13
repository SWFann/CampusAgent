# Packages

共享包必须保持窄接口，不能成为绕过模块边界的公共杂物箱。

- `api-client/`：由 OpenAPI 生成的类型安全客户端；
- `shared-types/`：稳定的跨应用契约类型；
- `ui/`：设计令牌和无业务状态的共享组件；
- `config/`：lint、format、TypeScript 等通用工具配置。
