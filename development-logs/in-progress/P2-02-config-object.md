---
task_id: P2-02
task_name: 建立配置对象
status: in_review
started_at: 2026-07-16T16:30:00+08:00
completed_at: 2026-07-16T17:15:00+08:00
actual_hours: 0.75
owner: Claude
auditor: Codex
---

# P2-02: 建立配置对象

## 1. 背景

- P2-01 Docker Compose 基线已通过 Codex 二次审计。
- 当前路径：`/root/CampusAgent`
- 当前分支：`main`，基准提交 `5124c09 docs(project): record remote CI completion`
- P2-01 未提交修改完整保留，未回滚、未覆盖。
- 本次任务只做 P2-02：建立配置对象。

## 2. 修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/config.py` | 重写 | 引入 `AppEnv` StrEnum、`SecretStr` 敏感字段、`model_validator` 生产校验、`safe_model_dump()` |
| `apps/api/src/middleware/env_validation.py` | 修改 | 移除与 Settings 重复的密钥强度检查，保留轻量启动时非空防线 |
| `apps/api/src/main.py` | 修改 | lifespan 中传给 `validate_production_env` 的 SecretStr 字段改用 `.get_secret_value()`，APP_ENV 枚举用 `str()` |
| `apps/api/tests/unit/test_config.py` | 新增 | 9 组测试覆盖默认加载、枚举校验、Secret 不泄露、显式读取、生产失败关闭、外部模型 API Key、.env.example 对齐、App factory 集成 |
| `apps/api/tests/unit/test_env_validation.py` | 修改 | 移除已迁移到 Settings 的强度检查测试，新增空值检测测试 |
| `compose.yaml` | 修改 | 补充 `MODEL_GATEWAY_API_KEY: ""` 到 api.environment，与 Settings 字段对齐 |

## 3. Settings 设计说明

### 3.1 AppEnv 类型

使用 `enum.StrEnum`（Python 3.11+），值为 `development` / `test` / `production`。
非法 `APP_ENV` 会导致 Pydantic `ValidationError`。

### 3.2 Secret 字段

以下字段使用 `pydantic.SecretStr`：
- `APP_SECRET`
- `FIELD_ENCRYPTION_KEY`
- `MODEL_GATEWAY_API_KEY`

`repr(settings)` 和 `str(settings.APP_SECRET)` 显示遮蔽形式 `**********`，不泄露明文。
读取真实值必须显式调用 `.get_secret_value()`。

### 3.3 默认值策略

- development / test：使用开发默认值（`dev-secret-key-change-in-production` 等）
- production：禁止使用开发默认密钥，密钥长度 >= 32，`LOG_PROMPT_CONTENT` 必须为 `False`

### 3.4 Production 失败关闭规则

通过 `@model_validator(mode="after")` 实现，在 Settings 构造时即校验：

**所有环境生效：**
- `ENABLE_EXTERNAL_MODEL=true` 时 `MODEL_GATEWAY_API_KEY` 必须非空

**仅 production 生效：**
- `APP_SECRET` 不得为开发默认值，长度 >= 32
- `FIELD_ENCRYPTION_KEY` 不得为开发默认值，长度 >= 32
- `LOG_PROMPT_CONTENT` 必须为 `False`

### 3.5 Safe dump / repr 策略

- `safe_model_dump()` 返回字典，敏感字段显示 `"**********"`
- `repr()` 和 `str()` 不泄露明文（由 SecretStr 内建遮蔽保证）
- 错误消息中不包含密钥明文

### 3.6 与 env_validation 的关系

`env_validation.py` 的 `validate_production_env` 保留为启动时轻量防线（深度防御），仅检查必要变量非空。
密钥强度检查已迁移到 Settings 的 `model_validator`，避免两套冲突规则。

## 4. 与 .env.example / compose.yaml 对齐说明

### .env.example

已包含所有 Settings 面向环境变量的字段（18 个），包括 `MODEL_GATEWAY_BASE_URL` 和 `MODEL_GATEWAY_API_KEY`。
本次未修改 `.env.example`（P2-01 已对齐）。

### compose.yaml

