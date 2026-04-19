# ChargeLLM 后端接口文档

本文档整理 `backend` 当前对外 HTTP API。后端基于 FastAPI，默认服务地址为 `http://127.0.0.1:8000`，所有业务接口统一带 `/api` 前缀。

## 在线文档

- Swagger UI: `GET /docs`
- OpenAPI JSON: `GET /openapi.json`
- ReDoc: `GET /redoc`

## 认证约定

- 管理员接口使用 `Authorization: Bearer <admin_access_token>`。
- 普通试用接口使用邀请码换取 `session_token`，随后统一通过 `Authorization: Bearer <session_token>` 传入。
- 禁止把 token 放在 URL query 中，避免浏览器历史、代理日志、网关日志泄露访问凭证。
- 前端把管理员 token 和邀请码 session token 存在 `sessionStorage`，关闭标签页后失效。

## 模型访问配置

`/api/chat/stream` 默认读取后端运行环境里的 vLLM/OpenAI-compatible 配置：

- `VLLM_MOCK`：`false` 时调用真实模型；`true` 时只使用本地规则模拟输出。
- `VLLM_BASE_URL`：模型服务根地址，后端会请求 `{VLLM_BASE_URL}/chat/completions`。
- `VLLM_MODEL`：传给模型服务的模型名。
- `VLLM_API_KEY`：可选访问密钥。配置后后端会发送 `Authorization: Bearer <VLLM_API_KEY>`。

真实模型请求体使用 OpenAI Chat Completions 兼容格式，包含系统提示词、用户问题和当前数据集的充电时序数据。模型被要求返回可解析 JSON，后端再转换为前端诊断卡片使用的结构化结果。

## 健康检查

### GET `/health`

返回服务状态，不带 `/api` 前缀。

响应：

```json
{
  "status": "ok",
  "service": "ChargeLLM Backend"
}
```

### GET `/api/health`

同 `/health`，用于前端或网关走统一 `/api` 前缀时探活。

## Auth

### POST `/api/auth/admin/login`

管理员登录。

请求：

```json
{
  "username": "admin",
  "password": "ChangeMe123!"
}
```

响应：

```json
{
  "access_token": "admin_xxx",
  "token_type": "bearer",
  "admin_username": "admin"
}
```

常见错误：

- `401 admin_login_failed`: 用户名或密码错误。

### POST `/api/auth/invite/start`

普通用户输入邀请码后启动临时试用会话。

请求：

```json
{
  "invite_code": "PUBLIC-BETA-001"
}
```

响应：

```json
{
  "invite_code": "PUBLIC-BETA-001",
  "session_token": "demo_xxx",
  "demo_user_id": 1,
  "quota_total": 10,
  "quota_used": 0,
  "quota_remaining": 10,
  "expires_at": null
}
```

常见错误：

- `404 invite_not_found`: 邀请码不存在。
- `400 invite_inactive`: 邀请码已停用。
- `400 invite_expired`: 邀请码已过期。
- `400 invite_quota_exhausted`: 邀请码总次数已用完。

### POST `/api/auth/sms/send`

发送 mock 短信验证码。

请求：

```json
{
  "phone": "13800000000"
}
```

响应：

```json
{
  "phone_masked": "138****0000",
  "status": "mock_sent",
  "mock_code": "123456"
}
```

### POST `/api/auth/sms/login`

手机号 + mock 验证码登录，用于查询真实历史充电记录。

请求：

```json
{
  "phone": "13800000000",
  "code": "123456"
}
```

响应：

```json
{
  "access_token": "phone_xxx",
  "token_type": "bearer",
  "phone_masked": "138****0000",
  "status": "mock_authenticated"
}
```

常见错误：

- `401 sms_code_invalid`: 验证码错误。

## Admin

以下接口均需要管理员 Bearer token。

### GET `/api/admin/me`

读取当前管理员状态。

响应：

```json
{
  "username": "admin",
  "status": "ok"
}
```

### GET `/api/admin/invites`

列出邀请码。

响应：

```json
[
  {
    "id": 1,
    "code": "PUBLIC-BETA-001",
    "name": "公测体验码",
    "max_uses": 20,
    "used_uses": 3,
    "per_user_quota": 10,
    "expires_at": null,
    "is_active": true
  }
]
```

### POST `/api/admin/invites`

创建邀请码。

请求：

