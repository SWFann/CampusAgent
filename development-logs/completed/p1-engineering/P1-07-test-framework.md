---
task_id: P1-07
status: completed
stage: P1
title: 建立测试框架
started_at: 2026-07-14T10:10:00+09:00
completed_at: 2026-07-14T10:25:00+09:00
estimated_hours: 1.5
actual_hours: 0.75
---

# P1-07：建立测试框架

## 目标

建立前后端测试框架，确保代码质量。

**来自开发计划**：P1-07 - 建立测试框架

**产物**：
- pytest 配置（后端）
- 前端测试框架配置（Jest + Testing Library）
- Playwright E2E 空运行基线
- 测试目录结构

**依赖**：P1-03（Web工程 ✅）、P1-04（API工程 ✅）

## 验收标准

- [x] pytest 配置（后端）
- [x] pytest-asyncio 配置
- [x] 前端测试框架配置
- [x] Playwright E2E 配置
- [x] 测试目录结构
- [x] 空运行测试（验证框架可用）

## 测试策略

### 后端测试

- **单元测试**：pytest
- **异步测试**：pytest-asyncio
- **HTTP 测试**：httpx + AsyncClient
- **数据库测试**：SQLite in-memory（开发阶段）

### 前端测试

- **单元测试**：Jest + Testing Library
- **组件测试**：React Testing Library
- **E2E 测试**：Playwright

## 目录结构

### 后端

```
apps/api/tests/
├── conftest.py              # pytest 配置
├── unit/                    # 单元测试
│   ├── __init__.py
│   └── example_test.py
├── integration/             # 集成测试
│   ├── __init__.py
│   └── example_test.py
└── e2e/                     # E2E 测试
    ├── __init__.py
    └── example_test.py
```

### 前端

```
apps/web/
├── __tests__/               # Jest 测试
│   └── example.test.tsx
├── e2e/                     # Playwright 测试
│   └── example.spec.ts
├── jest.config.js
├── jest.setup.js
└── playwright.config.ts
```

## 配置详情

### pytest

- 测试环境：test
- 数据库：SQLite in-memory
- Redis：独立数据库（db=1）
- 异步测试：pytest-asyncio
- 覆盖率：集成在后续 CI 配置

### Jest

- 环境：jest-environment-jsdom
- 预设：next/jest
- 覆盖率：70% 阈值
- Path alias: `@/*` → `src/*`

### Playwright

- 浏览器：Chromium
- 并行测试：启用
- 重试：CI 环境 2 次
- Web Server：自动启动 Next.js dev server

## 示例测试

### 后端集成测试

```python
@pytest.mark.asyncio
async def test_health_live(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
```

### 前端单元测试

```typescript
it('renders CampusAgent title', () => {
  render(<HomePage />)
  const title = screen.getByText('CampusAgent')
  expect(title).toBeInTheDocument()
})
```

### Playwright E2E

```typescript
test('has title', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle('CampusAgent')
})
```

## 修改的文件

### 新增文件

**后端**：
- `apps/api/tests/conftest.py` - pytest 配置
- `apps/api/tests/unit/__init__.py`
- `apps/api/tests/unit/example_test.py`
- `apps/api/tests/integration/__init__.py`
- `apps/api/tests/integration/example_test.py`
- `apps/api/tests/e2e/__init__.py`
- `apps/api/tests/e2e/example_test.py`

**前端**：
- `apps/web/jest.config.js`
- `apps/web/jest.setup.js`
- `apps/web/__tests__/example.test.tsx`
- `apps/web/playwright.config.ts`
- `apps/web/e2e/example.spec.ts`

### 修改文件

- `apps/web/package.json` - 添加测试脚本和依赖

### 删除文件
- （无）

## 下一步

- **后续任务**：P1-08 建立统一命令
- **注意事项**：后续在根 package.json 添加统一的 test 命令

## 提交信息

- Commit: `test: establish pytest and Jest testing frameworks`
