import type { FormEvent } from 'react'
import { useEffect, useRef, useState } from 'react'
import { ChargeChart } from '@/components/ChargeChart'
import { getInviteCode, getInviteSessionToken, hasInviteAccess } from '@/api/auth'
import { runChatStream } from '@/api/chat'
import {
  NEW_CONVERSATION_EVENT,
  OPEN_CONVERSATION_EVENT,
  appendConversationTurn,
  createConversationId,
  getActiveConversationId,
  getConversationById,
  notifyConversationHistoryChanged,
  setActiveConversationId,
  type ConversationRecord,
  type ConversationTurnRecord,
} from '@/api/conversations'
import { listDatasets, uploadDataset } from '@/api/datasets'
import type { BatteryExample, ChatCompletionMessage, ChatEvent, DiagnosisResult } from '@/api/types'

type ChatTurn = {
  id: string
  question: string
  battery: BatteryExample
  events: ChatEvent[]
  result: DiagnosisResult | null
  pending: boolean
}

const promptChips = ['这份数据反映了什么健康风险？', '哪些充电过程最值得复核？', '请给出面向监管或运营的诊断摘要']

async function readFileContent(file: File): Promise<string> {
  if (typeof file.text === 'function') {
    return file.text()
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ''))
    reader.onerror = () => reject(reader.error ?? new Error('file_read_failed'))
    reader.readAsText(file)
  })
}

function getAssistantText(turn: ChatTurn) {
  return turn.events
    .filter((event) => event.type === 'token')
    .map((event) => event.message)
    .join('')
}

function tryParseStructuredAnswer(text: string): { answer: string; diagnosis?: Partial<DiagnosisResult> } | null {
  const trimmed = text.trim()
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
    return null
  }
  try {
    const parsed = JSON.parse(trimmed) as {
      answer?: unknown
      diagnosis?: {
        label?: unknown
        capacity_range?: unknown
        capacityRange?: unknown
        confidence?: unknown
        reason?: unknown
        key_processes?: unknown
        keyProcesses?: unknown
      }
    }
    if (typeof parsed.answer !== 'string' || !parsed.answer.trim()) {
      return null
    }
    const diagnosis = parsed.diagnosis
    return {
      answer: parsed.answer,
      diagnosis: diagnosis
        ? {
            label: typeof diagnosis.label === 'string' ? diagnosis.label : undefined,
            capacityRange:
              typeof diagnosis.capacityRange === 'string'
                ? diagnosis.capacityRange
                : typeof diagnosis.capacity_range === 'string'
                  ? diagnosis.capacity_range
                  : undefined,
            confidence: typeof diagnosis.confidence === 'number' ? diagnosis.confidence : undefined,
            reason: typeof diagnosis.reason === 'string' ? diagnosis.reason : undefined,
            keyProcesses: Array.isArray(diagnosis.keyProcesses)
              ? diagnosis.keyProcesses.map(String)
              : Array.isArray(diagnosis.key_processes)
                ? diagnosis.key_processes.map(String)
                : undefined,
          }
        : undefined,
    }
  } catch {
    return null
  }
}

function normalizeAssistantText(text: string) {
  return tryParseStructuredAnswer(text)?.answer || text
}

function buildConversationMessages(turns: ChatTurn[], nextQuestion: string): ChatCompletionMessage[] {
  const messages: ChatCompletionMessage[] = []
  for (const turn of turns) {
    messages.push({ role: 'user', content: turn.question })
    const answer = getAssistantText(turn)
    if (answer) {
      messages.push({ role: 'assistant', content: answer })
    }
  }
  messages.push({ role: 'user', content: [{ type: 'text', text: nextQuestion }] })
  return messages
}

function fallbackDiagnosis(battery: BatteryExample, answer: string): DiagnosisResult {
  const structured = tryParseStructuredAnswer(answer)
  if (structured?.diagnosis) {
    return {
      label: structured.diagnosis.label || battery.label,
      capacityRange: structured.diagnosis.capacityRange || battery.capacityRange,
      confidence: structured.diagnosis.confidence ?? 0,
      reason: structured.diagnosis.reason || structured.answer,
      keyProcesses: structured.diagnosis.keyProcesses || (battery.highlightedProcessId ? [battery.highlightedProcessId] : []),
    }
  }
  return {
    label: battery.label,
    capacityRange: battery.capacityRange,
    confidence: 0,
    reason: normalizeAssistantText(answer) || battery.shortSummary,
    keyProcesses: battery.highlightedProcessId ? [battery.highlightedProcessId] : [],
  }
}

