# ChargeLLM 平台架构与 API 参考

> 阅读对象：后端/前端开发者、想接入或扩展平台的工程师。
> 想要"怎么用"，看 [`usage.md`](./usage.md)。

## 1. 整体架构

```
┌─────────────────┐  SSE                 ┌──────────────────────────────────┐
│ Frontend         │ ─────────────────▶  │ FastAPI                            │
│ React + AntD X   │                     │   /api/chat/agent/stream           │
│ ECharts          │ ◀─── token / tool ──│   ├── Aliyun 内容安全 (TextModerationPlus)
└─────────────────┘     events           │   │   • query_security_check (输入)
        ▲                                │   │   • response_security_check (输出，异步窗口)
        │ /api/admin/*                   │   ├── Tool registry
        │ /api/charge/orders             │   │   • query_charging_records (IOT MySQL)
        │ /api/auth/*                    │   │   • highlight_charge_segment (display-only)
        │ /api/meta/*                    │   │   • compare_orders / web_search
┌─────────────────┐                      │   └── vLLM (OpenAI 兼容流式)
│ Admin UI         │                      └──────────────────────────────────┘
│ (同前端域名)     │                              │            │
└─────────────────┘                              ▼            ▼
                                          ┌──────────┐  ┌──────────┐
                                          │ SQLite   │  │ MySQL    │
                                          │ 应用元数据│  │ IOT 充电 │
                                          │ + 对话历史│  │ 数据(只读)│
                                          └──────────┘  └──────────┘
```

数据库分工：
- **SQLite**（应用自有）：`users`、`invite_codes`、`demo_sessions`、`chat_sessions`、`chat_messages`、`sms_codes`、`system_prompts`、`welcome_messages`、`battery_examples`
- **MySQL**（外部 IOT 平台、只读）：`smc_device_order_push` + `smc_device_order_push_finish` + `smc_device_supplier`，按手机号 + 时间窗查询

## 2. 鉴权模型

- **Demo 会话**：用户用邀请码换 `session_token`，存 `sessionStorage`，随每个对话/查询请求作 `Authorization: Bearer <token>`
- **管理员会话**：用户名 + 密码换 `admin_*` 内存 token（重启后失效，按 KISS 设计未持久化）
- **SMS 验证码**：6 位随机码、5 分钟 TTL、60 秒限频；**登录时不比对用户提交的 code**（mock 模式），只验证记录存在

## 3. 对话流式接口

### `POST /api/chat/agent/stream`

```
Headers: Authorization: Bearer <session_token>
         Content-Type: application/json
         Accept: text/event-stream
```

**请求体**：

```json
{
  "messages": [{ "role": "user", "content": "分析该用户电池健康" }],
  "user_phone": "13061947220",
  "system_prompt": "（可选）覆盖默认系统提示词"
}
```

`messages` 是完整对话历史；最后一条必须是 `role=user`。多轮对话由前端把 `assistant` / `tool` 角色的历史一起 POST 过来，后端无状态。

**SSE 事件协议**（每个 `event:`+`data:` 块以空行分隔）：

| event | data 字段 | 说明 |
|---|---|---|
| `status` | `{message, chat_session_id?}` | 进度提示 / 携带新建会话 ID |
| `token` | `{text}` | 模型增量文本 |
| `tool_call` | `{id, name, arguments}` | 模型决定调用某工具，arguments 是 JSON 字符串 |
| `tool_result` | `{id, name, display, data, is_error}` | 后端工具执行结果。`display` 给用户看，`data` 给前端渲染 |
| `safety` | `{stage: "input"\|"output", reason, label?}` | 阿里云内容安全命中。后续会立刻 emit 一个友好 `token` 事件 |
| `error` | `{message, type}` | 系统/上游异常（vLLM 失败、配额耗尽等） |
| `done` | `{status: "ok"\|"blocked"\|"failed"\|"max_iters"}` | 终结事件 |

**安全命中时的用户体验**：
- 输入命中 → 不调用 vLLM，emit `safety` + `token: "让我们换个话题吧"` + `done: blocked`
- 输出命中 → 中止上游流，emit `safety` + `token: "\n\n很遗憾我无法回答"` + `done: blocked`

## 4. 充电记录接口

### `POST /api/charge/orders`

