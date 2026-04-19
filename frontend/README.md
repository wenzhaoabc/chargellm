# ChargeLLM Frontend

前端应用是电池健康诊断 AI 助手的用户入口，面向普通体验用户、政府机构、企业客户和投资人展示。应用基于 React、Vite、TypeScript，重点提供产品介绍、邀请码准入、ChatGPT 风格对话、数据导入、历史对话和后台入口隔离。

## 目录

```text
frontend/
  src/
    components/   # 通用组件
    pages/        # 页面级组件
    services/     # API 客户端
    test/         # 测试工具
  e2e/            # Playwright 端到端测试
  docs/           # 前端设计与实现文档
```

## 本地运行

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

默认访问地址为 `http://127.0.0.1:5173`。本地开发时前端会通过 Vite 代理访问后端 `/api`。

## 配置

```env
VITE_API_BASE_URL=/api
```

部署到独立域名或静态资源服务时，可以把 `VITE_API_BASE_URL` 改成后端完整地址。

## 测试与构建

```bash
cd frontend
npm test -- --run
npm run build
npm run e2e -- --project=chromium
```

端到端测试会自动启动后端和前端开发服务，后端使用 `VLLM_MOCK=true`，避免测试依赖真实模型服务。

## 文档

- 前端实现计划：[docs/implementation_plan.md](docs/implementation_plan.md)
- 对话页改造计划：[docs/chat-workspace-ui-plan.md](docs/chat-workspace-ui-plan.md)