function conversationToTurns(conversation: ConversationRecord): ChatTurn[] {
  return conversation.turns.map((turn) => ({
    id: turn.id,
    question: turn.question,
    battery: {
      id: turn.batteryId || turn.batteryName,
      name: turn.batteryName,
      status: 'normal',
      label: turn.batteryLabel,
      capacityRange: turn.diagnosis.capacityRange,
      shortSummary: turn.diagnosis.reason,
      longSummary: turn.diagnosis.reason,
      processCount: turn.diagnosis.keyProcesses.length,
      highlightedProcessId: turn.diagnosis.keyProcesses[0] || '',
      processes: [],
    },
    events: turn.answer ? [{ type: 'token', message: turn.answer }] : [],
    result: turn.diagnosis,
    pending: false,
  }))
}

async function copyText(text: string) {
  await navigator.clipboard?.writeText(text)
}

function AssistantMessage({
  turn,
  onCopy,
  onRetry,
}: {
  turn: ChatTurn
  onCopy: () => void
  onRetry: () => void
}) {
  const streamedText = getAssistantText(turn)
  const visibleText = normalizeAssistantText(streamedText)
  const diagnosisReason = turn.result?.reason ? normalizeAssistantText(turn.result.reason) : ''
  const shouldShowDiagnosisReason = Boolean(diagnosisReason && diagnosisReason !== visibleText)
  const thoughtEvents = turn.events.filter((event) => event.type !== 'token' && event.type !== 'final')
  const thoughtSummary = turn.pending ? '正在分析数据特征' : `已分析 ${thoughtEvents.length} 项数据特征`

  return (
    <article className="message-row assistant-row">
      <div className="avatar assistant-avatar">AI</div>
      <div className="message-stack">
        {thoughtEvents.length > 0 ? (
          <details className="tool-trace thinking-trace" open={turn.pending}>
            <summary>{thoughtSummary}</summary>
            <div className="stream-list">
              {thoughtEvents.map((event, index) => (
                <div key={`${event.type}-${index}`} className={`stream-row ${event.type === 'error' ? 'error' : ''}`}>
                  <span className="thought-dot" aria-hidden="true" />
                  <p>{event.message}</p>
                </div>
              ))}
            </div>
          </details>
        ) : null}

        <div className="assistant-bubble">
          <p>{visibleText || (turn.pending ? '正在读取充电过程并生成诊断...' : '诊断已完成。')}</p>
        </div>

        {turn.result ? (
          <details className="diagnosis-card" open>
            <summary>
              <span>诊断摘要</span>
              <strong>{turn.result.label}</strong>
            </summary>
            <div className="diagnosis-grid">
              <div className="metric-row">
                <span>容量区间</span>
                <strong>{turn.result.capacityRange}</strong>
              </div>
              <div className="metric-row">
                <span>置信度</span>
                <strong>{Math.round(turn.result.confidence * 100)}%</strong>
              </div>
            </div>
            {shouldShowDiagnosisReason ? <p>{diagnosisReason}</p> : null}
            <div className="tag-row">
              {turn.result.keyProcesses.map((processId) => (
                <span key={processId}>{processId}</span>
              ))}
            </div>
          </details>
        ) : null}

        {!turn.pending && visibleText ? (
          <div className="message-actions" aria-label="回答操作">
            <button type="button" onClick={onCopy}>
              复制回答
            </button>
            <button type="button" onClick={onRetry}>
              重新生成
            </button>
          </div>
        ) : null}
      </div>
    </article>
  )
}

function DatasetButton({
  battery,
  active,
  onSelect,
}: {
  battery: BatteryExample
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      className={`battery-option${active ? ' active' : ''}`}
      type="button"
      aria-label={`选择数据源：${battery.name}`}
      onClick={onSelect}
    >
      <span>{battery.name}</span>
      <strong>{battery.label}</strong>
      <small>{battery.capacityRange} · {battery.source === 'user_upload' ? '我的导入数据' : '专业案例库'}</small>
    </button>
  )
}