```json
{
  "phone": "13061947220",
  "start_time": "2025-10-01T00:00:00Z",
  "end_time": "2026-04-22T00:00:00Z"
}
```

`start_time` / `end_time` 可选，缺省取最近 6 个月。返回该手机号在窗口内**所有** `order_status=3`（已完成）的订单：

```json
{
  "phone_masked": "130****7220",
  "orders": [
    {
      "order_no": "...",
      "supplier_name": "...",
      "charge_start_time": "2026-04-21 18:11:03",
      "charge_end_time": "2026-04-21 18:41:51",
      "charge_capacity": 103.0,
      "series": {
        "time_offset_min": [0, 2, 7, 12, ...],
        "powers":          [0.0, 0.0, 214.2, ...],
        "voltages":        [225.5, 225.4, 225.1, ...],
        "currents":        [0.0, 0.0, 1.51, ...]
      }
    }
  ]
}
```

**后处理规则**（在 `charging_data_service.py`）：
- `GROUP_CONCAT` 按 `,` 拆分；`-1` 视为 `null`（没有上报数据点）
- 若首样 `push_time != 0` → 前插一个 0 分钟点（`power=0, current=0, voltage=首个非空电压`）
- 任意一列长度短了，对其它列截断到最短长度（防 GROUP_CONCAT 不对齐）

## 5. 鉴权 / 邀请码 / SMS

| 路由 | 用途 |
|---|---|
| `POST /api/auth/admin/login` | `{username, password}` → `{access_token}` |
| `POST /api/auth/invite/start` | 邀请码换 `session_token` |
| `POST /api/auth/sms/send` | 生成 mock 6 位码（5 分钟 TTL，60s 限频） |
| `POST /api/auth/sms/login` | 只校验是否有未过期未消费的记录 |

## 6. 内容安全

`build_content_safety(settings)` 自动选型：

```python
if (ALIYUN_ACCESS_KEY_ID + SECRET + ENDPOINT) 都已配置:
    AliyunContentSafetyService(fallback=KeywordService)
else:
    ContentSafetyService(mode="keyword")  # 本地关键词
```

阿里云调用规则：
- 输入端 `service=query_security_check` 同步 await
- 输出端 `service=response_security_check` 由 agent loop 累积 token，**每 ≥ 60 字符或遇到 `。！？；\n` 断句**就 `asyncio.create_task` 一次提交，每帧 `_drain_safety` 取已完成结果，命中立即截流并 emit `safety + 友好 token + done:blocked`
- SDK 调用失败自动 fallback 到关键词模式（保持服务可用）

## 7. 工具系统

`backend/app/services/tools/`：每个工具一个 `@register_tool(...)` 装饰的 async 函数，通过 OpenAI tool spec 注入到 vLLM。

| 工具 | 描述 | feed_back_to_model |
|---|---|---|
| `query_charging_records(phone?, start_time?, end_time?)` | 查 IOT MySQL，返回**该用户全部订单** | ✅ 是（下采样到 ~9 点回注） |
| `highlight_charge_segment(order_no, metric, start_min, end_min, reason, severity?)` | 让前端在该订单图上 markArea | ❌（display-only） |
| `compare_orders(order_nos[], metric)` | 跨订单聚合 max/avg/min；优先复用 `ctx.extras['orders_cache']` | ✅ |
| `web_search(query)` | 当前 stub，预留位 | ✅ |

新增工具：

```python
@register_tool(
    name="my_tool",
    description="...",
    parameters_schema={"type": "object", "properties": {...}, "required": [...]},
    feed_back_to_model=True,
)
async def _my_tool(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult(
        name="my_tool", call_id="",
        display="人类可读摘要（写入 ChatMessage.content）",
        data={...},          # 仅前端渲染用
        model_payload="...", # 回注模型用，feed_back=False 时为空
    )
```

Agent loop 上限：`_MAX_TOOL_ITERATIONS = 5`，每次 LLM 回合可发任意条 tool_call，全部执行后回注模型继续生成；display-only 工具回注 `"ok"` 占位。

## 8. 后台管理

### Admin 路由（需 `Authorization: Bearer admin_*`）

