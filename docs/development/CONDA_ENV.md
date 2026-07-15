# CampusAgent Conda 环境

**环境名称**：CampusAgent  
**Python 版本**：3.11.15  
**创建日期**：2026-07-14

## 使用说明

### 激活环境

```bash
conda activate CampusAgent
```

### 停用环境

```bash
conda deactivate
```

### 查看环境

```bash
conda env list
```

### 安装依赖

```bash
# 安装经过验证的完整依赖集合
conda run -n CampusAgent python -m pip install -r apps/api/requirements.lock
```

### 依赖来源

- `apps/api/pyproject.toml`：依赖声明与工具配置的权威来源；
- `apps/api/requirements.lock`：本地和 CI 使用的已验证锁定集合；
- `apps/api/requirements.txt`、`requirements-dev.txt`：人工升级时使用的依赖分组。

## 注意事项

- 此环境独立于 base 环境
- 仅用于 CampusAgent 项目开发
- 环境变量 `PYTHONNOUSERSITE=1`，禁止继承用户级 Python 包
- 不要使用裸 `pip`，统一使用 `conda run -n CampusAgent python -m pip`

## 环境位置

Windows 当前环境：`D:\Conda\Soft\envs\CampusAgent`

Linux/WSL 环境路径由 `conda env list` 决定，不应假定为 `/root/miniconda3`。
