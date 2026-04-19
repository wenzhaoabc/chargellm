# ChargeLLM 前端平台实现路径

## 目标

建设一个轻量但具备基本工程化部署能力的 demo 平台，用于客户展示 ChargeLLM 的电池充电数据分析能力。

平台核心链路：

```text
邀请码进入示例体验
-> 选择示例电池
-> 前端展示功率/电流曲线
-> 用户提问
-> 后端合规检查、拼接上下文、调用 vLLM
-> SSE 流式返回分析过程和模型结果
-> 前端展示诊断结论
```

真实历史充电记录体验是可选增强链路：

```text
用户点击“我的充电记录”
-> 手机号 + 短信验证码登录
-> 后端按登录手机号查询历史充电记录
-> 用户选择真实电池记录
-> 进入同一套分析流程
```

本阶段不做复杂 SaaS，不做高并发，不做复杂权限体系。目标是稳定、可部署、可演示、方便后续扩展。

## 技术栈

### 前端

```text
React
TypeScript
Vite
ECharts
Fetch/EventSource
```

前端重点：

- 页面美观；
- 操作路径清晰；
- 曲线展示直观；
- Chat 体验接近 ChatGPT/Gemini；
- 支持 SSE 流式输出。

### 后端

```text
FastAPI
SQLAlchemy 2.x
Alembic
SQLite
Pydantic v2
httpx
```

后端重点：

- 邀请码体验态；
- 管理员认证；
- 手机号验证码认证，仅用于查询真实历史充电记录；
- 邀请码和次数限制；
- 阿里云内容安全审核；
- 示例数据和真实数据接口预留；
- vLLM OpenAI-compatible API 调用；
- SSE 流式响应；
- 诊断记录落库。

### 模型服务

模型由 vLLM 单独部署，FastAPI 只调用模型接口。

```text
vLLM OpenAI-compatible server
POST /v1/chat/completions
stream = true
```

## 产品功能范围

### 普通用户

普通用户功能：

- 输入邀请码后直接体验示例数据；
- 查看剩余体验次数；
- 选择平台内置示例电池；
- 查看充电曲线；
- 向模型提问；
- 接收流式分析结果；
- 查看历史诊断记录。

查询真实历史充电记录时才需要：

```text
手机号 + 短信验证码登录
-> 按登录手机号查询本人历史充电记录
-> 选择真实记录进入分析
```

第一版短信验证码可以先使用 mock，开发环境固定验证码为 `123456`。

### 管理员

管理员功能：

- 管理员账号密码登录；
- 创建邀请码；
- 查看邀请码使用情况；
- 禁用邀请码；
- 查看用户列表；
- 查看用户剩余次数；
- 查看最近诊断记录。

管理员功能只做基本后台，不做复杂数据看板。

## 角色与权限

角色：

```text
admin
user
```

权限规则：

- `admin` 可以访问 `/admin` 页面和 `/api/admin/*` 接口；
- 邀请码体验用户只能访问示例数据；
- 手机号登录用户可以访问本人历史充电记录；
- 发起模型诊断必须有有效邀请码和剩余额度；
- 每次成功诊断扣减一次额度；
- 阿里云内容安全审核拒绝、模型输入被拒绝、模型调用失败，不扣次数。

## 页面设计

## 前端菜单与路由

前端需要有清晰菜单和路由，避免 demo 看起来像单页脚本。

第一版路由：

```text
/                 跳转到 /demo
/demo             示例数据体验主页面
/records          我的历史充电记录，需要手机号验证码登录
/history          我的诊断历史
/admin/login      管理员登录
/admin            管理员后台首页
/admin/invites    邀请码管理
/admin/users      用户/体验记录
/admin/runs       诊断记录
```

普通用户顶部菜单：

```text
示例体验
我的充电记录
诊断历史
剩余次数
```

管理员顶部菜单：

```text
概览
邀请码
用户
诊断记录
退出
```

### 普通用户页面

主页面采用三块区域：

```text
顶部栏：
  ChargeLLM / 当前用户 / 剩余次数 / 退出登录

左侧：
  示例电池
  我的充电记录
  推荐问题

中间：
  当前电池信息
  功率/电流曲线
  容量范围
  关键充电过程

右侧：
  Chat 对话
  流式输出
  诊断结果卡片
```

