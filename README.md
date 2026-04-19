# ChargeLLM

电动自行车电池健康诊断大模型项目仓库。仓库按三个同级项目组织：AI 模型训练、前端应用、后端服务；部署与 CI/CD 作为仓库级工程资产统一维护。

## 目录结构

```text
chargellm/
  model-training/   # AI 模型训练、数据契约、SFT/GRPO、推理验证
  frontend/         # React + Vite 前端应用
  backend/          # FastAPI 后端服务、认证、对话、数据源、管理接口
  deploy/           # Docker Compose、Nginx、镜像构建文件
  docs/             # 仓库级文档，包含 CI/CD 与历史归档
  .github/          # GitHub Actions 与仓库协作配置
```

## 快速启动

后端：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

模型训练：

```bash
cd model-training
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
pytest
```

容器部署：

```bash
cd deploy
docker compose up --build
```

## 子项目文档

- 模型训练：[model-training/README.md](model-training/README.md)
- 后端服务：[backend/README.md](backend/README.md)
- 前端应用：[frontend/README.md](frontend/README.md)
- 统一 CI/CD：[docs/ci-cd.md](docs/ci-cd.md)

## 配置说明

- 后端运行配置放在 `backend/.env`，模板为 `backend/.env.example`。
- 前端运行配置放在 `frontend/.env`，模板为 `frontend/.env.example`。
- `backend/.env.example` 不保存真实密钥，接入真实 VLLM 时需要在本地或部署环境写入 `VLLM_BASE_URL`、`VLLM_MODEL`、`VLLM_API_KEY`。
- 训练产物、模型权重、本地数据库、前端依赖与构建结果已在 `.gitignore` 中排除，不应提交到仓库。