```json
{
  "name": "政府监管试用",
  "code": "GOV-TRIAL-001",
  "max_uses": 50,
  "per_user_quota": 5,
  "expires_at": null
}
```

说明：

- `code` 可不传，后端自动生成。
- `max_uses` 和 `per_user_quota` 不传时使用默认配置。

响应：`InviteCodeRead`，结构同列表项。

### PATCH `/api/admin/invites/{invite_id}`

修改邀请码。

请求：

```json
{
  "name": "政府监管试用",
  "max_uses": 80,
  "per_user_quota": 8,
  "expires_at": null,
  "is_active": true
}
```

响应：`InviteCodeRead`。

常见错误：

- `404 invite_not_found`: 邀请码不存在。

### DELETE `/api/admin/invites/{invite_id}`

删除邀请码。

响应：

```json
{
  "id": 1,
  "code": "PUBLIC-BETA-001",
  "status": "deleted"
}
```

常见错误：

- `404 invite_not_found`: 邀请码不存在。

### GET `/api/admin/datasets`

列出后台维护的专业演示数据、用户导入数据和预留平台抽取数据。响应为 `BatteryExampleRead[]`。

### POST `/api/admin/datasets`

新增专业演示数据。`content` 支持 JSON 或 CSV，字段固定为时间、电压、电流、功率序列。

```json
{
  "title": "政府抽检高风险样本",
  "problem_type": "异常衰减",
  "capacity_range": "60-80%",
  "description": "来自抽检数据的脱敏演示样本",
  "sort_order": 1,
  "is_active": true,
  "file_name": "case.json",
  "content": "{\"time_offset_min\":[0,10],\"voltage_series\":[46.1,47.0],\"current_series\":[10,9.6],\"power_series\":[461,451]}"
}
```

响应：`BatteryExampleRead`。

### PATCH `/api/admin/datasets/{dataset_id}`

修改演示数据标题、类型、说明、排序、启停状态，或重新上传 `content`。

### DELETE `/api/admin/datasets/{dataset_id}`

删除演示数据。

```json
{
  "id": 1,
  "status": "deleted"
}
```

### POST `/api/admin/datasets/mysql-import`

从已有物联网数据接收平台按手机号和时间范围抽取数据。当前只保留稳定接口边界，SQL 查询逻辑后续填充。

```json
{
  "phone": "13800000000",
  "start_time": "2026-04-18T00:00:00",
  "end_time": "2026-04-18T23:59:59",
  "title": "平台抽取样本"
}
```

当前未配置 SQL 时响应：

```json
{
  "detail": "external_mysql_query_not_configured"
}
```

## Charge

### GET `/api/charge/examples`

列出内置示例电池数据。

响应：

```json
{
  "items": [
    {
      "id": 1,
      "sample_key": "aging_001",
      "title": "老化趋势样本",
      "problem_type": "aging",
      "capacity_range": "130-180Ah",
      "description": "示例描述",
      "sort_order": 1,
      "series": {
        "time_offset_min": [0, 5, 10],
        "power_series": [1.2, 1.1, 0.9],
        "current_series": [8.1, 7.8, 7.1],
        "voltage_series": [52.1, 52.4, 52.7]
      }
    }
  ]
}
```

### GET `/api/charge/examples/{sample_key}`

读取单个示例电池数据。

常见错误：

- `404 example_not_found`: 示例不存在。

### POST `/api/charge/history/query`

手机号 + 短信验证码查询历史充电记录。当前为 mock 返回。

请求：

```json
{
  "phone": "13800000000",
  "sms_code": "123456"
}
```

响应：

```json
{
  "status": "mock",
  "phone_masked": "138****0000",
  "records": []
}
```

## Datasets

以下接口面向普通体验用户，需要先通过邀请码换取 `session_token`，并在请求头中携带：

```http
Authorization: Bearer demo_xxx
```

### GET `/api/datasets`

列出当前用户可用于诊断的数据源，包括后台启用的专业案例库、平台抽取数据，以及当前用户自己上传的数据。

```json
{
  "items": [
    {
      "id": 1,
      "sample_key": "demo_case-abc",
      "title": "政府抽检高风险样本",
      "problem_type": "异常衰减",
      "capacity_range": "60-80%",
      "description": "来自抽检数据的脱敏演示样本",
      "source": "demo_case",
      "is_active": true,
      "sort_order": 1,
      "series": {
        "time_offset_min": [0, 10],
        "voltage_series": [46.1, 47.0],
        "current_series": [10, 9.6],
        "power_series": [461, 451]
      }
    }
  ]
}
```