推荐问题：

```text
这块电池是否存在老化趋势？
这几次充电过程里有没有异常？
这块电池大概处于什么容量范围？
哪些充电过程最值得关注？
这块电池是否适合继续使用？
```

第一版必须提供几个示例电池：

```text
正常电池示例
老化电池示例
故障电池示例
非标电池示例
```

### 管理员页面

管理员页面保持简单：

```text
/admin/login
/admin
```

后台模块：

- 邀请码列表；
- 创建邀请码；
- 用户列表；
- 诊断记录列表。

不做复杂报表。

## 前端目录结构

建议：

```text
frontend/
  package.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    router.tsx
    api/
      client.ts
      auth.ts
      admin.ts
      charge.ts
      chat.ts
    components/
      AppLayout.tsx
      LoginPanel.tsx
      InviteGate.tsx
      BatterySelector.tsx
      ChargeChart.tsx
      ChatPanel.tsx
      DiagnosisCard.tsx
      ToolTimeline.tsx
      AdminLayout.tsx
    pages/
      DemoPage.tsx
      AdminLoginPage.tsx
      AdminPage.tsx
    types/
      auth.ts
      charge.ts
      chat.ts
```

## 后端目录结构

建议：

```text
backend/
  pyproject.toml
  alembic.ini
  app/
    main.py
    core/
      config.py
      security.py
    db/
      base.py
      session.py
    models/
      user.py
      invite.py
      chat.py
    schemas/
      auth.py
      invite.py
      charge.py
      chat.py
    api/
      auth.py
      admin.py
      charge.py
      chat.py
    services/
      sms_service.py
      invite_service.py
      moderation_service.py
      charge_data_service.py
      prompt_service.py
      model_client.py
      chat_service.py
    scripts/
      bootstrap_admin.py
  alembic/
    versions/
```

如果后续希望和当前 `src/chargellm` 代码完全合并，可以再把后端包迁移进主项目。第一版建议保持 `backend/` 独立，便于部署。

## 数据库设计

第一版使用 SQLite，但必须通过 SQLAlchemy ORM 和 Alembic 管理，方便后续迁移 PostgreSQL。

### users

```text
id
phone nullable unique
username nullable unique
password_hash nullable
role: admin/user/guest
is_active
invite_code_id nullable
usage_quota_total
usage_quota_used
created_at
last_login_at
```

说明：

- 管理员使用 `username + password_hash`；
- 邀请码体验用户可以没有手机号，角色可记为 `guest`；
- 手机号用户使用 `phone`；
- 普通用户可以没有密码；
- `usage_quota_total - usage_quota_used` 即剩余次数。

### invite_codes

```text
id
code unique
name
max_users
used_users
per_user_quota
expires_at nullable
is_active
created_by
created_at
```

### invite_redemptions

```text
id
invite_code_id
user_id
phone
redeemed_at
```

### sms_codes

```text
id
phone
code_hash
expires_at
consumed_at nullable
created_at
```

开发阶段可以不落库短信验证码，使用内存或固定验证码；但表结构保留。

### chat_sessions

```text
id
user_id
battery_id nullable
title
created_at
updated_at
```

### chat_messages

```text
id
session_id
role: user/assistant/tool/system
content
metadata_json
created_at
```

### diagnosis_runs

```text
id
user_id
session_id nullable
battery_id
question
request_json
raw_model_output
parsed_result_json
status: running/success/failed/blocked
quota_charged
created_at
finished_at nullable
```

扣次数规则：

```text
只有 status=success 且 quota_charged=false 时，才扣一次。
阿里云内容安全审核拒绝、模型调用失败、模型输出不可用，不扣次数。
```

## 环境变量

后端配置：

