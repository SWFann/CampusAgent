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
# 激活环境
conda activate CampusAgent

# 安装后端依赖
cd apps/api
pip install -r requirements.txt

# 或安装单个包
pip install <package-name>
```

### 当前已安装的包

- fastapi 0.139.0
- uvicorn 0.51.0
- pydantic 2.13.4
- pydantic-settings 2.14.2
- sqlalchemy 2.0.51
- alembic 1.18.5
- redis 8.0.1
- python-dotenv 1.2.2

## 注意事项

- 此环境独立于 base 环境
- 仅用于 CampusAgent 项目开发
- 不要在该环境中安装全局包

## 环境位置

```
/root/miniconda3/envs/CampusAgent
```
