# ChargeLLM 使用说明

本文从三个视角讲清楚"怎么用"：

- [普通用户（对话端）](#一普通用户对话端)
- [管理员（后台）](#二管理员后台)
- [开发者（本地联调 + 扩展）](#三开发者本地联调--扩展)

如果你要读架构和 API，请看 [`platform.md`](./platform.md)。

---

## 一、普通用户（对话端）

### 1.1 入口与登录

- 访问 `http://<host>/chat`
- 第一次进入时，系统会引导输入**邀请码**（管理员发放）
- 邀请码换取的 demo 会话 token 存在浏览器 `sessionStorage`，关闭窗口失效；无需重新输入账号密码

> 短信登录 `/api/auth/sms/*` 在当前版本是 mock（不实发短信），但流程完整，便于后续接入真实 SMS 服务商。

### 1.2 加载用户充电记录

1. 左侧面板输入需要分析的**手机号**（示例：`13061947220` / `13122553940` / `13154428629`）
2. 点击"查询"→ 下方展示该手机号最近 6 个月的全部充电订单
3. 点击 **"将全部记录送入对话分析"** — 全部订单会作为上下文塞入后续每一次提问

### 1.3 提问的几种典型场景

| 用户意图 | 示例提问 | 后端行为 |
|---|---|---|
| 一般健康诊断 | "请分析这位用户的电池健康状况" | 触发 `query_charging_records` → 跨订单分析 → 文本结论 |
| 容量相关 | "我的电池容量还剩多少？" | 基于充电量 + 容量区间做估算 |
| 充电时长 | "我每次充电时长是不是有点不正常？" | 比较各订单起止时间 |
| 异常高亮 | "如果哪次充电异常就在图上标出来" | 模型调用 `highlight_charge_segment`，前端 ECharts `markArea` 展示 |
| 多轮追问 | Q1:"这位用户充了几次"<br>Q2:"最后一次容量多少？" | 后端无状态，前端把历史一起 POST |
| 跨订单对比 | "这几次的峰值功率有衰减吗？" | 触发 `compare_orders` 聚合 max/avg/min |

每一次对话的流式协议：**模型的 token 实时显示 → 工具调用用卡片显示并可展开参数 → 高亮结果直接在 Chart 上标色**。

### 1.4 内容安全

- **恶意输入**（违法 / 色情 / 暴力等）→ 界面会显示"让我们换个话题吧"，不会真正调用大模型
- **通过正常提问诱导大模型输出违法内容** → 输出阶段安全审核命中，剩余未输出文本会中止，补上"很遗憾我无法回答"

这两种拒绝都是系统层 Aliyun 内容安全 + 模型自我拒绝共同保障的。

### 1.5 配额

每个邀请码有两个配额维度：
- `max_uses`：邀请码总共能被几个不同用户使用
- `per_user_quota`：单个用户最多发多少次消息

配额耗尽 → SSE 返回 `done: blocked` + `error: quota`，界面会提示"体验次数已用完"。

---

## 二、管理员（后台）

### 2.1 登录

- 访问 `http://<host>/admin`
- 默认管理员：`.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`（生产环境请一定修改）

### 2.2 七大管理模块

| 模块 | 功能 |
|---|---|
| **平台概览** | 注册用户数、邀请码数、对话历史数等统计 |
| **用户管理** | 按手机号/角色筛选；启用/禁用；调整 `usage_quota_total` |
| **邀请码管理** | 新建自定义/自动编码；限制 `max_uses` 与 `per_user_quota`；启停；删除 |
| **充电数据集** | 数据集 CRUD；**从 IOT MySQL 按手机号 + 时间范围一键导入** |
| **对话历史** | 列表 + 按手机号搜索；点开查看完整消息（user/tool/assistant）+ 工具调用 metadata |
| **系统提示词** | 按 `scope` 维护多条提示词；激活后自动作用于所有新对话 |
| **欢迎语** | 用户对话页展示；支持激活/草稿；排序 |

### 2.3 系统提示词工作机制

1. 管理员在"系统提示词"模块新建一条 `scope=default`、`is_active=true` 的记录
2. 用户下次发起对话时，`/api/chat/agent/stream` 路由会自动 `get_active_system_prompt(db)` 注入到 `messages[0]`
3. 用户端通过 `user_phone` + `orders` 的上下文注入，与管理员的提示词互不冲突
4. 用户端若显式传了 `system_prompt` 字段，会覆盖 DB 版（用于 A/B 测试）

### 2.4 管理员安全提醒

- 管理员 token 是**内存态**，重启服务即失效 — 这是刻意的 KISS 设计，意味着每次后端重启需要管理员重新登录
- `.env` 中 `JWT_SECRET` / `ADMIN_PASSWORD` / `ALIYUN_*` / `VLLM_API_KEY` / `IOT_DB_URL` 都是敏感项，**不要**提交到仓库
- "充电数据集 → MySQL 导入"只能被管理员触发；用户端的 `/api/charge/orders` 查手机号会走 demo session token 鉴权

---

## 三、开发者（本地联调 + 扩展）

### 3.1 环境准备

```bash
# 后端
cd backend
cp .env.example .env            # 填入真实凭据
uv pip install -e ".[dev]"
uv pip install alibabacloud-green20220302 pymysql cryptography sse-starlette httpx

# 前端
cd ../frontend
npm install
```

`.env` 关键字段（详细列表见 `backend/.env.example`）：

```
# vLLM（OpenAI 兼容）
VLLM_BASE_URL=https://<your-endpoint>/v1
VLLM_MODEL=<model-name>
VLLM_API_KEY=<key>
VLLM_MOCK=false   # live 测试必须设为 false

# IOT MySQL 只读
IOT_DB_URL=mysql://user:pwd@host:3306/database

# Aliyun 内容安全
ALIYUN_ACCESS_KEY_ID=...
ALIYUN_ACCESS_KEY_SECRET=...
ALIYUN_CONTENT_SAFETY_ENDPOINT=green-cip.cn-shanghai.aliyuncs.com
ALIYUN_REGION_ID=cn-shanghai

# 管理员与邀请码
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password>
CHARGELLM_INVITE_DEFAULT_MAX_USES=20
CHARGELLM_INVITE_DEFAULT_PER_USER_QUOTA=10
```

### 3.2 启动

```bash
# 终端 1：后端
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 终端 2：前端
cd frontend && npm run dev       # http://localhost:5173
```

### 3.3 常用 cURL 联调片段

```bash
# 1. 管理员登录
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/admin/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# 2. 创建一张邀请码
curl -s -X POST http://127.0.0.1:8000/api/admin/invites \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"dev","max_uses":5,"per_user_quota":20}'

# 3. 用邀请码换 demo session
SESSION=$(curl -s -X POST http://127.0.0.1:8000/api/auth/invite/start \
  -H 'Content-Type: application/json' \
  -d '{"invite_code":"<上一步返回的 code>"}' | jq -r .session_token)

# 4. 查充电订单
curl -s -X POST http://127.0.0.1:8000/api/charge/orders \
  -H "Authorization: Bearer $SESSION" -H 'Content-Type: application/json' \
  -d '{"phone":"13061947220"}' | jq '.orders | length'

# 5. Agent SSE 流式对话
curl -N -X POST http://127.0.0.1:8000/api/chat/agent/stream \
  -H "Authorization: Bearer $SESSION" -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"请分析手机号 13061947220 的电池健康"}],
       "user_phone":"13061947220"}'
```

### 3.4 扩展：新增一个工具

1. 在 `backend/app/services/tools/implementations.py` 里添加：

   ```python
   @register_tool(
       name="estimate_remaining_range",
       description="根据电池健康 + 最近一次充电容量 估算续航公里数",
       parameters_schema={
           "type": "object",
           "properties": {
               "capacity_wh": {"type": "number"},
               "watt_per_km": {"type": "number", "default": 15},
           },
           "required": ["capacity_wh"],
       },
       feed_back_to_model=True,
   )
   async def _estimate_remaining_range(args: dict, ctx: ToolContext) -> ToolResult:
       km = float(args["capacity_wh"]) / float(args.get("watt_per_km") or 15)
       return ToolResult(
           name="estimate_remaining_range",
           call_id="",
           display=f"预计续航约 {km:.1f} km",
           data={"km": km},
           model_payload=json.dumps({"km": km}),
       )
   ```

2. 模块在 `__init__.py` 中已自动 import，重启后端即生效
3. **不需要**改前端代码：`ToolCallCard` 通用渲染，显示 display + 可折叠参数

### 3.5 扩展：新增管理员视图

1. 在 `backend/app/api/admin.py` 添加新路由
2. 新增对应 schema（`backend/app/schemas/admin_content.py`）
3. 前端在 `frontend/src/admin/views/` 新建 `XxxView.tsx`
4. 在 `frontend/src/admin/AdminLayout.tsx` 的 `MENU_ITEMS` 与 `switch(selected)` 里注册

### 3.6 测试指南

```bash
# 默认套件（37 个，单元 + 集成，约 8 秒）
cd backend && uv run pytest

# Live 套件（14 个，真实 vLLM/Aliyun/MySQL，约 2 分钟）
uv run pytest tests/live/ -v --override-ini="addopts="

# 前端构建校验
cd ../frontend && npm run build
```

**覆盖范围**：
- `tests/test_admin_extension.py` — 用户/提示词/欢迎语/对话历史管理路由
- `tests/test_agent_loop.py` — Agent loop 单元：工具事件序列、输入安全短路、配额阻断
- `tests/test_charging_data.py` — MySQL 后处理逻辑（空值、缺首零、长度不对齐等）
- `tests/test_sms.py` — SMS 生成/消费/过期
- `tests/test_datasets.py` `test_invite.py` `test_chat.py` `test_config.py` `test_health.py`
- `tests/live/test_agent_live_e2e.py` — 8 条端到端：纯文本/工具调用/高亮/多轮记忆/多轮工具复用/安全/配额/持久化
- `tests/live/test_user_scenarios.py` — 6 条用户视角：容量/充电时长/健康/恶意输入/越狱引导/对照组

### 3.7 部署注意事项

- 前端 `VITE_API_BASE_URL=/api`（同域反向代理），或直接指向后端 URL
- 反代需透传 `text/event-stream`，关闭 `proxy_buffering`，`proxy_read_timeout` ≥ 120s
- `ChargeLLM` 的 SQLite 数据文件 `backend/data/chargellm_demo.db` 需要持久化卷
- Aliyun SDK 的时区警告（DeprecationWarning）可忽略，不影响功能

---

## 四、常见问题排查

| 症状 | 可能原因 | 解决 |
|---|---|---|
| SSE 立刻返回 `error: Insufficient account balance` | vLLM 代理账户余额为 0 | 充值；或临时 `VLLM_MOCK=true` 切 mock |
| `/api/charge/orders` 503 `iot_db_not_configured` | `.env` 没配置 `IOT_DB_URL` | 填写后重启后端 |
| `/api/charge/orders` 502 `iot_db_query_failed` | MySQL 连接超时或权限问题 | 查 backend 日志里的 `charge order query failed` 堆栈 |
| 对话总是返回空白 | 前端 session_token 失效 | 清 `sessionStorage` 后用邀请码重新进入 |
| 内容安全一直返回 allow | 凭据缺失 → fallback 关键词模式 | 补齐 `ALIYUN_*` 三项 + 重启；或手动 `CHARGELLM_CONTENT_SAFETY_MODE=aliyun` |
| 管理员登录后 401 | 后端重启导致 admin token 失效 | 重新登录即可 |
| 浏览器打字时工具卡片闪烁 | React 虚拟 DOM 刷新频率高 | 当前默认每帧渲染，若卡顿可在 `ChatPage` 里节流 `applyEvent` 的 setState |