```env
DATABASE_URL=sqlite:///./data/chargellm_demo.db
JWT_SECRET=change-me
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ChangeMe123!
SMS_MOCK_CODE=123456
VLLM_BASE_URL=http://127.0.0.1:8001/v1
VLLM_MODEL=Qwen3-VL
DEMO_DATA_PATH=../dataset/sft.json
ALIYUN_ACCESS_KEY_ID=...
ALIYUN_ACCESS_KEY_SECRET=...
ALIYUN_CONTENT_SAFETY_ENDPOINT=...
ALIYUN_GUARDRAIL_INPUT_SERVICE=...
ALIYUN_GUARDRAIL_OUTPUT_SERVICE=response_security_check_hp
```

前端配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API 设计

### 邀请码体验

邀请码进入 demo：

```text
POST /api/auth/invite/start
```

请求：

```json
{
  "code": "CHARGE-ABCD-1234"
}
```

返回：

```json
{
  "access_token": "...",
  "visitor": {
    "id": 1,
    "role": "guest",
    "quota_total": 10,
    "quota_used": 0,
    "quota_remaining": 10
  }
}
```

说明：

- 只体验示例数据时，不需要手机号；
- 体验 token 和邀请码绑定；
- 每次成功诊断扣减邀请码分配的体验次数。

### 手机号认证

手机号认证只用于查询用户本人真实历史充电记录。

发送验证码：

```text
POST /api/auth/sms/send
```

请求：

```json
{
  "phone": "13800000000"
}
```

验证码登录：

```text
POST /api/auth/sms/login
```

请求：

```json
{
  "phone": "13800000000",
  "code": "123456"
}
```

返回：

```json
{
  "access_token": "...",
  "user": {
    "id": 2,
    "phone": "138****0000",
    "role": "user"
  }
}
```

手机号用户如需继续调用模型分析真实记录，仍需要有效邀请码额度。第一版可复用已兑换的邀请码，也可以在登录后提示输入邀请码绑定。

绑定邀请码：

```text
POST /api/auth/invite/bind
```

```json
{
  "code": "CHARGE-ABCD-1234"
}
```

### 管理员

管理员登录：

```text
POST /api/admin/login
```

请求：

```json
{
  "username": "admin",
  "password": "ChangeMe123!"
}
```

创建邀请码：

```text
POST /api/admin/invites
```

请求：

```json
{
  "name": "第一批公测",
  "max_users": 20,
  "per_user_quota": 10,
  "expires_at": "2026-05-01T00:00:00"
}
```

其他管理接口：

```text
GET   /api/admin/invites
PATCH /api/admin/invites/{invite_id}
GET   /api/admin/users
GET   /api/admin/diagnosis-runs
```

### 示例和充电记录

示例电池：

```text
GET /api/examples/batteries
GET /api/examples/batteries/{battery_id}
```

我的充电记录：

```text
GET /api/charge-records
GET /api/charge-records/{battery_id}
```

真实手机号查询接口预留：

```text
POST /api/charge-records/sync-by-phone
```

第一版实现为占位：

```text
仅手机号验证码登录后的用户可调用。
根据当前登录用户手机号调用 ChargeDataProvider。
ChargeDataProvider 先返回空列表或 mock 数据。
后续替换为真实 SQL 查询。
```

后端接口不要信任前端传入手机号，必须从登录态读取手机号。

### Chat SSE

发起流式诊断：

```text
POST /api/chat/stream
```

请求：

```json
{
  "battery_id": "battery_001",
  "question": "这块电池是否存在老化趋势？",
  "source": "example"
}
```

SSE 事件：

```text
event: status
data: {"message":"正在读取充电记录"}

event: tool_start
data: {"name":"load_charge_record"}

event: tool_result
data: {"name":"load_charge_record","status":"success"}

event: status
data: {"message":"正在调用诊断模型"}

event: token
data: {"text":"根据功率和电流曲线..."}

event: final
data: {"label":"电池老化","capacity_range":"80-90%","confidence":0.82,"key_processes":["p006"],"reason":"..."}

event: done
data: {}
```

错误：

```text
event: error
data: {"error":"quota_exceeded","message":"当前体验次数已用完，请联系管理员。"}
```

## 后端推理流程

