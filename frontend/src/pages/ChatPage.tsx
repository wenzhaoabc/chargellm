import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  App,
  Avatar,
  Button,
  Empty,
  Layout,
  Modal,
  Space,
  Spin,
  Splitter,
  Tag,
  Typography,
} from 'antd'
import { Bubble, Sender } from '@ant-design/x'
import { ClearOutlined, RobotOutlined, UserOutlined, WarningFilled } from '@ant-design/icons'
import { generateChatTitle, streamAgentChat, type AgentChatMessage, type AgentEvent } from '@/api/agentChat'
import type { ChargeOrder } from '@/api/chargeOrders'
import {
  NEW_CONVERSATION_EVENT,
  OPEN_CONVERSATION_EVENT,
  appendConversationTurn,
  createConversationId,
  getActiveConversationId,
  getConversationById,
  setActiveConversationId,
  setConversationChatSessionId,
  updateConversationTitle,
} from '@/api/conversations'
import { ChargeChartECharts, type ChargeHighlight } from '@/components/ChargeChartECharts'
import { MarkdownView } from '@/components/MarkdownView'
import { PhoneSearchPanel } from '@/components/PhoneSearchPanel'
import { ToolCallCard, type ToolInvocation } from '@/components/ToolCallCard'

type UiMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  toolInvocations: ToolInvocation[]
  // Highlights captured from highlight_charge_segment tool calls, grouped by
  // order_no so we can render an inline chart for each affected order.
  highlightsByOrder: Record<string, ChargeHighlight[]>
  blocked?: { stage: string; reason: string; label?: string }
  status?: 'streaming' | 'done' | 'error'
}

const CONTEXT_KEY = 'chargellm.chat.context'

type ChatContext = {
  phone: string
  phoneMasked: string
  orders: ChargeOrder[]
}