补充 `MODEL_GATEWAY_API_KEY: ""` 到 `api.environment`，使所有 Settings 字段在 Compose 中都有对应环境变量。
未改变服务结构、网络、卷、端口、healthcheck。

## 5. 新增测试列表

| 测试文件 | 测试用例 | 覆盖点 |
|---|---|---|
| `test_config.py` | `TestDefaultSettings::test_settings_loads_with_defaults` | 默认 Settings 可加载 |
| `test_config.py` | `TestDefaultSettings::test_app_env_defaults_to_development` | APP_ENV 默认为 development |
| `test_config.py` | `TestDefaultSettings::test_debug_is_bool` | DEBUG 是 bool |
| `test_config.py` | `TestDefaultSettings::test_url_fields_exist` | URL 字段存在 |
| `test_config.py` | `TestAppEnvValidation::test_valid_app_env_values` | 合法 APP_ENV 值 |
| `test_config.py` | `TestAppEnvValidation::test_invalid_app_env_rejected` | 非法 APP_ENV 被拒绝 |
| `test_config.py` | `TestSecretNonLeakage::test_repr_does_not_contain_dev_secret` | repr 不泄露 APP_SECRET |
| `test_config.py` | `TestSecretNonLeakage::test_repr_does_not_contain_dev_encryption_key` | repr 不泄露 FIELD_ENCRYPTION_KEY |
| `test_config.py` | `TestSecretNonLeakage::test_str_of_secret_field_does_not_leak` | str() 不泄露明文 |
| `test_config.py` | `TestSecretNonLeakage::test_safe_model_dump_does_not_leak` | safe dump 不泄露明文 |
| `test_config.py` | `TestSecretValueAccess::test_get_secret_value_returns_app_secret` | 显式读取 APP_SECRET 明文 |
| `test_config.py` | `TestSecretValueAccess::test_get_secret_value_returns_encryption_key` | 显式读取 FIELD_ENCRYPTION_KEY 明文 |
| `test_config.py` | `TestSecretValueAccess::test_secret_fields_are_secret_str_type` | 字段类型为 SecretStr |
| `test_config.py` | `TestProductionSecretDefaults::*` (5 cases) | 生产环境默认/弱密钥失败关闭 |
| `test_config.py` | `TestProductionLogPromptContent::*` (2 cases) | 生产 LOG_PROMPT_CONTENT=true 失败 |
| `test_config.py` | `TestExternalModelApiKey::*` (3 cases) | 外部模型 API Key 必填逻辑 |
| `test_config.py` | `TestEnvExampleAlignment::test_env_example_contains_field` (18 cases) | .env.example 字段对齐 |
| `test_config.py` | `TestAppFactoryIntegration::test_create_app_with_secret_str_settings` | create_app 兼容 SecretStr |
| `test_config.py` | `TestAppFactoryIntegration::test_create_app_default_settings_works` | create_app() 默认可用 |
| `test_env_validation.py` | `test_production_environment_rejects_empty_keys` | 空值检测 |

## 6. 验证命令和结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 139 source files | |
| `python -m pytest apps/api/tests -q -p no:cacheprovider` | 54 passed in 0.25s | |
| `corepack pnpm lint` | All checks passed! | 前端 + API |
| `corepack pnpm typecheck` | Success: no issues found in 139 source files | 前端 + API |
| `corepack pnpm test` | 54 passed (API) + 2 passed (Web) | |

## 7. 边界声明

- 未执行 P2-03～P2-14
- 未接入 PostgreSQL
- 未初始化 Alembic
- 未实现 Redis 客户端
- 未实现 API Envelope
- 未修改 P0/P1 冻结契约
- 未修改业务模块代码
- 未提交、未推送，等待 Codex 审计

---

## Codex 二次审计整改

### 整改日期

2026-07-16

### 阻塞问题 1：DEBUG 环境变量污染导致 API import 失败

**问题**：Settings 直接读取通用环境变量 `DEBUG`，宿主 shell 中 `DEBUG=release` 会导致 Pydantic bool 解析失败，API 无法导入。

**根因**：`DEBUG` 是非常泛的环境变量名，可能被系统、IDE、shell 或其他工具设置成 `release`/`1`/`verbose` 等非 Pydantic bool 值。