```text
收到 /api/chat/stream
-> 验证 JWT
-> 检查邀请码体验态或手机号用户的邀请码绑定状态
-> 检查剩余次数
-> 调用阿里云内容安全检查用户输入
-> 加载电池数据
-> 生成时序摘要和模型上下文
-> 调用阿里云内容安全检查模型输入
-> 创建 diagnosis_run(status=running)
-> 调用 vLLM streaming 接口
-> 对模型流式输出做切片审核
-> 审核通过的切片通过 SSE 推送 token
-> 收集完整模型输出
-> 解析诊断 JSON
-> 调用阿里云内容安全检查最终输出
-> 保存 diagnosis_run 和 chat_messages
-> 推理成功后扣次数
-> SSE 推送 final 和 done
```

## 阿里云内容安全审核

第一版使用阿里云内容安全 / AI 安全护栏服务，不再维护本地敏感词词表。

相关文档：

- 内容安全文档入口：<https://help.aliyun.com/zh/document_detail/2573826.html>
- API 接入重点文档：<https://help.aliyun.com/zh/document_detail/2875413.html>
- 大模型生成内容流式审核方案：<https://help.aliyun.com/zh/document_detail/2980054.html>

阿里云流式审核文档建议在大模型流式生成过程中，按字符数切片或滑动窗口切片进行审核；检测无风险后再透出给用户。如果发现风险，应停止后续输出，并替换为合规代答。

服务：

```text
services/content_safety_service.py
```

接口：

```python
check_user_input(text) -> SafetyResult
check_model_prompt(text) -> SafetyResult
check_model_output(text) -> SafetyResult
check_stream_chunk(chat_id, chunk, done=False) -> SafetyResult
```

命中后返回统一拒答：

```json
{
  "type": "refusal",
  "message": "该问题暂不支持分析。你可以询问电池健康、充电异常、容量范围或历史充电趋势。"
}
```

流式输出审核策略：

```text
1. vLLM token 先进入后端缓冲区，不直接透出给前端；
2. 按累计字符数切片，例如每 80-120 个中文字符审核一次；
3. 调用阿里云流式审核服务；
4. 审核通过后再向前端发送 token/chunk；
5. 如果审核失败，立即停止 vLLM 请求或停止继续读取；
6. SSE 返回 refusal/error 事件；
7. diagnosis_run.status 记录为 blocked；
8. 不扣用户次数。
```

流式审核需要维护同一轮对话的 `chatId` 和 `done` 标识，用于关联多切片审核。

配置项：

```text
ALIYUN_ACCESS_KEY_ID
ALIYUN_ACCESS_KEY_SECRET
ALIYUN_CONTENT_SAFETY_ENDPOINT
ALIYUN_GUARDRAIL_INPUT_SERVICE
ALIYUN_GUARDRAIL_OUTPUT_SERVICE
```

## 充电数据服务

定义统一接口：

```python
class ChargeDataProvider:
    async def list_example_batteries(self) -> list[BatterySummary]:
        ...

    async def get_example_battery(self, battery_id: str) -> BatterySample:
        ...

    async def list_user_batteries(self, phone: str) -> list[BatterySummary]:
        ...

    async def get_user_battery(self, phone: str, battery_id: str) -> BatterySample:
        ...
```

第一版实现：

```text
JsonDemoChargeDataProvider
```

后续替换：

```text
SqlChargeDataProvider
```

替换真实 SQL 时，前端和 chat 流程不需要改。

## vLLM Client

服务：

```text
services/model_client.py
```

职责：

- 读取 `VLLM_BASE_URL`；
- 调用 OpenAI-compatible `/chat/completions`；
- 支持 stream；
- 把模型 token 转为后端统一事件。

第一版如果模型接口还没准备好，实现 mock 模式：

```env
VLLM_MOCK=true
```

mock 返回固定诊断，保证前后端先联调。

## 部署方式

第一版使用 Docker Compose。

服务：

```text
frontend
backend
vllm
```

如果 vLLM 已经单独部署，compose 中只保留：

```text
frontend
backend
```

建议目录：

```text
deploy/
  docker-compose.yml
  backend.Dockerfile
  frontend.Dockerfile
  nginx.conf
```

本地启动：

```bash
docker compose -f deploy/docker-compose.yml up --build
```

后端启动时：

```text
alembic upgrade head
bootstrap admin
start uvicorn
```

