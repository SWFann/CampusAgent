# CampusAgent uv 环境

CampusAgent 后端使用 uv 管理 Python 3.11、虚拟环境和锁定依赖，不向系统 Python 或用户 `site-packages` 安装任何内容。

## 环境边界

- Python 版本：`apps/api/.python-version`
- 依赖声明：`apps/api/pyproject.toml`
- 唯一锁文件：`apps/api/uv.lock`
- 虚拟环境：`apps/api/.venv`
- uv 缓存：`.local/uv-cache`
- uv 管理的 Python：`.local/uv-python`

上述运行时目录均已加入 `.gitignore`。

## 首次安装

```bash
make install
```

或直接运行：

```bash
UV_CACHE_DIR=.local/uv-cache \
UV_PYTHON_INSTALL_DIR=.local/uv-python \
uv sync --project apps/api --extra dev --frozen
```

## 常用命令

```bash
make test
make lint
make typecheck
make db-migrate

# 单独运行后端测试
uv run --project apps/api --extra dev --frozen \
  python -m pytest apps/api/tests -q
```

`uv run` 会自动使用 `apps/api/.venv`，无需 `source` 或手动激活。

## 更新依赖

```bash
uv add --project apps/api <package>
uv add --project apps/api --optional dev <dev-package>
uv lock --project apps/api
uv sync --project apps/api --extra dev --frozen
```

不要直接编辑 `uv.lock`，也不要使用全局 `pip install`。
