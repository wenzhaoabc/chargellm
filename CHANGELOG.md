# Changelog

## 2026-04-22 — Phase 1 ~ 3 完成

### 核心能力

- **真实充电数据接入**：`app/services/charging_data_service.py` 按 MyBatis XML 翻译的参数化 SQL，从 `IOT_DB_URL` 查询 `smc_device_order_push(_finish)` 并做 GROUP_CONCAT / null-sentinel / 零前插等后处理
- **流式 Agent Loop**：`app/services/agent_service.py` 重写，SSE 协议 `token/tool_call/tool_result/safety/status/error/done`，支持多轮工具调用（`_MAX_TOOL_ITERATIONS = 5`）
- **工具框架**：`app/services/tools/` — `@register_tool` 装饰器、`ToolContext`、`feed_back_to_model` 开关；内置四个工具
- **阿里云内容安全**：`AliyunContentSafetyService.check_input/_output`（`alibabacloud-green20220302 TextModerationPlus`）+ 滚动窗口异步审核；命中时自动下发友好 token（输入 `让我们换个话题吧`，输出 `很遗憾我无法回答`）
- **SMS mock 流程修正**：新增 `SmsCode` 表 + `sms_service.py`（5 分钟 TTL、60 秒限频），登录不对比 code

### 后台管理

- 新模型：`SystemPrompt`、`WelcomeMessage`、`SmsCode`
- 新路由：`/api/admin/{users, prompts, welcome, conversations}` 全套 CRUD
- 公开路由：`/api/meta/{system-prompt, welcome}`
- Agent loop 自动 persist `ChatSession + ChatMessage`（含 tool metadata）供管理员审计
- `import_dataset_from_mysql` 从 NotImplementedError 改为真实 IOT 导入

### 前端

- 对话页 `ChatPage.tsx` 基于 Ant Design X `Bubble` + `Sender` + `Splitter`，集成 Markdown、ECharts markArea 高亮、工具调用卡片
- 新组件：`ChargeChartECharts` `PhoneSearchPanel` `ToolCallCard` `MarkdownView`
- 后台 `AdminLayout` + 7 个 views：Dashboard / User / Invite / Dataset / Conversation / Prompt / Welcome

### 测试

- 默认套件：37 passed（单元 + 集成，SQLite，约 8 秒）
- Live 套件：14 passed（真实 vLLM `chargesafe-oss` + Aliyun + IOT MySQL，约 2 分钟），覆盖：
  - 纯文本单轮 / 工具调用 / 高亮工具 / 多轮上下文记忆 / 多轮工具结果复用
  - 输入敏感词（友好引导回复） / 正常提示词引导越狱（安全层或模型自拒）
  - 用户视角：容量询问 / 充电时长询问 / 健康判断 / 对照组
  - 配额耗尽 / 对话历史持久化与管理员读取

### 文档

- `README.md` — 顶层导航，一分钟跑起来
- `docs/usage.md` — 用户/管理员/开发者三视角使用说明 + FAQ
- `docs/platform.md` — 架构、SSE 协议、所有 API、数据流、源码索引
- `backend/.env.example` — 完整字段注释