## 开发实施顺序

### Phase 1: 平台骨架

目标：前后端能启动。

任务：

1. 创建 `backend/` FastAPI 项目；
2. 创建 `frontend/` React + Vite 项目；
3. 配置 Docker Compose；
4. 后端提供 `/api/health`；
5. 前端调用 `/api/health` 显示服务状态。

验收：

```text
docker compose up 后，浏览器能打开前端页面，并显示后端健康状态。
```

### Phase 2: 用户、管理员、邀请码

目标：具备公测访问控制。

任务：

1. SQLAlchemy models；
2. Alembic migration；
3. 管理员 bootstrap；
4. 管理员登录；
5. 邀请码创建和列表；
6. 邀请码启动体验；
7. 体验 token；
8. 额度检查；
9. 手机号验证码 mock 登录接口预留给真实数据查询。

验收：

```text
管理员可以创建邀请码。
用户输入邀请码即可进入示例体验。
用户能看到剩余次数。
手机号验证码登录可进入“我的充电记录”页面。
```

### Phase 3: 示例数据和曲线展示

目标：用户能看到可理解的电池数据。

任务：

1. 示例电池列表接口；
2. 电池详情接口；
3. 前端电池选择；
4. ECharts 绘制功率/电流曲线；
5. 推荐问题按钮。

验收：

```text
用户点击示例电池后，前端显示功率/电流曲线和推荐问题。
```

### Phase 4: Chat SSE 和 mock 模型

目标：先跑通流式体验。

任务：

1. `/api/chat/stream`；
2. SSE 事件封装；
3. 前端 ChatPanel；
4. mock model client；
5. 诊断结果卡片；
6. 诊断记录落库；
7. 成功后扣次数。

验收：

```text
用户提问后，前端能看到状态事件、流式文本和最终诊断卡片。
成功一次后，剩余次数减少 1。
```

### Phase 5: 阿里云内容安全审核

目标：具备基础合规防护。

任务：

1. 封装阿里云内容安全 client；
2. 用户输入审核；
3. 模型 prompt 审核；
4. 模型最终输出审核；
5. 模型流式输出切片审核；
6. 前端拒答展示。

验收：

```text
阿里云审核拒绝时，后端拒绝响应或中断流式输出，不扣次数。
```

### Phase 6: 接入 vLLM

目标：替换 mock 模型。

任务：

1. 实现 vLLM streaming client；
2. 配置 `VLLM_BASE_URL` 和 `VLLM_MODEL`；
3. 拼接电池上下文；
4. 解析模型最终输出；
5. 保存 raw output 和 parsed output。

验收：

```text
前端通过 SSE 看到真实模型输出。
最终诊断结果可解析并展示。
```

### Phase 7: 真实充电记录接口预留

目标：后续可以接入用户真实数据。

任务：

1. 定义 `ChargeDataProvider`；
2. mock 实现；
3. 预留 SQL provider 文件；
4. 后端接口从登录手机号读取用户身份；
5. 前端增加“我的充电记录”入口。

验收：

```text
接口路径稳定。
后续只需要补 SQL 查询逻辑，不需要改前端主流程。
```

## 推荐开发路径

第一版不要同时推进所有功能。推荐按“能演示的垂直闭环”推进：

```text
平台骨架
-> 邀请码进入示例体验
-> 示例电池曲线展示
-> Chat SSE mock
-> 阿里云内容安全
-> vLLM 接入
-> 管理员后台补齐
-> 手机号真实数据接口预留
```

这样每一步都有可运行结果，避免最后才发现前后端或模型链路无法联通。

### 第一条垂直闭环

第一条闭环只做示例数据，不接真实手机号数据：

```text
邀请码
-> 示例电池
-> 曲线图
-> 推荐问题
-> mock SSE
-> 诊断卡片
-> 扣次数
```

验收后再接：

```text
阿里云审核
-> vLLM 真实流式输出
-> 管理员诊断记录
-> 手机号历史记录入口
```

### 为什么这样排

