# ChargeLLM

电动自行车电池健康诊断平台 — 充电曲线 + 大模型 + 工具调用 + 内容安全。

## 仓库结构

```text
chargellm/
  model-training/   # 模型训练（SFT / GRPO / Qwen3-VL）
  frontend/         # React + Vite + Ant Design v6 + AntD X
  backend/          # FastAPI + SQLAlchemy + vLLM + Aliyun 内容安全
  deploy/           # Docker Compose、Nginx
  docs/             # 平台文档（本目录下）
```

## 文档导航

| 文档 | 适合谁读 | 内容 |
|---|---|---|
| **[docs/usage.md](docs/usage.md)** | 用户 / 管理员 / 开发者 | 入口、典型对话场景、后台操作、cURL 联调、扩展指南、FAQ |
| **[docs/platform.md](docs/platform.md)** | 后端/前端工程师 | 架构图、SSE 事件协议、所有 API 详解、数据流、源码索引 |
| [docs/ci-cd.md](docs/ci-cd.md) | 运维 | CI/CD 流程 |
| [model-training/README.md](model-training/README.md) | 算法 | 训练数据契约与流程 |

## Quick Start

```bash
# 后端
cd backend
cp .env.example .env             # 填入 vLLM / Aliyun / IOT_DB_URL 凭据
uv pip install -e ".[dev]"
uv pip install alibabacloud-green20220302 pymysql cryptography sse-starlette httpx
uv run uvicorn app.main:app --reload --port 8000

# 前端（另开终端）
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

更详细的扩展、测试、部署说明见 [docs/usage.md](docs/usage.md)。

## 核心特性

- **真实充电数据接入**：手机号 → IOT MySQL → 自动归并所有完成订单 + 时间序列后处理
- **流式 Agent Loop**：SSE 协议（`token` / `tool_call` / `tool_result` / `safety` / `done`），支持多轮工具调用
- **可扩展工具系统**：`@register_tool` 装饰器一行注册，`feed_back_to_model` 区分回注/纯展示
- **阿里云内容安全**：输入同步阻断 + 输出滚动窗口异步审核，命中即截流并友好回退
- **Ant Design X 对话界面**：Bubble + Sender + Markdown + ECharts markArea 高亮
- **完整后台**：用户/邀请码/数据集/对话历史/系统提示词/欢迎语 CRUD

## 测试

```bash
cd backend
uv run pytest                                                       # 默认 37 个，~8 秒
uv run pytest tests/live/ -v --override-ini="addopts="              # 真实 E2E 14 个，~2 分
```

Live 套件命中真实 vLLM + Aliyun + IOT MySQL，覆盖：纯文本对话 / 工具调用 / 多轮记忆 / 跨订单复用 / 输入越狱 / 输出过滤 / 配额限制 / 持久化等。
