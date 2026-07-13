# Infrastructure（待实现）

该目录将承载 Docker Compose、本地依赖、监控配置和可重复执行的运维脚本。首个可运行版本应支持离线 Demo，并提供 PostgreSQL、Redis、Mock Model Server，以及可选的 MinIO/Prometheus。

任何凭据都必须通过环境变量或密钥服务注入，不能写入仓库。