function DataContextPanel({
  datasets,
  selectedBattery,
  selectedProcess,
  selectedProcessId,
  datasetError,
  onSelectDataset,
  onSelectProcess,
}: {
  datasets: BatteryExample[]
  selectedBattery?: BatteryExample
  selectedProcess?: BatteryExample['processes'][number]
  selectedProcessId: string
  datasetError: string
  onSelectDataset: (battery: BatteryExample) => void
  onSelectProcess: (processId: string) => void
}) {
  return (
    <div className="data-context-panel" role="region" aria-label="数据上下文">
      <div className="data-context-panel-header">
        <div>
          <span className="eyebrow">数据上下文</span>
          <h2>{selectedBattery?.name ?? '等待数据'}</h2>
        </div>
        <span>{selectedBattery?.source === 'user_upload' ? '我的导入数据' : '专业案例库'}</span>
      </div>
      <p>{selectedBattery?.longSummary ?? '输入邀请码后可以读取专业案例库，也可以导入 CSV 或 JSON 数据。'}</p>
      {datasetError ? <div className="inline-info">{datasetError}</div> : null}

      <div className="battery-list compact">
        {datasets.map((battery) => (
          <DatasetButton
            key={battery.id}
            battery={battery}
            active={battery.id === selectedBattery?.id}
            onSelect={() => onSelectDataset(battery)}
          />
        ))}
      </div>

      {selectedBattery && selectedProcess ? (
        <div className="data-evidence-card">
          <div className="section-header">
            <div>
              <span className="eyebrow">分析依据</span>
              <h3>{selectedProcess.title}</h3>
            </div>
            <select value={selectedProcessId} onChange={(event) => onSelectProcess(event.target.value)}>
              {selectedBattery.processes.map((process) => (
                <option key={process.processId} value={process.processId}>
                  {process.title}
                </option>
              ))}
            </select>
          </div>
          <ChargeChart battery={selectedBattery} process={selectedProcess} />
        </div>
      ) : null}
    </div>
  )
}