- 邀请码和示例数据是客户 demo 的入口，必须最先稳定；
- SSE 和诊断卡片决定产品观感，必须早验证；
- vLLM 接入可能受模型部署影响，先用 mock 解耦前后端；
- 阿里云审核涉及外部服务，单独封装后可用 mock 替代；
- 手机号真实数据接口暂时只保留稳定边界，等 SQL 细节确定后再接。

## 并行开发方式

并行开发按模块边界拆分。每个 agent 或开发者只修改自己负责的目录，减少冲突。

### Agent A: 后端基础设施

负责范围：

```text
backend/app/main.py
backend/app/core/
backend/app/db/
backend/app/models/
backend/alembic/
backend/pyproject.toml
deploy/backend.Dockerfile
deploy/docker-compose.yml
```

交付：

- FastAPI 应用启动；
- `/api/health`；
- SQLAlchemy session；
- Alembic 初始化；
- users / invite_codes / diagnosis_runs 基础表；
- 管理员 bootstrap；
- Docker Compose 后端服务。

不负责：

- 前端页面；
- vLLM 调用；
- 具体业务 prompt。

验收：

```text
pytest backend/tests/test_health.py
pytest backend/tests/test_db_models.py
docker compose -f deploy/docker-compose.yml up backend
```

### Agent B: 认证、邀请码和额度

负责范围：

```text
backend/app/api/auth.py
backend/app/api/admin.py
backend/app/services/invite_service.py
backend/app/services/sms_service.py
backend/app/core/security.py
backend/tests/test_auth.py
backend/tests/test_invites.py
```

交付：

- 管理员账号密码登录；
- 邀请码创建、禁用、列表；
- `POST /api/auth/invite/start`；
- 体验 token；
- 额度检查；
- 手机号验证码 mock 登录；
- 手机号登录只用于真实记录入口。

不负责：

- 前端 UI；
- 模型推理；
- 真实短信供应商。

验收：

```text
管理员能创建邀请码。
用户只输入邀请码即可进入 demo。
成功诊断后额度扣 1。
额度不足时 chat 接口拒绝。
```

### Agent C: 示例数据和充电数据服务

负责范围：

```text
backend/app/api/charge.py
backend/app/schemas/charge.py
backend/app/services/charge_data_service.py
backend/tests/test_charge_data_service.py
```

交付：

- `GET /api/examples/batteries`；
- `GET /api/examples/batteries/{battery_id}`；
- `GET /api/charge-records`；
- `POST /api/charge-records/sync-by-phone` 占位；
- `ChargeDataProvider` 抽象；
- `JsonDemoChargeDataProvider`；
- `SqlChargeDataProvider` 空实现或接口占位。

不负责：

- 前端图表；
- 真实 SQL 查询；
- 模型 prompt。

验收：

```text
示例电池列表可返回。
示例电池详情包含 power_series/current_series/time_offset。
手机号未登录不能访问真实记录接口。
```

### Agent D: Chat SSE 和模型编排

负责范围：

```text
backend/app/api/chat.py
backend/app/schemas/chat.py
backend/app/services/chat_service.py
backend/app/services/prompt_service.py
backend/app/services/model_client.py
backend/tests/test_chat_stream.py
backend/tests/test_model_client.py
```

交付：

- `/api/chat/stream`；
- SSE 事件格式；
- mock model client；
- vLLM streaming client；
- prompt 拼接；
- 模型输出 JSON 解析；
- diagnosis_runs 落库；
- 成功后扣次数。

依赖：

- Agent B 的额度检查；
- Agent C 的电池数据服务；
- Agent E 的内容安全服务。

验收：

```text
mock 模式下前端能收到 status/token/final/done。
模型输出不可解析时返回兜底结果。
成功时扣次数，失败时不扣。
```

### Agent E: 阿里云内容安全

负责范围：

```text
backend/app/services/content_safety_service.py
backend/app/schemas/safety.py
backend/tests/test_content_safety_service.py
```

交付：

- 阿里云 client 封装；
- 用户输入审核；
- prompt 审核；
- 最终输出审核；
- 流式输出切片审核；
- mock safety client；
- 审核失败统一拒答。

不负责：

- vLLM 具体调用；
- 前端页面。

验收：

