---
task_id: P1-09
status: completed
stage: P1
title: 建立环境变量校验
started_at: 2026-07-14T10:50:00+09:00
completed_at: 2026-07-14T11:00:00+09:00
estimated_hours: 1
actual_hours: 0.5
---

# P1-09：建立环境变量校验

## 目标

建立环境变量管理机制，确保配置安全和一致性。

**来自开发计划**：P1-09 - 建立环境变量校验

**产物**：
- `.env.example` 文件
- 环境变量校验逻辑
- 测试环境默认值

**依赖**：P1-04（API工程 ✅）

## 验收标准

- [x] `.env.example` 文件
- [x] 环境变量校验（启动时）
- [x] 测试环境默认值
- [x] 敏感信息不提交

## 环境变量清单

### 必需变量

| 变量名 | 描述 | 类型 | 示例 |
|--------|------|------|------|
| `APP_ENV` | 运行环境 | string | `development` |
| `DATABASE_URL` | 数据库连接 | string | `postgresql://...` |
| `REDIS_URL` | Redis 连接 | string | `redis://...` |

### 安全相关

| 变量名 | 描述 | 类型 | 要求 |
|--------|------|------|------|
| `APP_SECRET` | JWT 密钥 | string | ≥32 字符（生产环境） |
| `FIELD_ENCRYPTION_KEY` | 字段加密密钥 | string | ≥32 字符（生产环境） |

### 可选变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `DEBUG` | 调试模式 | `false` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `ENABLE_EXTERNAL_MODEL` | 启用外部模型 | `false` |
| `PRIVATE_SCENE_TTL_HOURS` | 私有场景 TTL | `24` |

## 环境变量校验

### 校验逻辑

1. **所有环境**：检查 APP_ENV, DATABASE_URL, REDIS_URL
2. **生产环境**：
   - 检查 APP_SECRET 长度 ≥ 32
   - 检查 FIELD_ENCRYPTION_KEY 长度 ≥ 32
   - 检查所有必需变量

### 使用方式

```python
# 应用启动时自动校验
from src.main import create_app

app = create_app()  # 触发环境校验
```

### 校验失败处理

- 打印错误信息
- 列出缺失变量
- 退出进程（exit code 1）

## 修改的文件

### 新增/更新文件
- `.env.example` ✅ - 完整的模板文件（已存在并更新）
- `apps/api/src/middleware/env_validation.py` ✅ - 环境校验
- `apps/api/src/config.py` ✅ - 更新配置类

### 修改文件
- （暂无）

### 删除文件
- （无）

## 安全措施

### 1. .env 不被提交

`.gitignore` 已包含：
```
.env
.env.*
!.env.example
```

### 2. 生产环境强制校验

- SECRET_KEY 长度 ≥ 32
- ENCRYPTION_KEY 长度 ≥ 32
- 所有必需变量必须设置

### 3. 测试环境默认值

```python
# tests/conftest.py
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
```

## 下一步

- **后续任务**：P1-10 建立 CI
- **注意事项**：.env 文件不应该出现在任何提交中

## 提交信息

- Commit: `chore(config): add environment variable validation`
