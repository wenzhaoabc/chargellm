# ChargeLLM Backend

后端服务负责电池健康诊断 AI 助手的认证、邀请码、对话、数据集、后台管理和 VLLM 模型接入。服务基于 FastAPI，业务接口统一使用 `/api` 前缀。

## 目录

```text
backend/
  app/
    api/        # HTTP 路由
    core/       # 配置与安全能力
    db/         # 数据库会话
    models/     # SQLAlchemy 数据模型
    schemas/    # Pydantic 请求与响应结构
    services/   # 业务服务与模型调用
  tests/        # 后端测试
  docs/         # 后端接口文档
```

## 本地运行

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后可访问：

- 健康检查：`http://127.0.0.1:8000/api/health`
- OpenAPI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

## 配置

主要配置项在 `backend/.env.example` 中维护：

- `DATABASE_URL`：数据库连接，默认使用 SQLite。
- `JWT_SECRET`：后台登录和邀请码会话的签名密钥。
- `ADMIN_USERNAME`、`ADMIN_PASSWORD`：后台管理员临时账号。
- `CHARGELLM_INVITE_DEFAULT_MAX_USES`、`CHARGELLM_INVITE_DEFAULT_PER_USER_QUOTA`：邀请码默认调用额度。
- `VLLM_MOCK`：是否启用模型模拟输出。
- `VLLM_BASE_URL`、`VLLM_MODEL`、`VLLM_API_KEY`：真实 VLLM OpenAI-compatible 服务配置。
- `CORS_ALLOW_ORIGINS`：允许访问后端的前端来源。

真实密钥不要写入 `.env.example`，只写入本地 `backend/.env` 或部署环境变量。

## 测试

```bash
cd backend
pytest tests -q
```

## 接口文档

后端接口说明见 [docs/api.md](docs/api.md)。代码变更涉及接口行为时，应同步更新该文档。
