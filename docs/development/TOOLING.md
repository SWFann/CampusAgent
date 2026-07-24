# 开发工具链版本规范

> 本文档定义 CampusAgent 项目的工具版本基线，确保所有开发者在统一环境下工作。

**版本**：v1.0  
**更新日期**：2026-07-14  
**适用范围**：所有 P1-P13 开发任务

---

## 前端工具链

### Node.js

- **最低版本**：18.x LTS
- **推荐版本**：20.x LTS
- **当前 Windows 环境**：v22.19.0 ✅

**验证命令**：
```bash
node --version
```

**说明**：
- Next.js 14 要求 Node.js 18.x 或更高
- 建议使用 LTS 版本以获得长期支持
- 版本高于最低要求即可（如 v20.x、v22.x、v24.x）

### 包管理器

- **推荐**：pnpm 8.x+
- **备选**：npm 9.x+ / yarn 1.22.x+

**推荐 pnpm 的理由**：
- Monorepo 支持更好
- 磁盘空间效率高
- 安装速度快
- 严格的依赖管理

**验证命令**：
```bash
corepack pnpm --version
```

### TypeScript

- **最低版本**：5.0.0
- **推荐版本**：5.3.x

**验证命令**：
```bash
tsc --version
```

---

## 后端工具链

### Python

- **最低版本**：3.11
- **项目锁定版本**：3.11.15
- **环境位置**：`apps/api/.venv`（由 uv 管理）

**验证命令**：
```bash
uv run --project apps/api --extra dev --frozen python --version
```

**说明**：
- FastAPI 要求 Python 3.7+
- 推荐 3.11+ 以获得性能改进
- 版本高于最低要求即可

### uv

- **最低版本**：0.5
- **推荐版本**：最新稳定版

**验证命令**：
```bash
uv --version
```

`uv.lock` 是后端唯一锁文件。禁止对系统 Python 或用户 site-packages 执行 `pip install`。

---

## 基础设施

### Docker

- **最低版本**：24.x
- **推荐版本**：最新稳定版
- **当前环境**：未安装 ⚠️

**验证命令**：
```bash
docker --version
```

**安装指南**：
- [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- [Docker Engine for Linux](https://docs.docker.com/engine/install/)

### Docker Compose

- **最低版本**：2.20.0
- **推荐版本**：最新稳定版
- **当前环境**：未安装 ⚠️

**验证命令**：
```bash
docker compose version
```

**说明**：
- Docker Compose v2 已集成到 Docker Desktop
- Linux 需要单独安装 `docker-compose-plugin`

### Git

- **最低版本**：2.40.0
- **推荐版本**：最新稳定版
- **当前环境**：2.25.1 ⚠️

**验证命令**：
```bash
git --version
```

**说明**：
- 版本 2.25.1 可以工作，但建议升级到 2.40.0+
- 新版本提供更好的性能和安全性

---

## 开发工具（可选）

### 代码编辑器

- **推荐**：VS Code 1.85+
- **必备扩展**：
  - ESLint
  - Prettier
  - Python（Microsoft）
  - Pylance
  - Docker
  - GitLens

### 数据库工具

- **pgAdmin**：PostgreSQL 管理
- **Redis Insight**：Redis 可视化
- **DBeaver**：通用数据库工具

### API 测试工具

- **Postman** 或 **Insomnia**：API 测试
- **WebSocket King**：WebSocket 测试

---

## 版本检查脚本

项目提供版本检查脚本，自动验证环境是否符合要求：

```bash
# 运行版本检查
./scripts/check-versions.sh
```

**脚本功能**：
- ✅ 检查所有必需工具
- ✅ 验证版本是否符合最低要求
- ✅ 提供安装建议

---

## 环境配置建议

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/campus-agent.git
cd campus-agent

# 2. 运行版本检查
./scripts/check-versions.sh

# 3. 如果版本不符合，参考安装指南
# 4. 继续 P1-02：初始化 Workspace
```

### WSL 环境注意事项

如果在 WSL (Windows Subsystem for Linux) 环境下开发：

1. **安装 Docker Desktop for Windows** 并启用 WSL2 集成
2. **确保文件系统**：项目文件放在 Linux 文件系统（`~/`）而非 `/mnt/c/`
3. **端口映射**：Docker 端口正确映射到 Windows

---

## 版本升级策略

### 政策

- **主版本升级**（如 Node 18 → 20）：需要测试验证后统一升级
- **次版本升级**（如 Node 20.1 → 20.2）：可以随时升级
- **补丁版本升级**（如 Node 20.2.1 → 20.2.2）：建议及时升级

### 流程

1. 在开发分支测试升级
2. 更新 `TOOLING.md` 版本基线
3. 在团队通知中说明
4. 合并到主分支

---

## 常见问题

### Q: Node.js 版本过高会有问题吗？

A: 通常不会有问题，Next.js 和大多数库都兼容新版本。如果遇到兼容性问题，请使用 LTS 版本。

### Q: Python 3.13 可以使用吗？

A: 可以，项目要求 Python 3.11+，3.13 完全符合要求。

### Q: Docker 必须安装吗？

A: 是的，Docker 是本地开发环境的必备工具，用于运行 PostgreSQL、Redis 等依赖服务。

---

## 相关文档

- [开发计划表](../development/DEVELOPMENT_PLAN.md)
- [快速开始](../development/QUICK_START.md)
- [项目 README](../../README.md)

---

**维护者**：开发团队  
**最后更新**：2026-07-14
