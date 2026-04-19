import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import { ChargeChart } from '@/components/ChargeChart'
import { InviteGate } from '@/components/InviteGate'
import { getInviteCode, hasInviteAccess } from '@/api/auth'
import { listExampleBatteries } from '@/api/charge'
import { runChatStream } from '@/api/chat'
import type { BatteryExample, ChatEvent, ChargingProcess, DiagnosisResult } from '@/api/types'

type ChatTurn = {
  id: string
  question: string
  battery: BatteryExample
  events: ChatEvent[]
  result: DiagnosisResult | null
  pending: boolean
}

function buildPath(values: number[], width: number, height: number) {
  if (values.length === 0) {
    return ''
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return values
    .map((value, index) => {
      const x = values.length === 1 ? width : (index / (values.length - 1)) * width
      const y = height - ((value - min) / range) * height
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
}

function MiniSeriesPreview({ battery }: { battery: BatteryExample }) {
  const process: ChargingProcess = battery.processes.find((item) => item.processId === battery.highlightedProcessId)
    || battery.processes[0]
  const powerPath = buildPath(process.power, 140, 44)
  const currentPath = buildPath(process.current, 140, 44)

  return (
    <div className="mini-series">
      <svg viewBox="0 0 140 44" role="img" aria-label={`${battery.name} 时序数据预览`}>
        <path d={powerPath} className="mini-series-power" />
        <path d={currentPath} className="mini-series-current" />
      </svg>
      <div>
        <strong>{battery.name}</strong>
        <span>{battery.label} · {battery.capacityRange}</span>
      </div>
    </div>
  )
}

function ThoughtPanel({ events, pending }: { events: ChatEvent[]; pending: boolean }) {
  const thoughtEvents = events.filter((event) => event.type !== 'token' && event.type !== 'final')
  if (thoughtEvents.length === 0) {
    return null
  }

  return (
    <details className="message-bubble thought-panel">
      <summary>{pending ? '正在思考' : '思考过程'} · {thoughtEvents.length} 步</summary>
      <div className="thought-list">
        {thoughtEvents.map((event, index) => (
          <div key={`${event.type}-${index}`} className="thought-row">
            <span className={`stream-type ${event.type}`}>{event.type}</span>
            <div>
              <div className="stream-message">{event.message}</div>
              {event.payload ? <pre className="stream-payload">{JSON.stringify(event.payload, null, 2)}</pre> : null}
            </div>
          </div>
        ))}
      </div>
    </details>
  )
}

function AssistantAnswer({ turn }: { turn: ChatTurn }) {
  const assistantAnswer = turn.events
    .filter((event) => event.type === 'token')
    .map((event) => event.message)
    .join('')

  return (
    <div className="message assistant-message">
      <div className="message-avatar">AI</div>
      <div className="assistant-stack">
        <ThoughtPanel events={turn.events} pending={turn.pending} />
        {assistantAnswer ? (
          <div className="message-bubble">
            <p>{assistantAnswer}</p>
          </div>
        ) : null}
        {turn.result ? (
          <div className="message-bubble result-bubble">
            <strong>{turn.result.label}</strong>
            <span>{turn.result.capacityRange}</span>
            <p>{turn.result.reason}</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}

export function DemoPage() {
  const batteries = useMemo(() => listExampleBatteries(), [])
  const [selectedBatteryId, setSelectedBatteryId] = useState(batteries[0]?.id || '')
  const selectedBattery = batteries.find((item) => item.id === selectedBatteryId) ?? batteries[0]!
  const [inviteCode, setInviteCode] = useState(getInviteCode())
  const [question, setQuestion] = useState('这块电池是否存在老化趋势？')
  const [pending, setPending] = useState(false)
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [detailBatteryId, setDetailBatteryId] = useState<string | null>(null)

  const inviteUnlocked = hasInviteAccess()
  const detailBattery = batteries.find((item) => item.id === detailBatteryId)

  const handleAsk = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!inviteUnlocked || !selectedBattery) {
      return
    }
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) {
      return
    }

    const turnId = `${Date.now()}-${selectedBattery.id}`
    setPending(true)
    setTurns((current) => [
      ...current,
      {
        id: turnId,
        question: trimmedQuestion,
        battery: selectedBattery,
        events: [],
        result: null,
        pending: true,
      },
    ])

    await runChatStream(
      {
        batteryId: selectedBattery.id,
        inviteCode,
        question: trimmedQuestion,
      },
      {
        onEvent: (chatEvent) => {
          setTurns((current) =>
            current.map((turn) =>
              turn.id === turnId
                ? {
                    ...turn,
                    events: [...turn.events, chatEvent],
                    result: chatEvent.type === 'final' && chatEvent.payload ? (chatEvent.payload as DiagnosisResult) : turn.result,
                  }
                : turn,
            ),
          )
          if (chatEvent.type === 'final' && chatEvent.payload) {
            setTurns((current) =>
              current.map((turn) =>
                turn.id === turnId ? { ...turn, result: chatEvent.payload as DiagnosisResult } : turn,
              ),
            )
          }
        },
        onFinal: (diagnosis) => {
          setTurns((current) =>
            current.map((turn) => (turn.id === turnId ? { ...turn, result: diagnosis } : turn)),
          )
        },
      },
    )

    setTurns((current) => current.map((turn) => (turn.id === turnId ? { ...turn, pending: false } : turn)))
    setPending(false)
  }

  const handleUseExample = (batteryId: string) => {
    setSelectedBatteryId(batteryId)
    const battery = batteries.find((item) => item.id === batteryId)
    setQuestion(
      battery
        ? `请基于示例数据“${battery.name}”分析这块电池的健康状态、容量范围和关键充电过程。`
        : '请分析这块电池的健康状态。',
    )
  }

  return (
    <div className="chat-workspace">
      <section className="conversation-panel">
        <div className="conversation-header">
          <div>
            <div className="section-kicker">ChargeLLM Chat</div>
            <h2>电池充电数据诊断助手</h2>
          </div>
          <div className="header-actions">
            <span className="beta-pill">公测版</span>
            <span className={`status-pill ${inviteUnlocked ? 'success' : 'warning'}`}>
              {inviteUnlocked ? '邀请码已启用' : '输入框已禁用'}
            </span>
          </div>
        </div>

        <div className="message-list">
          {!inviteUnlocked ? (
            <div className="message assistant-message">
              <div className="message-avatar">AI</div>
              <div className="message-bubble invite-message">
                <InviteGate onConfirmed={setInviteCode} />
              </div>
            </div>
          ) : null}

          <div className="message assistant-message">
            <div className="message-avatar">AI</div>
            <div className="message-bubble">
              <p>
                请先查询你的真实历史充电记录，或点击下方示例数据快速体验。示例会自动带入当前对话，
                你可以继续追问容量范围、异常过程和健康状态。
              </p>
            </div>
          </div>

          {turns.map((turn) => (
            <div key={turn.id} className="turn-block">
              <div className="message user-message">
                <div className="message-bubble user-bubble">
                  <p>{turn.question}</p>
                  <MiniSeriesPreview battery={turn.battery} />
                </div>
                <div className="message-avatar user-avatar">你</div>
              </div>
              <AssistantAnswer turn={turn} />
            </div>
          ))}
        </div>

        <div className="composer-shell">
          <div className="floating-examples">
            {batteries.map((battery) => (
              <article key={battery.id} className={`floating-card ${battery.id === selectedBattery.id ? 'active' : ''}`}>
                <button type="button" className="card-main" onClick={() => handleUseExample(battery.id)}>
                  <strong>{battery.name}</strong>
                  <span>{battery.label} · {battery.capacityRange}</span>
                </button>
                <button
                  type="button"
                  className="icon-button"
                  title="放大查看曲线详情"
                  onClick={() => setDetailBatteryId(battery.id)}
                >
                  ⤢
                </button>
              </article>
            ))}
          </div>

          <form className="chat-composer" onSubmit={handleAsk}>
            <textarea
              className="chat-input"
              rows={2}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              disabled={!inviteUnlocked || pending}
              placeholder={
                inviteUnlocked
                  ? '输入你要分析的问题，或点击上方示例数据'
                  : '请输入邀请码后再发起诊断'
              }
            />
            <button className="send-button" type="submit" disabled={!inviteUnlocked || pending}>
              {pending ? '■' : '发送'}
            </button>
          </form>
        </div>
      </section>

      {detailBattery && (
        <div className="modal-backdrop" onClick={() => setDetailBatteryId(null)}>
          <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
            <div className="panel-header">
              <div>
                <div className="section-kicker">曲线详情</div>
                <h2>{detailBattery.name}</h2>
              </div>
              <button className="button secondary" type="button" onClick={() => setDetailBatteryId(null)}>
                关闭
              </button>
            </div>
            <ChargeChart
              battery={detailBattery}
              process={
                detailBattery.processes.find((item) => item.processId === detailBattery.highlightedProcessId)
                  || detailBattery.processes[0]
              }
            />
          </div>
        </div>
      )}
    </div>
  )
}