export function ChatPage() {
  const [datasets, setDatasets] = useState<BatteryExample[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const selectedBattery = datasets.find((dataset) => dataset.id === selectedDatasetId) ?? datasets[0]
  const [selectedProcessId, setSelectedProcessId] = useState('')
  const selectedProcess =
    selectedBattery?.processes.find((process) => process.processId === selectedProcessId) ?? selectedBattery?.processes[0]
  const [inviteCode] = useState(getInviteCode())
  const [question, setQuestion] = useState(promptChips[0])
  const [attachments, setAttachments] = useState<string[]>([])
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [conversationId, setConversationId] = useState(() => getActiveConversationId() || createConversationId())
  const [pending, setPending] = useState(false)
  const [datasetError, setDatasetError] = useState('')
  const [contextOpen, setContextOpen] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const inviteUnlocked = hasInviteAccess()
  const sessionToken = getInviteSessionToken()

  useEffect(() => {
    setActiveConversationId(conversationId)
    notifyConversationHistoryChanged()
  }, [conversationId])

  useEffect(() => {
    const openConversation = (event: Event) => {
      const conversationId = (event as CustomEvent<{ conversationId: string }>).detail?.conversationId
      if (!conversationId) {
        return
      }
      const conversation = getConversationById(conversationId)
      if (!conversation) {
        return
      }
      setConversationId(conversation.id)
      setTurns(conversationToTurns(conversation))
      setQuestion('')
      setAttachments([])
      setPending(false)
    }
    const newConversation = () => {
      handleNewConversation()
    }
    window.addEventListener(OPEN_CONVERSATION_EVENT, openConversation)
    window.addEventListener(NEW_CONVERSATION_EVENT, newConversation)
    const activeConversation = getConversationById(getActiveConversationId())
    if (activeConversation) {
      setConversationId(activeConversation.id)
      setTurns(conversationToTurns(activeConversation))
    }
    return () => {
      window.removeEventListener(OPEN_CONVERSATION_EVENT, openConversation)
      window.removeEventListener(NEW_CONVERSATION_EVENT, newConversation)
    }
  }, [])

  useEffect(() => {
    let active = true
    listDatasets(sessionToken)
      .then((items) => {
        if (!active) {
          return
        }
        setDatasets(items)
        if (items[0]) {
          setSelectedDatasetId(items[0].id)
          setSelectedProcessId(items[0].highlightedProcessId)
        }
      })
      .catch((error) => {
        if (active) {
          setDatasetError(error instanceof Error ? error.message : '数据读取失败')
        }
      })
    return () => {
      active = false
    }
  }, [sessionToken])

  const selectDataset = (battery: BatteryExample) => {
    setSelectedDatasetId(battery.id)
    setSelectedProcessId(battery.highlightedProcessId)
  }

  const handleUpload = async (files: FileList | null) => {
    const file = files?.[0]
    if (!file || !inviteUnlocked || !sessionToken) {
      return
    }
    setAttachments([file.name])
    try {
      const uploaded = await uploadDataset({
        sessionToken,
        name: file.name,
        fileName: file.name,
        content: await readFileContent(file),
      })
      setDatasets((current) => [uploaded, ...current])
      selectDataset(uploaded)
    } catch (error) {
      setDatasetError(error instanceof Error ? error.message : '数据导入失败')
    }
  }

  const handleNewConversation = () => {
    const nextConversationId = createConversationId()
    setTurns([])
    setQuestion(promptChips[0])
    setAttachments([])
    setPending(false)
    setConversationId(nextConversationId)
    setActiveConversationId(nextConversationId)
    notifyConversationHistoryChanged()
  }

  const runDiagnosisTurn = async (turnId: string, trimmedQuestion: string, battery: BatteryExample, replaceExisting: boolean) => {
    if (!inviteUnlocked || pending) {
      return
    }
    const streamedEvents: ChatEvent[] = []
    let completedResult: DiagnosisResult | null = null
    const historyTurns = replaceExisting ? turns.filter((turn) => turn.id !== turnId) : turns
    const abortController = new AbortController()
    abortControllerRef.current = abortController
    setPending(true)
    setActiveConversationId(conversationId)
    notifyConversationHistoryChanged()
    setTurns((current) => {
      const nextTurn: ChatTurn = {
        id: turnId,
        question: trimmedQuestion,
        battery,
        events: [],
        result: null,
        pending: true,
      }
      return replaceExisting ? current.map((turn) => (turn.id === turnId ? nextTurn : turn)) : [...current, nextTurn]
    })

    try {
      await runChatStream(
        {
          batteryId: battery.id,
          datasetId: battery.datasetId,
          inviteCode,
          question: trimmedQuestion,
          messages: buildConversationMessages(historyTurns, trimmedQuestion),
          signal: abortController.signal,
        },
        {
          onEvent: (chatEvent) => {
            streamedEvents.push(chatEvent)
            setTurns((current) =>
              current.map((turn) =>
                turn.id === turnId
                  ? {
                      ...turn,
                      events: [...turn.events, chatEvent],
                      result:
                        chatEvent.type === 'final' && chatEvent.payload
                          ? (chatEvent.payload as DiagnosisResult)
                          : turn.result,
                    }
                  : turn,
              ),
            )
          },
          onFinal: (diagnosis) => {
            completedResult = diagnosis
            setTurns((current) =>
              current.map((turn) => (turn.id === turnId ? { ...turn, result: diagnosis } : turn)),
            )
          },
          onError: (message) => {
            setTurns((current) =>
              current.map((turn) =>
                turn.id === turnId
                  ? { ...turn, events: [...turn.events, { type: 'error', message }], pending: false }
                  : turn,
              ),
            )
          },
        },
      )
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        const message = error instanceof Error ? error.message : '对话请求失败'
        setTurns((current) =>
          current.map((turn) =>
            turn.id === turnId ? { ...turn, events: [...turn.events, { type: 'error', message }], pending: false } : turn,
          ),
        )
      }
    } finally {
      const answer = streamedEvents
        .filter((chatEvent) => chatEvent.type === 'token')
        .map((chatEvent) => chatEvent.message)
        .join('')
      const visibleAnswer = normalizeAssistantText(answer)
      if (!completedResult && answer) {
        completedResult = fallbackDiagnosis(battery, answer)
        setTurns((current) => current.map((turn) => (turn.id === turnId ? { ...turn, result: completedResult } : turn)))
      }
      if (completedResult) {
        const record: ConversationTurnRecord = {
          id: turnId,
          batteryId: battery.id,
          question: trimmedQuestion,
          batteryName: battery.name,
          batteryLabel: battery.label,
          answer: visibleAnswer,
          diagnosis: completedResult,
        }
        appendConversationTurn(conversationId, record)
      }
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null
      }
      setPending(false)
      setQuestion('')
      setTurns((current) => current.map((turn) => (turn.id === turnId ? { ...turn, pending: false } : turn)))
    }
  }

  const handleAsk = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmedQuestion = question.trim()
    if (!selectedBattery || !trimmedQuestion || !inviteUnlocked || pending) {
      return
    }

    await runDiagnosisTurn(`${Date.now()}-${selectedBattery.id}`, trimmedQuestion, selectedBattery, false)
  }

  const handleRetry = async (turn: ChatTurn) => {
    if (pending) {
      return
    }
    await runDiagnosisTurn(turn.id, turn.question, turn.battery, true)
  }

  const handleStop = () => {
    abortControllerRef.current?.abort()
  }

  const handleCopy = async (turn: ChatTurn) => {
    const text = normalizeAssistantText(getAssistantText(turn)) || turn.result?.reason || ''
    if (text) {
      await copyText(text)
    }
  }

  return (
    <div className="chat-product">
      <section className="chat-main" aria-label="诊断对话">
        <header className="chat-header">
          <div>
            <span className="eyebrow">Battery Health AI</span>
            <h1>电池健康诊断 AI 助手</h1>
          </div>
          <div className="chat-header-actions">
            {pending ? (
              <button className="button secondary" type="button" onClick={handleStop}>
                停止生成
              </button>
            ) : null}
            <button className="button secondary" type="button" onClick={handleNewConversation} disabled={pending}>
              新建对话
            </button>
            <span className={`session-pill ${inviteUnlocked ? 'ready' : 'locked'}`}>
              {inviteUnlocked ? '已连接会话' : '等待邀请码'}
            </span>
          </div>
        </header>

        <div className="message-list">
          {turns.length === 0 ? (
            <div className="welcome-panel">
              <span className="eyebrow">专业电池健康诊断</span>
              <h2>今天想分析哪组电池数据？</h2>
              <p>选择已有专业案例或导入 CSV/JSON，然后像使用 ChatGPT 一样直接提问。</p>
              <div className="prompt-grid">
                {promptChips.map((chip) => (
                  <button key={chip} type="button" onClick={() => setQuestion(chip)}>
                    {chip}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            turns.map((turn) => (
              <div key={turn.id} className="turn-block">
                <article className="message-row user-row">
                  <div className="user-bubble">
                    <p>{turn.question}</p>
                    <span>
                      {turn.battery.name} · {turn.battery.label}
                    </span>
                  </div>
                  <div className="avatar user-avatar">你</div>
                </article>
                <AssistantMessage turn={turn} onCopy={() => void handleCopy(turn)} onRetry={() => void handleRetry(turn)} />
              </div>
            ))
          )}
        </div>

        <div className="composer">
          {!inviteUnlocked ? <div className="composer-hint">请先在产品介绍页输入邀请码，再进入诊断对话。</div> : null}
          <div className="context-strip">
            <button
              className="context-toggle"
              type="button"
              aria-expanded={contextOpen}
              onClick={() => setContextOpen((open) => !open)}
            >
              <span>当前数据：{selectedBattery?.name ?? '等待数据'}</span>
              <small>
                {selectedBattery
                  ? `${selectedBattery.label} · ${selectedBattery.source === 'user_upload' ? '我的导入数据' : '专业案例库'}`
                  : '邀请码通过后加载'}
              </small>
            </button>
          </div>
          {contextOpen ? (
            <DataContextPanel
              datasets={datasets}
              selectedBattery={selectedBattery}
              selectedProcess={selectedProcess}
              selectedProcessId={selectedProcess?.processId ?? selectedProcessId}
              datasetError={datasetError}
              onSelectDataset={selectDataset}
              onSelectProcess={setSelectedProcessId}
            />
          ) : null}
          <form className="composer-surface" onSubmit={handleAsk}>
            <label className="attach-button" role="button" aria-label="添加图片或文件" tabIndex={0}>
              <input
                aria-label="添加图片或文件"
                type="file"
                accept=".csv,.json"
                onChange={(event) => void handleUpload(event.target.files)}
              />
              <span>+</span>
            </label>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={inviteUnlocked ? '询问电池老化、故障、容量区间或异常充电过程' : '输入邀请码后开始诊断'}
              rows={2}
              disabled={!inviteUnlocked || pending}
            />
            <button type="submit" disabled={!inviteUnlocked || pending || !question.trim() || !selectedBattery}>
              {pending ? '分析中' : '发送'}
            </button>
          </form>
          {attachments.length > 0 ? (
            <div className="attachment-strip">
              {attachments.map((name) => (
                <span key={name}>{name}</span>
              ))}
            </div>
          ) : null}
        </div>
      </section>
    </div>
  )
}