**整改**：
- `apps/api/src/config.py`：`DEBUG` 字段改用 `Field(default=False, validation_alias="APP_DEBUG")`，Python 属性名仍为 `DEBUG`，但环境变量来源改为 `APP_DEBUG`
- `.env.example`：`DEBUG=false` 改为 `APP_DEBUG=false`
- `compose.yaml`：`DEBUG: "false"` 改为 `APP_DEBUG: "false"`
- `apps/api/tests/conftest.py`：`os.environ["DEBUG"]` 改为 `os.environ["APP_DEBUG"]`
- `apps/api/tests/unit/test_config.py`：`_SETTINGS_ENV_VARS` 和 `.env.example` 对齐测试中 `DEBUG` 改为 `APP_DEBUG`

**新增测试**：
- `TestDebugEnvPollution::test_ambient_debug_release_does_not_break_settings`：`DEBUG=release` 不影响 Settings 加载
- `TestDebugEnvPollution::test_app_debug_true_sets_debug_true`：`APP_DEBUG=true` 生效
- `TestDebugEnvPollution::test_app_debug_invalid_value_raises`：`APP_DEBUG=not-bool` 失败
- `TestDebugEnvPollution::test_api_import_survives_debug_release`：`DEBUG=release` 下 API import 成功

### 阻塞问题 2：.env.example 中 APP_ENV 重复冲突

**问题**：`.env.example` 中 `APP_ENV` 出现两次（顶部 `APP_ENV=development`，末尾 `APP_ENV=test`）。

**整改**：
- 删除末尾 Testing 小节中的 `APP_ENV=test` 实际赋值行
- 改为注释说明：`# Test runner overrides APP_ENV=test in apps/api/tests/conftest.py.`
- `# Do not set APP_ENV=test in the default development .env template.`

**新增测试**：
- `TestEnvExampleKeyUniqueness::test_app_env_appears_once`：APP_ENV 只出现一次
- `TestEnvExampleKeyUniqueness::test_app_debug_appears_once`：APP_DEBUG 只出现一次
- `TestEnvExampleKeyUniqueness::test_debug_does_not_appear`：DEBUG 不出现

### 整改后修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `apps/api/src/config.py` | 修改 | `DEBUG` 字段改用 `validation_alias="APP_DEBUG"` |
| `.env.example` | 修改 | `DEBUG=false` → `APP_DEBUG=false`；删除末尾 `APP_ENV=test`，改为注释 |
| `compose.yaml` | 修改 | `DEBUG: "false"` → `APP_DEBUG: "false"` |
| `apps/api/tests/conftest.py` | 修改 | `os.environ["DEBUG"]` → `os.environ["APP_DEBUG"]` |
| `apps/api/tests/unit/test_config.py` | 修改 | 环境变量列表和对齐测试中 `DEBUG` → `APP_DEBUG`；新增 `TestDebugEnvPollution` (4 cases) 和 `TestEnvExampleKeyUniqueness` (3 cases) |

### 整改后自检命令和结果

| 命令 | 结果 | 备注 |
|---|---|---|
| `ruff check apps/api --no-cache` | All checks passed! | |
| `mypy apps/api/src apps/api/tests --no-incremental` | Success: no issues found in 139 source files | |
| `python -m pytest apps/api/tests -q -p no:cacheprovider` | 61 passed in 0.25s | |
| `DEBUG=release python -c "...import src.main..."` | API_IMPORT_OK | 关键复现命令 |
| `APP_DEBUG=true python -c "...Settings(_env_file=None)..."` | APP_DEBUG_TRUE_OK | APP_DEBUG 生效验证 |
| `.env.example` 键值唯一性验证 | ENV_EXAMPLE_KEYS_OK | |
| `corepack pnpm lint` | All checks passed! | |
| `corepack pnpm typecheck` | Success: no issues found in 139 source files | |
| `corepack pnpm test` | 61 passed (API) + 2 passed (Web) | |

### 整改后边界声明

- 未执行 P2-03～P2-14
- 未接入 PostgreSQL
- 未初始化 Alembic
- 未实现 Redis 客户端
- 未实现 API Envelope
- 未修改 P0/P1 冻结契约
- 未提交、未推送，等待 Codex 复审
