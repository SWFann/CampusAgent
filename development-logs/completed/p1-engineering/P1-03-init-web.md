---
task_id: P1-03
status: completed
stage: P1
title: 初始化Web工程
started_at: 2026-07-14T08:45:00+09:00
completed_at: 2026-07-14T09:00:00+09:00
estimated_hours: 1.5
actual_hours: 0.75
---

# P1-03：初始化Web工程

## 目标

初始化 Next.js Web 应用项目结构，配置 TypeScript strict 模式。

**来自开发计划**：P1-03 - 初始化 Web 工程

**产物**：
- Next.js 14 App Router 项目
- TypeScript strict 配置
- 基础健康检查页（仅技术验证，不涉及UI设计）

**依赖**：P1-02（Workspace ✅）

## 验收标准

- [x] Next.js 14 App Router 项目初始化
- [x] TypeScript strict 模式
- [x] ESLint + Prettier 配置（P1-06前置）
- [x] 创建基础健康检查页（仅文本输出）
- [x] 项目可以在 `apps/web` 目录独立运行
- [x] 无 UI 设计相关代码

## 设计决策

### 重点：不涉及UI设计

根据用户要求，此阶段**只创建工程结构和必要配置**，不涉及：
- ❌ 具体的UI组件设计
- ❌ 页面布局和样式
- ❌ 颜色、字体等视觉设计
- ❌ 任何 shadcn/ui 组件安装

**只做**：
- ✅ 项目结构和配置
- ✅ 技术栈设置
- ✅ 基础路由和页面（纯文本）
- ✅ 开发工具链配置

## 项目结构

```
apps/web/
├── src/
│   ├── app/
│   │   ├── layout.tsx        # 根布局（极简）
│   │   ├── page.tsx          # 首页（仅文本）
│   │   └── health/           # 健康检查页
│   │       └── page.tsx
│   ├── lib/                  # 工具函数
│   │   └── utils.ts
│   └── middleware.ts         # 中间件（预留）
├── public/                   # 静态资源（空）
├── next.config.js
├── tsconfig.json
├── .eslintrc.json
├── .prettierrc
├── next-env.d.ts
├── package.json
└── README.md
```

## 技术配置

### TypeScript Strict

```json
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### Next.js Config

- React Strict Mode: 启用
- 无自定义UI相关配置
- 保留扩展性

### ESLint + Prettier

- ESLint: Next.js 核心规则
- Prettier: 统一代码风格
- 配置将在 P1-06 统一完善

## 修改的文件

### 新增文件
- `apps/web/package.json` - 项目配置
- `apps/web/next.config.js` - Next.js配置
- `apps/web/tsconfig.json` - TypeScript严格模式
- `apps/web/next-env.d.ts` - Next.js类型声明
- `apps/web/.eslintrc.json` - ESLint配置
- `apps/web/.prettierrc` - Prettier配置
- `apps/web/README.md` - 项目说明
- `apps/web/src/app/layout.tsx` - 根布局
- `apps/web/src/app/page.tsx` - 首页（纯文本）
- `apps/web/src/app/health/page.tsx` - 健康检查页
- `apps/web/src/lib/utils.ts` - 工具函数

### 修改文件
- （暂无）

### 删除文件
- （无）

## 下一步

- **后续任务**：P1-04 初始化 API 工程
- **注意事项**：不安装任何UI组件库，只创建基础配置

## 提交信息

- Commit: `feat(web): initialize Next.js app with TypeScript strict`
