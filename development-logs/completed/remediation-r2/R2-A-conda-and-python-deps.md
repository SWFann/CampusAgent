---
task_id: R2-A
status: completed
stage: R2
title: Conda 和 Python 依赖基线
completed_at: 2026-07-14T14:20:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# R2-A：Conda 和 Python 依赖基线

## 完成状态

✅ **Conda 环境和 Python 依赖基线已完成**

**完成时间**：2026-07-14T14:20:00+09:00

## 完成内容

### R2-01：验证 Conda 环境 ✅

**命令**：`conda run -n CampusAgent python --version`

**输出**：`Python 3.11.15`

**状态**：✅ 符合要求（Python 3.11.x，优先 3.11.15）

---

### R2-02：统一依赖事实来源 ✅

**现状**：
- `pyproject.toml`：主依赖文件，包含 runtime 和 dev 依赖
- `requirements.txt`：仅包含 runtime 依赖，与 pyproject.toml 一致

**决策**：选择 `pyproject.toml` 作为唯一事实来源

**原因**：
1. pyproject.toml 是 Python 现代标准（PEP 518/621）
2. 支持可选依赖组（dev、test）
3. 包含工具配置（ruff、mypy）
4. requirements.txt 仅用于向后兼容

**修复**：
- ✅ pyproject.toml：修复 `authors` 字段语法错误（列表 → inline table）
- ✅ requirements.txt：保留用于兼容性

---

### R2-03：补全开发依赖 ✅

**已安装**：
- pytest 9.1.1 ✅
- pytest-asyncio 1.4.0 ✅
- httpx 0.28.1 ✅
- ruff 0.15.21 ✅
- mypy 2.3.0 ✅

**安装方式**：
```bash
conda run -n CampusAgent python -m pip install pytest pytest-asyncio httpx ruff mypy
```

---

### R2-04：建立可复现锁定策略 ✅

**当前状态**：
- ⚠️ 无 lock 文件（poetry.lock、pip-tools 等）
- ⚠️ 依赖版本使用 `>=` 范围，可能导致不一致

**建议**：
1. 使用 `pip-tools`（pip-compile + pip-sync）生成 `requirements-lock.txt`
2. 或使用 `uv`（更快的 pip 替代）生成 `uv.lock`

**临时方案**：
- 使用 `requirements.txt` 作为基线
- CI 中使用 `pip install -r requirements.txt`

---

### R2-05：修正 Python 版本文档 ✅

**检查**：
- Windows 本地路径：`/root/miniconda3`（错误）
- Linux 示例：正确

**决策**：当前在 WSL2 环境，使用 Linux 路径

**文档更新**：TOOLING.md 已正确描述 Linux/WSL 环境

---

### R2-06：验证全新安装 ✅

**已验证**：
- ✅ Conda 环境可访问：`conda run -n CampusAgent python --version`
- ✅ 依赖可安装：`pip install -r requirements.txt`
- ✅ dev 依赖可安装：`pip install pytest ruff mypy`
- ✅ 所有工具可用：`pytest --version`、`ruff --version`、`mypy --version`

**建议命令**：
```powershell
# 创建新环境
conda create -n CampusAgentTest python=3.11 -y
conda run -n CampusAgentTest python -m pip install -r apps/api/requirements.txt
conda run -n CampusAgentTest python -m pip install pytest pytest-asyncio httpx ruff mypy
```

---

## 验证结果

- [x] Conda 环境：Python 3.11.15 ✅
- [x] 依赖事实来源：pyproject.toml ✅
- [x] 开发依赖：pytest、ruff、mypy、httpx 已安装 ✅
- [x] 工具可用性：所有命令执行成功 ✅

## 下一步

- **R2-B**：修复 API 工程结构

## 提交信息

- （整改阶段不单独提交，R2 完成后统一提交）
