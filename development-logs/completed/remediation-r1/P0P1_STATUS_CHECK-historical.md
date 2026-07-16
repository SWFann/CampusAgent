# P0/P1 整改现状检查报告

> 日期：2026-07-14
> 检查范围：P0、P1 整改完成情况

> 历史说明：本报告记录 2026-07-14 的中间态问题清单，不作为当前权威状态。2026-07-16 R1-32～R1-36 收口后，API 契约口径已更新为 68 个 MVP HTTP 端点 + 3 个 internal 端点 = 71 个总文档化端点，pnpm frozen install 已本地通过；远端 CI 观察仍需用户授权推送后完成。

## CODEX 文档记录 vs 实际验证

### 后端验证

| 门禁 | CODEX 记录 | 实际验证 | 状态 |
|------|-----------|---------|------|
| API import | 通过 | 通过 ✅ | 一致 |
| pytest | 10 passed | 3 passed | ⚠️ 差异 |
| Ruff | 0 errors | 0 errors ✅ | 一致 |
| **mypy strict** | **0 errors** | **19 errors** | ❌ **严重差异** |

### 前端验证

| 门禁 | CODEX 记录 | 实际验证 | 状态 |
|------|-----------|---------|------|
| pnpm frozen install | 通过 | ❌ EACCES 权限错误 | ❌ 失败 |
| Web ESLint | 通过 | 未验证（安装失败） | ⚠️ 待验证 |
| Web TypeScript | 通过 | 未验证（安装失败） | ⚠️ 待验证 |
| Jest | 2 passed | 未验证（安装失败） | ⚠️ 待验证 |
| Next.js build | 通过 | 未验证（安装失败） | ⚠️ 待验证 |
| Playwright | 1 passed | 未验证（安装失败） | ⚠️ 待验证 |

### 文档一致性

| 项目 | 问题 |
|------|------|
| R4-03 | API 契约覆盖率 41/68（60.3%），CODEX 也标注此问题 |
| R4-01 | MVP scope 描述，CODEX 未明确是否通过 |
| R4-02 | 角色 ADR，CODEX 未单独标注 |

## 关键问题

### 1. mypy strict 0 errors（严重）

**CODEX 声称**：mypy strict 0 errors
**实际发现**：19 errors（缺少类型注解）

**差异原因分析**：
- CODEX 使用了 `--ignore-missing-imports` 标志
- 实际应该使用 strict 模式（pyproject.toml 配置）

**影响**：
- pyproject.toml 中设置了 `strict = true`
- 但 CODEX 验证时可能忽略了此配置
- 这导致 P1 门禁实际上未通过

### 2. pytest 数量差异

**CODEX 声称**：10 passed
**实际发现**：3 passed

**差异原因分析**：
- CODEX 可能运行了更多测试
- 当前只有 1 个测试文件（test_app_factory.py）

### 3. pnpm install 失败

**CODEX 声称**：pnpm frozen install 通过
**实际发现**：EACCES 权限错误

**差异原因分析**：
- WSL2 文件系统权限问题
- 可能在 CODEX 环境中是 Linux 原生环境

## 下一步行动

### 必须完成

1. **修复 mypy strict 配置问题**
   - 选项 A：保持 strict = true，修复所有类型错误（P2 任务）
   - 选项 B：暂时关闭 strict，P2 阶段逐步开启

2. **修复 pnpm install 权限问题**
   - 检查 node_modules 权限
   - 尝试以不同用户身份运行
   - 或使用 Docker 进行前端构建

3. **补充 pytest 测试**
   - 当前只有 3 个测试
   - CODEX 记录了 10 个测试

4. **补充 API 契约**
   - 41/68（60.3%）
   - CODEX 也标注此问题

### 建议

根据执行规则"不允许通过修改完成总结、进度表或勾选状态来掩盖实际缺口"，建议：

1. **立即修复 mypy 配置问题**：明确是否使用 strict 模式
2. **修复 pnpm 安装问题**：清理 node_modules 并重新安装
3. **补充测试**：达到 CODEX 记录的 10 个测试

### 需要决策

1. **mypy strict 模式**：
   - 是否现在修复 19 个类型错误？
   - 还是暂时调整配置，P2 阶段修复？

2. **pnpm install 权限问题**：
   - 是否现在修复（chown/chmod）？
   - 还是使用 Docker？

3. **API 契约覆盖率**：
   - 是否现在补充 27 个端点文档？
   - 还是保持现状，P2 实现时补充？

---

**检查日期**：2026-07-14
**检查人**：Claude
**状态**：发现问题，待决策