```text
mock allow 时 chat 正常继续。
mock block 时 chat 返回 refusal/error。
block 不扣次数。
流式输出命中 block 时中断后续输出。
```

### Agent F: 前端基础、路由和布局

负责范围：

```text
frontend/src/main.tsx
frontend/src/App.tsx
frontend/src/router.tsx
frontend/src/components/AppLayout.tsx
frontend/src/pages/DemoPage.tsx
frontend/src/pages/AdminLoginPage.tsx
frontend/src/pages/AdminPage.tsx
frontend/src/pages/RecordsPage.tsx
frontend/src/pages/HistoryPage.tsx
frontend/src/api/client.ts
```

交付：

- React Router；
- 顶部菜单；
- 普通用户 demo 布局；
- 管理员布局；
- API client；
- 基础错误提示和 loading 状态。

不负责：

- 具体 ECharts 曲线；
- Chat 组件细节；
- 管理员业务表格细节。

验收：

```text
/demo、/records、/history、/admin/login、/admin 可访问。
顶部菜单可跳转。
前端能显示 /api/health 状态。
```

### Agent G: 前端业务组件

负责范围：

```text
frontend/src/components/InviteGate.tsx
frontend/src/components/BatterySelector.tsx
frontend/src/components/ChargeChart.tsx
frontend/src/components/ChatPanel.tsx
frontend/src/components/DiagnosisCard.tsx
frontend/src/components/ToolTimeline.tsx
frontend/src/api/auth.ts
frontend/src/api/charge.ts
frontend/src/api/chat.ts
```

交付：

- 邀请码入口；
- 剩余次数展示；
- 示例电池选择；
- ECharts 功率/电流曲线；
- 推荐问题；
- SSE Chat；
- 诊断结果卡片。

依赖：

- Agent F 的布局和路由；
- Agent B/C/D 的 API。

验收：

```text
输入邀请码进入 demo。
选择示例电池后显示曲线。
点击推荐问题后开始 SSE。
最终结果渲染为诊断卡片。
```

### Agent H: 管理员前端

负责范围：

```text
frontend/src/api/admin.ts
frontend/src/pages/AdminPage.tsx
frontend/src/components/AdminLayout.tsx
frontend/src/components/InviteTable.tsx
frontend/src/components/UserTable.tsx
frontend/src/components/DiagnosisRunTable.tsx
```

交付：

- 管理员登录；
- 邀请码列表；
- 创建邀请码；
- 用户列表；
- 诊断记录列表。

依赖：

- Agent F 的管理员路由；
- Agent B 的管理员 API。

验收：

```text
管理员能登录。
管理员能创建邀请码。
管理员能看到邀请码和诊断记录。
```

## 并行依赖顺序

第一批并行：

```text
Agent A: 后端基础设施
Agent F: 前端基础、路由和布局
```

第二批并行：

```text
Agent B: 认证、邀请码和额度
Agent C: 示例数据和充电数据服务
Agent E: 阿里云内容安全 mock/client
Agent G: 前端业务组件骨架
```

第三批：

```text
Agent D: Chat SSE 和模型编排
Agent H: 管理员前端
```

第四批：

```text
联调 vLLM
联调阿里云真实审核
联调 Docker Compose
```

关键阻塞关系：

```text
Agent D 依赖 B/C/E 的最小接口。
Agent G 依赖 F 的路由骨架。
Agent H 依赖 F 的管理员路由和 B 的管理员 API。
真实 vLLM 接入不阻塞前端和 SSE，先用 mock。
真实阿里云审核不阻塞 chat，先用 mock safety client。
```

## 测试策略

测试目标是确保每一步都能独立验证，而不是只靠最终人工点页面。

### 后端单元测试

范围：

```text
backend/tests/test_auth.py
backend/tests/test_invites.py
backend/tests/test_charge_data_service.py
backend/tests/test_content_safety_service.py
backend/tests/test_model_client.py
backend/tests/test_chat_stream.py
```

重点用例：

- 管理员密码哈希校验；
- 邀请码过期、禁用、超额；
- 邀请码进入 demo 不需要手机号；
- 手机号验证码登录只用于真实记录；
- 额度不足时拒绝 chat；
- 审核拒绝不扣次数；
- mock SSE 输出事件顺序正确；
- 模型输出非法 JSON 时兜底。