function newId() {
  return `m_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function loadContext(): ChatContext | null {
  if (typeof window === 'undefined') return null
  const raw = window.sessionStorage.getItem(CONTEXT_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as ChatContext
  } catch {
    return null
  }
}

function saveContext(ctx: ChatContext | null) {
  if (typeof window === 'undefined') return
  if (ctx) window.sessionStorage.setItem(CONTEXT_KEY, JSON.stringify(ctx))
  else window.sessionStorage.removeItem(CONTEXT_KEY)
}

export function ChatPage() {
  const { message } = App.useApp()
  const [context, setContext] = useState<ChatContext | null>(() => loadContext())
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [draft, setDraft] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [previewOrder, setPreviewOrder] = useState<ChargeOrder | null>(null)
  // Conversation currently open on this page — persisted on each completed turn.
  const [conversationId, setConversationId] = useState<string>(() => getActiveConversationId())
  // Backend ChatSession id sent on the first `status` event of the stream.
  const chatSessionIdRef = useRef<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    saveContext(context)
  }, [context])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const resetConversationState = useCallback(() => {
    setMessages([])
    abortRef.current?.abort()
    setStreaming(false)
    chatSessionIdRef.current = null
  }, [])

  // Listen to sidebar "new" / "open" events so the ChatPage can sync.
  useEffect(() => {
    const onNew = () => {
      resetConversationState()
      setConversationId('')
    }
    const onOpen = (e: Event) => {
      const target = (e as CustomEvent).detail?.conversationId as string | undefined
      if (!target) return
      const record = getConversationById(target)
      if (!record) return
      abortRef.current?.abort()
      setStreaming(false)
      chatSessionIdRef.current = record.chatSessionId ?? null
      setConversationId(record.id)
      // Reconstruct UiMessages from saved turns (each turn = user + assistant pair).
      const restored: UiMessage[] = []
      for (const turn of record.turns) {
        restored.push({
          id: `${turn.id}-u`,
          role: 'user',
          text: turn.question,
          toolInvocations: [],
          highlightsByOrder: {},
          status: 'done',
        })
        restored.push({
          id: `${turn.id}-a`,
          role: 'assistant',
          text: turn.answer,
          toolInvocations: [],
          highlightsByOrder: {},
          status: 'done',
        })
      }
      setMessages(restored)
    }
    window.addEventListener(NEW_CONVERSATION_EVENT, onNew)
    window.addEventListener(OPEN_CONVERSATION_EVENT, onOpen)
    return () => {
      window.removeEventListener(NEW_CONVERSATION_EVENT, onNew)
      window.removeEventListener(OPEN_CONVERSATION_EVENT, onOpen)
    }
  }, [resetConversationState])

  function onUseOrders(phone: string, orders: ChargeOrder[]) {
    const phoneMasked = phone.length >= 7 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone
    setContext({ phone, phoneMasked, orders })
    message.success(`已加载 ${orders.length} 次充电记录到对话上下文`)
  }

  function onClear() {
    resetConversationState()
    setConversationId('')
    setActiveConversationId('')
  }

  function buildHistory(currentMessages: UiMessage[]): AgentChatMessage[] {
    const history: AgentChatMessage[] = []
    for (const m of currentMessages) {
      if (m.role === 'user') {
        history.push({ role: 'user', content: m.text })
      } else if (m.text.trim()) {
        history.push({ role: 'assistant', content: m.text })
      }
    }
    return history
  }

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed) return
    if (!context) {
      message.warning('请先在左侧搜索手机号并将充电记录送入对话')
      return
    }
    // Materialize a conversation id on first send if missing.
    let activeConvId = conversationId
    if (!activeConvId) {
      activeConvId = createConversationId()
      setConversationId(activeConvId)
      setActiveConversationId(activeConvId)
    }
    const isFirstTurn = messages.length === 0

    const userMsg: UiMessage = {
      id: newId(),
      role: 'user',
      text: trimmed,
      toolInvocations: [],
      highlightsByOrder: {},
    }
    const assistantMsg: UiMessage = {
      id: newId(),
      role: 'assistant',
      text: '',
      toolInvocations: [],
      highlightsByOrder: {},
      status: 'streaming',
    }
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setDraft('')
    setStreaming(true)

    const history = buildHistory([...messages, userMsg])
    const controller = new AbortController()
    abortRef.current = controller

    const ordersSummary = context.orders.map((o) => ({
      order_no: o.order_no,
      supplier_name: o.supplier_name,
      charge_start_time: o.charge_start_time,
      charge_end_time: o.charge_end_time,
      charge_capacity: o.charge_capacity,
      points: o.series.time_offset_min.length,
    }))
    const systemPrompt = `当前对话已绑定用户手机号 ${context.phone}（脱敏 ${context.phoneMasked}），已预先加载该用户最近 ${context.orders.length} 次充电订单：${JSON.stringify(ordersSummary)}。请基于跨订单趋势进行综合诊断；当需要明细数据时调用 query_charging_records 工具；如某次订单某段曲线明显异常请调用 highlight_charge_segment 让前端高亮显示。`

    let doneStatus: AgentEvent['type'] | string = 'streaming'
    try {
      await streamAgentChat(
        { messages: history, user_phone: context.phone, system_prompt: systemPrompt, signal: controller.signal },
        {
          onEvent: (evt) => {
            applyEvent(assistantMsg.id, evt)
            if (evt.type === 'status' && typeof evt.chat_session_id === 'number') {
              chatSessionIdRef.current = evt.chat_session_id
              setConversationChatSessionId(activeConvId, evt.chat_session_id)
            }
            if (evt.type === 'done') {
              doneStatus = evt.status
            }
          },
          onError: (err) => {
            applyEvent(assistantMsg.id, { type: 'error', message: err.message })
          },
        },
      )
    } catch (err) {
      applyEvent(assistantMsg.id, { type: 'error', message: err instanceof Error ? err.message : String(err) })
    } finally {
      setStreaming(false)
      abortRef.current = null
    }

    // Persist this turn into sidebar history regardless of success/blocked so
    // the user can revisit what happened.
    const finalAssistantText = await new Promise<string>((resolve) => {
      setMessages((prev) => {
        const answer = prev.find((m) => m.id === assistantMsg.id)?.text || ''
        resolve(answer)
        return prev
      })
    })
    appendConversationTurn(activeConvId, {
      id: userMsg.id,
      question: trimmed,
      answer: finalAssistantText,
      batteryName: context.phoneMasked,
      batteryLabel: `${context.orders.length} 次充电`,
    })

    // Problem 5: on the first completed OK turn, ask the fast model for a title.
    if (isFirstTurn && doneStatus === 'ok' && finalAssistantText.trim()) {
      try {
        const title = await generateChatTitle({
          user_message: trimmed,
          assistant_message: finalAssistantText,
          chat_session_id: chatSessionIdRef.current,
        })
        if (title) updateConversationTitle(activeConvId, title)
      } catch (err) {
        // fall back silently to user-message-derived title
      }
    }
  }

  function applyEvent(messageId: string, evt: AgentEvent) {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== messageId) return m
        switch (evt.type) {
          case 'token':
            return { ...m, text: m.text + evt.text }
          case 'tool_call':
            return {
              ...m,
              toolInvocations: [
                ...m.toolInvocations,
                { id: evt.id, name: evt.name, arguments: evt.arguments },
              ],
            }
          case 'tool_result': {
            const toolInvocations = m.toolInvocations.map((t) =>
              t.id === evt.id ? { ...t, result: evt } : t,
            )
            let highlightsByOrder = m.highlightsByOrder
            if (evt.name === 'highlight_charge_segment' && !evt.is_error) {
              const data = evt.data as Record<string, unknown>
              const orderNo = String(data.order_no || '')
              const highlight: ChargeHighlight = {
                metric: (data.metric as ChargeHighlight['metric']) || 'power',
                start_min: Number(data.start_min || 0),
                end_min: Number(data.end_min || 0),
                reason: String(data.reason || ''),
                severity: (data.severity as ChargeHighlight['severity']) || 'warning',
              }
              highlightsByOrder = {
                ...m.highlightsByOrder,
                [orderNo]: [...(m.highlightsByOrder[orderNo] || []), highlight],
              }
            }
            return { ...m, toolInvocations, highlightsByOrder }
          }
          case 'safety':
            return {
              ...m,
              status: 'error',
              blocked: { stage: evt.stage, reason: evt.reason, label: evt.label },
            }
          case 'error':
            return { ...m, status: 'error', text: m.text + `\n\n> 错误: ${evt.message}` }
          case 'done':
            return { ...m, status: evt.status === 'ok' ? 'done' : 'error' }
          default:
            return m
        }
      }),
    )
  }

  const ordersByNo = useMemo(() => {
    const map: Record<string, ChargeOrder> = {}
    context?.orders.forEach((o) => {
      map[o.order_no] = o
    })
    return map
  }, [context])

  return (
    <Layout style={{ height: 'calc(100vh - 64px)', background: '#fff' }}>
      <Splitter style={{ height: '100%' }}>
        <Splitter.Panel defaultSize={360} min={280} max={520}>
          <div style={{ padding: 12, height: '100%', overflowY: 'auto' }}>
            <PhoneSearchPanel onUseOrders={onUseOrders} />
            {context && (
              <div style={{ marginTop: 12 }}>
                <Typography.Title level={5} style={{ marginBottom: 8 }}>
                  当前用户充电曲线
                </Typography.Title>
                <Space direction="vertical" style={{ width: '100%' }} size={10}>
                  {context.orders.map((o) => (
                    <div
                      key={o.order_no}
                      style={{ border: '1px solid #f0f0f0', borderRadius: 8, padding: 8, cursor: 'pointer' }}
                      onClick={() => setPreviewOrder(o)}
                    >
                      <Space size={6} wrap>
                        <Typography.Text strong style={{ fontSize: 12 }}>{o.order_no}</Typography.Text>
                        {o.supplier_name && <Tag>{o.supplier_name}</Tag>}
                      </Space>
                      <ChargeChartECharts order={o} height={140} compact />
                    </div>
                  ))}
                </Space>
              </div>
            )}
          </div>
        </Splitter.Panel>
        <Splitter.Panel>
          <Layout style={{ height: '100%', background: '#fff' }}>
            <Layout.Header
              style={{
                background: '#fff',
                borderBottom: '1px solid #f0f0f0',
                padding: '0 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                height: 52,
              }}
            >
              <Space>
                <Typography.Title level={5} style={{ margin: 0 }}>
                  ChargeLLM 智能诊断
                </Typography.Title>
                {context && <Tag color="blue">{context.phoneMasked}</Tag>}
              </Space>
              <Button icon={<ClearOutlined />} size="small" onClick={onClear} disabled={messages.length === 0}>
                清空对话
              </Button>
            </Layout.Header>
            <Layout.Content
              ref={scrollRef as never}
              style={{ padding: 16, overflowY: 'auto', background: '#fafafa' }}
            >
              {messages.length === 0 ? (
                <Empty
                  description={context ? '直接提问，例如：请分析这位用户的电池健康状况' : '请先在左侧搜索一个手机号'}
                />
              ) : (
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  {messages.map((m) => renderMessage(m, ordersByNo))}
                </Space>
              )}
            </Layout.Content>
            <Layout.Footer style={{ padding: 12, background: '#fff', borderTop: '1px solid #f0f0f0' }}>
              <Sender
                value={draft}
                onChange={setDraft}
                onSubmit={send}
                loading={streaming}
                onCancel={() => abortRef.current?.abort()}
                placeholder={context ? '请输入问题…' : '请先在左侧搜索手机号'}
                disabled={!context}
              />
            </Layout.Footer>
          </Layout>
        </Splitter.Panel>
      </Splitter>
      <Modal
        open={Boolean(previewOrder)}
        onCancel={() => setPreviewOrder(null)}
        footer={null}
        width={840}
        title={previewOrder ? `订单 ${previewOrder.order_no}` : ''}
      >
        {previewOrder && <ChargeChartECharts order={previewOrder} height={420} />}
      </Modal>
    </Layout>
  )
}

function renderMessage(m: UiMessage, ordersByNo: Record<string, ChargeOrder>) {
  if (m.role === 'user') {
    return (
      <Bubble
        key={m.id}
        placement="end"
        avatar={<Avatar icon={<UserOutlined />} style={{ background: '#1677ff' }} />}
        content={<Typography.Text>{m.text}</Typography.Text>}
      />
    )
  }
  const charts = Object.entries(m.highlightsByOrder)
    .map(([orderNo, highlights]) => {
      const order = ordersByNo[orderNo]
      if (!order) return null
      return (
        <div key={orderNo} style={{ marginTop: 10 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            订单 {orderNo} 异常高亮
          </Typography.Text>
          <ChargeChartECharts order={order} highlights={highlights} height={260} />
        </div>
      )
    })
    .filter(Boolean)

  const content = (
    <div style={{ minWidth: 280 }}>
      {m.blocked && (
        <Space style={{ marginBottom: 8 }}>
          <WarningFilled style={{ color: '#faad14' }} />
          <Typography.Text type="warning">
            内容安全审核未通过 ({m.blocked.stage}/{m.blocked.label || m.blocked.reason})
          </Typography.Text>
        </Space>
      )}
      {m.toolInvocations.map((inv) => (
        <ToolCallCard key={inv.id} invocation={inv} />
      ))}
      {m.text && <MarkdownView text={m.text} />}
      {!m.text && !m.blocked && m.status === 'streaming' && <Spin size="small" />}
      {charts}
    </div>
  )

  return (
    <Bubble
      key={m.id}
      placement="start"
      avatar={<Avatar icon={<RobotOutlined />} style={{ background: '#52c41a' }} />}
      content={content}
    />
  )
}
