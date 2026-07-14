# Codex R2/R3 工程整改记录

> 日期：2026-07-14  
> 范围：Claude 无法完成的本机环境、后端门禁、前端工具链、锁文件与 CI

## 已修复

- 隔离 `CampusAgent` Conda 环境，设置 `PYTHONNOUSERSITE=1`，避免用户级包污染；
- 新增 `requirements.lock` 与 `requirements-dev.txt`，本地和 CI 使用同一锁定依赖；
- 移除应用生命周期中的 `sys.exit`，生产环境错误改为可测试异常；
- 新增生产环境缺失变量、弱密钥和有效配置测试；
- 为 13 个业务模块补齐 `permissions.py`、`events.py`、`exceptions.py`；
- 新增模块模板和跨模块 ORM 导入边界测试；
- 生成 `pnpm-lock.yaml` 并验证 frozen install；
- 修复 ESLint、TypeScript、Jest 与 Playwright 测试边界；
- 根 `package.json` 提供 Windows/Linux 通用的 dev/test/lint/typecheck/build/e2e 命令；
- CI 增加后端依赖安装、锁文件安装、正确环境变量与强制 secret scan；
- 修正 Conda 路径、APP_ENV/APP_SECRET 和快速开始命令。

## 验证证据

| 门禁 | 结果 |
|---|---|
| API import | 通过 |
| pytest | 10 passed |
| Ruff | 0 errors |
| mypy strict | 0 errors |
| pnpm frozen install | 通过 |
| Web ESLint | 通过 |
| Web TypeScript | 通过 |
| Jest | 2 passed |
| Next.js production build | 通过，3 个静态路由 |
| Playwright Chromium | 1 passed（首页与健康页） |

## 仍未关闭

1. R1-06～R1-17 / R4-03：API 契约仍只有 41/68，缺少 27 个端点完整契约；
2. R4-01～R4-10：P0 最终验收记录存在“部分通过/失败却整体通过”的冲突；
3. R3-25 / R4-19：需要推送分支并观察 GitHub Actions；
4. R4-21：需要用全新临时 Conda 环境执行一次锁定依赖安装；
5. R4-22～R4-23：需要整理现有工作树、提交并进行正式 P1 评审。

## 下一执行顺序

1. 补齐 27 个 API 契约并重新执行 P0 验收；
2. 从干净环境复现 Python 与 pnpm 安装；
3. 整理并提交当前整改文件；
4. 推送整改分支，修复 GitHub Actions 直至全绿；
5. 签署 P1 评审记录后再进入 P2。