### POST `/api/datasets/upload`

客户侧自主导入 CSV 或 JSON 数据，上传成功后可立即作为聊天上下文使用。

```json
{
  "name": "field.csv",
  "file_name": "field.csv",
  "content": "time_offset_min,voltage,current,power\n0,47.8,9.2,440\n5,48.4,8.8,426"
}
```

响应：`BatteryExampleRead`，其中 `source` 为 `user_upload`。

### DELETE `/api/datasets/{dataset_id}`

删除当前用户自己上传的数据。专业案例库数据不能由普通用户删除。

## Chat

### POST `/api/chat/completions`

推荐使用的对话接口。请求体和流式响应兼容 OpenAI Chat Completions，支持多轮 `messages`、多模态 `content` parts、`tools`、`tool_choice`、流式输出和客户端提前终止。

同时提供 `/api/v1/chat/completions` 别名，便于按 OpenAI-compatible base URL 方式集成。

请求头：

```http
Authorization: Bearer demo_xxx
```

请求：

```json
{
  "model": "chargellm-diagnosis",
  "stream": true,
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "请判断这块电池是否存在老化趋势。" },
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
      ]
    },
    { "role": "assistant", "content": "上一轮判断末段功率下降，需要继续观察。" },
    { "role": "user", "content": "继续结合电流变化判断。" }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_charge_process",
        "description": "读取充电过程明细",
        "parameters": { "type": "object", "properties": { "process_id": { "type": "string" } } }
      }
    }
  ],
  "tool_choice": "auto",
  "metadata": {
    "dataset_id": 1,
    "example_key": "aging_001"
  }
}
```

说明：

- `messages` 是唯一的多轮上下文来源，前端每次请求应携带当前会话历史。
- `metadata.dataset_id` 用于让后端把当前电压、电流、功率、时间序列作为系统上下文注入模型请求，不会透传给上游模型。
- `tools` 和 `tool_choice` 会按 Chat Completions 格式透传给兼容模型服务。
- `stream=false` 时返回普通 `chat.completion` JSON；`stream=true` 时返回 `text/event-stream`。
- 客户端提前终止时直接 abort/断开 HTTP 请求，后端会停止继续向前端推送。

流式响应：

```text
data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"模型判断..."},"finish_reason":null}]}

data: [DONE]
```

### POST `/api/chat/stream`

旧版页面接口。保留用于内部回归测试，新页面不再使用。以 SSE 方式返回诊断过程、模型回答文本和最终结构化结论。`VLLM_MOCK=false` 时，示例数据会作为真实模型输入，而不是直接按 demo 标签生成结果。

请求头：

```http
Authorization: Bearer demo_xxx
```

请求：

```json
{
  "question": "这块电池是否存在老化趋势？",
  "dataset_id": 1,
  "example_key": "aging_001"
}
```

说明：

- 新页面优先传 `dataset_id`，后端会读取对应专业案例或用户上传数据作为模型上下文。
- `example_key` 保留给旧的内置样本接口调用；新实现不再依赖它。

响应类型：`text/event-stream`。

事件示例：

```text
event: status
data: {"message":"已读取充电历史数据"}

event: status
data: {"message":"正在调用多模态诊断大模型"}

event: token
data: {"text":"模型判断该电池存在明显老化趋势，建议重点复核末段恒压时长。"}

event: final
data: {"label":"电池老化","capacity_range":"60-80%","confidence":0.87,"reason":"...","key_processes":["aging_001-p2"]}

event: done
data: {"status":"ok"}
```

常见错误：

- `401 demo_session_invalid`: session token 无效或已失效。
- SSE `error` / `quota_exceeded`: 单用户试用次数已用完。
- SSE `error` / `vllm_request_failed`: 真实模型服务不可达、超时或返回内容无法解析。
- SSE `error`: 内容安全检查未通过。

## 运行与排障

本地启动：

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

管理员默认账号：

```text
username: admin
password: ChangeMe123!
```

如果登录出现 500，优先检查：

- 后端是否是最新代码并已重启。
- `DATABASE_URL` 指向的 SQLite 是否为当前版本新建库。当前版本不迁移旧表结构；旧 demo 数据可以删除后重建。
- 前端 `VITE_API_BASE_URL` 是否指向正确后端；开发态默认通过 Vite 代理 `/api` 到 `127.0.0.1:8000`。
