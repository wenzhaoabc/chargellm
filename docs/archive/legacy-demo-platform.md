# ChargeLLM Demo Platform

这是一个面向演示和客户试用的轻量平台骨架，目标是提供基本工程化部署能力、清晰的运行说明，以及后续扩展到真实模型和真实历史充电记录的入口。

当前约定如下：

- 普通用户输入邀请码后，可以直接体验平台内置示例数据；
- 普通用户查询自己的真实历史充电记录时，才需要手机号 + 短信验证码；
- 管理员使用独立的账号密码登录；
- 后端默认监听 `8000`；
- 前端容器内使用 `nginx:80` 对外暴露，Docker Compose 默认映射到宿主机 `3000`；
- SQLite 数据通过 Docker volume 持久化；
- 默认支持 `VLLM_MOCK=true`，不依赖真实模型也可以跑通整个平台。

## 目录约定

本仓库当前只补齐部署层文件，应用代码后续按如下结构放入 `demo_platform/` 下：

```text
demo_platform/
  backend/
  frontend/
  deploy/
```

部署文件默认按这个约定工作。

## 默认体验流程

1. 管理员先登录后台，创建邀请码并设置可用次数。
2. 普通用户输入邀请码，直接进入示例数据体验。
3. 用户选择示例电池，查看充电曲线并发起提问。
4. 后端进行合规检查，拼接上下文，调用 vLLM 或 mock 模式。
5. 后端通过 SSE 把分析过程和结果推送到前端。
6. 用户如需查看真实历史充电记录，再走手机号 + 短信验证码流程。

## 默认账号与测试配置

推荐在开发环境使用以下默认配置：

```text
管理员用户名: admin
管理员密码: ChangeMe123!
短信验证码 mock: 123456
VLLM_MOCK: true
```

上线或对外试用前，请务必替换管理员密码和其它敏感配置。

## 环境变量

复制示例文件并按需修改：

```bash
cp demo_platform/.env.example demo_platform/.env
```

关键配置如下：

- `DATABASE_URL`：SQLite 数据库路径，默认使用 `backend/data` 下的文件；
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`：管理员初始账号；
- `SMS_MOCK_CODE`：开发环境短信验证码；
- `VLLM_MOCK`：是否启用模型 mock；
- `VLLM_BASE_URL` / `VLLM_MODEL` / `VLLM_API_KEY`：真实模型接入时使用，后端按 OpenAI Chat Completions 兼容格式调用；
- `ALIYUN_*`：阿里云内容安全相关配置；
- `VITE_API_BASE_URL`：前端调用后端 API 的地址，Compose 默认走 `/api`。

后端接口说明见 [`docs/demo_platform_backend_api.md`](../docs/demo_platform_backend_api.md)，运行中也可访问 FastAPI 自动文档：`/docs`、`/redoc`、`/openapi.json`。

## 本地开发

### 后端

后端代码准备好后，建议在 `demo_platform/backend/` 下本地启动：

```bash
cd demo_platform/backend
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

如果后端工程使用 `pyproject.toml` 或其它依赖管理方式，请按实际工程约定安装依赖；核心要求是服务监听 `8000`，并确保 `/api` 路由可用。

### 前端

前端代码准备好后，建议在 `demo_platform/frontend/` 下本地启动：

```bash
cd demo_platform/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

开发态前端可直接把 API 指向后端本地地址，例如 `http://127.0.0.1:8000`。

## Docker Compose

推荐在 `demo_platform/deploy/` 目录下启动：

```bash
cd demo_platform/deploy
docker compose up --build
```

默认访问地址：

- 前端：`http://127.0.0.1:3000`
- 后端：`http://127.0.0.1:8000`

### 运行说明

- 前端容器使用 Nginx 提供静态资源，并把 `/api/` 代理到后端；
- 后端默认读取 `../.env`，你可以把 `demo_platform/.env.example` 复制成 `demo_platform/.env`；
- SQLite 数据默认写入 Docker volume，容器重建后不会丢失；
- `VLLM_MOCK=true` 时，后端不会强依赖真实模型服务，适合先跑通 demo。
- 这个 Compose 文件默认按 `demo_platform/backend/` 和 `demo_platform/frontend/` 的目录约定构建，待对应应用代码就绪后即可直接启动。

## 邀请码体验

普通用户在示例体验页输入邀请码即可进入平台，不需要手机号登录。

建议的使用规则：

- 邀请码由管理员创建；
- 邀请码包含总次数或每用户次数限制；
- 用户每次成功完成一次诊断，扣减一次次数；
- 次数用完后，前端显示“体验已用尽”；
- 失败的合规审核、模型拒答、模型调用失败，不扣次数。

## 手机号验证码体验

手机号 + 短信验证码只用于查询用户本人真实历史充电记录。

开发阶段可以先使用：

- 固定验证码 `123456`；
- 后端 mock 的短信发送接口；
- 真实短信服务留作后续接入。

## 管理员后台

管理员后台建议保留最少能力：

- 登录 / 退出；
- 邀请码管理；
- 用户体验记录；
- 诊断记录查看。

后台不做复杂报表，重点是能管理公测邀请和试用额度。

## 部署建议

1. 先启动后端，再启动前端；
2. 本地调试优先使用 `VLLM_MOCK=true`；
3. 接真实模型时再修改 `VLLM_BASE_URL` 和 `VLLM_MODEL`；
4. 先用示例数据跑通前端菜单、路由、SSE 流和邀请码流程，再接真实历史数据；
5. 上线前务必替换管理员默认密码和所有 mock 配置。
