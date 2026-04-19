# CI/CD

本仓库按三个项目分别验证，CI/CD 入口统一放在 `.github/workflows/ci.yml`。

## CI 分层

1. 模型训练项目 `model-training`

   - 目标：验证训练代码的基础可导入性、数据结构、奖励函数和轻量单元逻辑。
   - 默认 CI 不下载大模型权重，不执行 GPU 训练，不上传模型产物。
   - 完整训练验证应在有 GPU、模型权重和训练数据权限的环境中运行。

2. 后端项目 `backend`

   - 目标：验证 FastAPI 路由、认证、邀请码、对话、多轮会话和数据接口。
   - CI 使用测试数据库，不依赖真实 VLLM 服务。
   - 涉及接口变更时必须同步更新 `backend/docs/api.md`。

3. 前端项目 `frontend`

   - 目标：验证 React 组件、路由、构建和基础交互。
   - 单元测试与生产构建在默认 CI 中执行。
   - Playwright 端到端测试可通过手动触发工作流运行。

## 推荐分支策略

- `main`：可部署主线。
- `feature/*`：功能开发分支。
- `fix/*`：缺陷修复分支。

合并到 `main` 前至少需要通过默认 CI。涉及前后端联动、认证、对话流式输出、后台管理或部署配置时，应额外运行 Playwright E2E。

## 部署流程

当前仓库提供 Docker Compose 部署入口：

```bash
cd deploy
docker compose up --build
```

部署前需要准备：

- `backend/.env`：真实后端运行配置和 VLLM 密钥。
- `frontend/.env`：前端 API 地址。
- 持久化数据库或对象存储方案：生产环境不建议长期使用本地 SQLite。

## 密钥管理

- 不允许提交真实 `VLLM_API_KEY`、JWT 密钥、云厂商密钥。
- `.env.example` 只保存字段名和安全占位值。
- GitHub Actions 中的生产密钥应通过 GitHub Secrets 或部署平台密钥管理注入。