| 路由 | 说明 |
|---|---|
| `GET /api/admin/me` | 当前管理员身份 |
| `GET POST PATCH DELETE /api/admin/invites` | 邀请码 CRUD |
| `GET POST PATCH DELETE /api/admin/datasets`<br>+ `POST /api/admin/datasets/mysql-import` | 数据集 CRUD + 按手机号从 IOT MySQL 导入 |
| `GET PATCH /api/admin/users` | 用户列表（`?phone=&role=&limit=&offset=`）+ 启用/配额调整 |
| `GET POST PATCH DELETE /api/admin/prompts` | 系统提示词 CRUD（多 scope） |
| `GET POST PATCH DELETE /api/admin/welcome` | 用户欢迎语 CRUD |
| `GET /api/admin/conversations` | 对话列表（`?phone=&limit=&offset=`） |
| `GET /api/admin/conversations/{id}` | 对话消息详情（包含 tool 消息的 metadata） |

### 公开路由（用户端用）

| 路由 | 说明 |
|---|---|
| `GET /api/meta/system-prompt?scope=default` | 当前激活的系统提示词（无则 `null`） |
| `GET /api/meta/welcome` | 激活的欢迎语列表 |

### 前端后台

- 入口：`/admin`（未登录自动跳 `/admin/login`）
- 侧边菜单 7 项：平台概览 / 用户管理 / 邀请码 / 数据集 / 对话历史 / 系统提示词 / 欢迎语
- 完全基于 Ant Design v6 原生组件（`Layout` + `Menu` + `Table` + `Form` + `Modal`）

## 9. 数据流总览

```
[用户 ChatPage]
    │ SSE /api/chat/agent/stream
    │   1. status: session_ready              (chat_session 创建)
    │   2. Aliyun query_security_check        (输入安全)
    │   3. quota check + commit
    │   4. 循环最多 5 次：
    │       a. vLLM /chat/completions stream + tools=...
    │       b. 模型 emit content → token 事件 + 滚动窗口异步丢给 Aliyun response_check
    │       c. 模型 emit tool_calls → 聚合后 emit tool_call 事件
    │       d. 后端执行工具 → emit tool_result → 写 ChatMessage(role=tool, metadata)
    │       e. 工具结果回注下一轮 messages
    │   5. 最终 token 拼出 assistant 文本 → 写 ChatMessage(role=assistant)
    │   6. emit done

[后台 AdminPage]
    │ GET /api/admin/conversations         → 会话列表
    │ GET /api/admin/conversations/{id}    → 全量消息（含 tool metadata）
```

## 10. 关键源码索引

**后端**：
- `backend/app/services/agent_service.py` — agent loop（SSE 协议、安全异步审核、工具执行）
- `backend/app/services/charging_data_service.py` — IOT MySQL 查询 + 后处理
- `backend/app/services/content_safety.py` — Aliyun + keyword 双模
- `backend/app/services/tools/` — 工具框架与实现
- `backend/app/services/sms_service.py` — Mock SMS
- `backend/app/services/admin_content_service.py` — 提示词/欢迎语
- `backend/app/services/chat_history_service.py` — ChatSession/Message 持久化
- `backend/app/api/chat.py` `charge.py` `auth.py` `admin.py` `meta.py` — 路由层

**前端**：
- `frontend/src/api/agentChat.ts` — `fetchEventSource` 解析 SSE
- `frontend/src/api/chargeOrders.ts` `adminExtra.ts` `admin.ts` — REST 客户端
- `frontend/src/pages/ChatPage.tsx` — 用户对话页（AntD X Bubble/Sender + Splitter）
- `frontend/src/components/ChargeChartECharts.tsx` — ECharts + markArea
- `frontend/src/components/PhoneSearchPanel.tsx` — 手机号搜索面板
- `frontend/src/components/ToolCallCard.tsx` — 工具调用渲染（折叠卡片）
- `frontend/src/components/MarkdownView.tsx` — Markdown + 高亮
- `frontend/src/admin/AdminLayout.tsx` + `frontend/src/admin/views/*.tsx` — 后台

## 11. 测试

| 套件 | 用法 | 数量 |
|---|---|---|
| 单元 + 集成（默认） | `uv run pytest` | 37 |
| 真实 E2E（vLLM/Aliyun/MySQL） | `uv run pytest tests/live/ --override-ini="addopts="` | 14 |

`addopts=--ignore=tests/live` 让默认 pytest 不跑 live 套件。Live 套件需要 `.env` 中的真实凭据，缺哪个跳哪个用例（`require_live` 守卫）。