运行：

```bash
cd backend
pytest
```

### 后端集成测试

使用 FastAPI `TestClient` 或 `httpx.AsyncClient`。

核心链路：

```text
创建管理员
-> 管理员登录
-> 创建邀请码
-> 邀请码 start
-> 获取示例电池
-> 调用 chat stream mock
-> 校验扣次数
-> 校验 diagnosis_run 落库
```

这条链路必须作为 CI 或本地 smoke test。

### SSE 测试

SSE 不只测接口状态码，要测事件顺序。

期望事件：

```text
status
tool_start
tool_result
status
token
final
done
```

异常事件：

```text
error
done
```

至少测试：

- 正常 mock 输出；
- 额度不足；
- 阿里云审核 mock block；
- 模型客户端异常；
- 模型输出非法 JSON。

### 前端测试

第一版不需要大规模组件测试，但需要基本冒烟：

```text
pnpm lint
pnpm build
```

建议补少量组件测试：

```text
InviteGate: 输入邀请码后调用接口
BatterySelector: 渲染示例列表
DiagnosisCard: 正确展示 label/capacity_range/confidence
ChatPanel: 能消费 SSE mock 事件
```

### 端到端手工验收

每次 milestone 完成后按以下脚本验收：

1. 启动 Docker Compose；
2. 打开前端；
3. 管理员登录；
4. 创建邀请码；
5. 普通入口输入邀请码；
6. 选择示例电池；
7. 查看功率/电流曲线；
8. 点击推荐问题；
9. 观察 SSE 流式输出；
10. 查看诊断卡片；
11. 确认剩余次数减少；
12. 管理员查看诊断记录。

### Mock 策略

为了并行开发，外部依赖必须可 mock：

```text
SMS_MOCK_CODE=123456
VLLM_MOCK=true
ALIYUN_SAFETY_MOCK=allow
```

建议 mock 模式：

```text
ALIYUN_SAFETY_MOCK=allow   全部放行
ALIYUN_SAFETY_MOCK=block   全部拒绝
ALIYUN_SAFETY_MOCK=keyword 命中特定词拒绝
```

vLLM mock 输出固定 JSON：

```json
{
  "label": "电池老化",
  "capacity_range": "80-90%",
  "confidence": 0.82,
  "key_processes": ["p001"],
  "reason": "多次充电过程显示容量和功率响应存在下降趋势。"
}
```

### 部署测试

Docker Compose 验收：

```bash
docker compose -f deploy/docker-compose.yml up --build
```

必须检查：

- frontend 容器启动；
- backend 容器启动；
- backend 自动执行 migration；
- 管理员账号可初始化；
- 前端能访问后端；
- SQLite 数据文件挂载到持久目录；
- 环境变量缺失时后端给出清晰错误。

## 最小交付标准

MVP 必须满足：

- 前端页面可访问；
- 前端具备菜单和路由；
- 管理员可登录；
- 管理员可创建邀请码；
- 普通用户输入邀请码即可体验示例数据；
- 邀请码用户有次数限制；
- 手机号验证码登录只用于查询真实历史充电记录；
- 用户可选择示例电池；
- 前端可展示功率/电流曲线；
- 用户可提问；
- 后端通过 SSE 返回状态、模型文本和最终结果；
- 阿里云内容安全审核拒绝时拒答或中断流；
- 诊断记录落库；
- Docker Compose 可启动。

## 暂不实现

第一版暂不做：

- 高并发；
- 支付；
- 复杂企业租户；
- 复杂管理员 BI 看板；
- 完整短信供应商接入；
- 完整 RBAC；
- 多模型路由；
- 文件上传；
- 精细审计系统；
- 复杂内容安全模型。

## 后续扩展点

后续可扩展：

- 接真实短信；
- 更细的阿里云审核策略和分类处置；
- SQLite 迁移 PostgreSQL；
- 接真实充电数据库；
- 增加 VLM 图片输入；
- 增加历史对话检索；
- 增加用户反馈；
- 增加管理员导出诊断记录；
- 增加模型效果统计。
