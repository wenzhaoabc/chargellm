import { getInviteSessionToken, startInviteSession } from './auth'
import { API_BASE, ApiError } from './client'
import type { ChatCompletionMessage, ChatEvent, ChatRequest, DiagnosisResult } from './types'

type ChatHandlers = {
  onEvent?: (event: ChatEvent) => void
  onFinal?: (result: DiagnosisResult) => void
  onError?: (message: string) => void
}

const TOKEN_CHUNK_SIZE = 8
const TOKEN_RENDER_DELAY_MS = 16

function mapFinalResult(payload: Record<string, unknown>): DiagnosisResult {
  return {
    label: String(payload.label || '未知'),
    capacityRange: String(payload.capacityRange || payload.capacity_range || '未知'),
    confidence: Number(payload.confidence || 0),
    reason: String(payload.reason || ''),
    keyProcesses: Array.isArray(payload.keyProcesses)
      ? payload.keyProcesses.map(String)
      : Array.isArray(payload.key_processes)
        ? payload.key_processes.map(String)
        : [],
  }
}

function normalizeEvent(type: string, payload: Record<string, unknown>): ChatEvent | null {
  if (type === 'done') {
    return null
  }
  if (type === 'final') {
    return {
      type: 'final',
      message: '诊断完成',
      payload: mapFinalResult(payload) as unknown as Record<string, unknown>,
    }
  }
  return {
    type: type as ChatEvent['type'],
    message: String(payload.message || payload.text || payload.reason || ''),
    payload,
  }
}

function normalizeOpenAIChunk(payload: Record<string, unknown>): ChatEvent | null {
  if (payload.error && typeof payload.error === 'object') {
    const error = payload.error as Record<string, unknown>
    return { type: 'error', message: String(error.message || '模型调用失败'), payload: error }
  }
  const choices = payload.choices
  if (!Array.isArray(choices) || choices.length === 0) {
    return null
  }
  const choice = choices[0] as Record<string, unknown>
  const delta = (choice.delta || {}) as Record<string, unknown>
  if (delta.tool_calls) {
    return { type: 'tool', message: '工具调用更新', payload: delta }
  }
  const content = delta.content
  if (typeof content === 'string' && content) {
    return { type: 'token', message: content, payload: { text: content } }
  }
  return null
}

function tryParseStructuredAnswer(text: string): { answer: string; payload?: Record<string, unknown> } | null {
  const trimmed = text.trim()
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
    return null
  }
  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>
    if (typeof parsed.answer === 'string' && parsed.answer.trim()) {
      return { answer: parsed.answer, payload: parsed }
    }
  } catch {
    return null
  }
  return null
}

function normalizeVisibleAnswer(text: string) {
  return tryParseStructuredAnswer(text)?.answer || text
}

function normalizeStreamingVisibleAnswer(text: string) {
  const trimmed = text.trimStart()
  if (trimmed.startsWith('{')) {
    const structured = tryParseStructuredAnswer(text)
    return structured?.answer || ''
  }
  return text
}

function waitForVisibleFrame() {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, TOKEN_RENDER_DELAY_MS)
  })
}

async function emitEvent(event: ChatEvent, handlers: ChatHandlers) {
  if (event.type === 'token' && event.message.length > TOKEN_CHUNK_SIZE) {
    for (let index = 0; index < event.message.length; index += TOKEN_CHUNK_SIZE) {
      const message = event.message.slice(index, index + TOKEN_CHUNK_SIZE)
      handlers.onEvent?.({
        ...event,
        message,
        payload: { ...(event.payload || {}), text: message },
      })
      await waitForVisibleFrame()
    }
    return
  }
  handlers.onEvent?.(event)
  if (event.type === 'final') {
    handlers.onFinal?.(event.payload as unknown as DiagnosisResult)
  }
  await waitForVisibleFrame()
}

export async function consumeSseStream(stream: ReadableStream<Uint8Array>, handlers: ChatHandlers) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let openAiContent = ''
  let emittedOpenAiText = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffer += decoder.decode(value, { stream: true })
    let splitIndex = buffer.indexOf('\n\n')
    while (splitIndex >= 0) {
      const chunk = buffer.slice(0, splitIndex)
      buffer = buffer.slice(splitIndex + 2)
      const lines = chunk.split('\n')
      const typeLine = lines.find((line) => line.startsWith('event: '))
      const dataLine = lines.find((line) => line.startsWith('data: '))
      if (dataLine) {
        const data = dataLine.slice(6).trim()
        if (data === '[DONE]') {
          return
        }
        const payload = JSON.parse(data) as Record<string, unknown>
        const event = typeLine ? normalizeEvent(typeLine.slice(7).trim(), payload) : normalizeOpenAIChunk(payload)
        if (event) {
          if (!typeLine && event.type === 'token') {
            openAiContent += event.message
            const visibleText = normalizeStreamingVisibleAnswer(openAiContent)
            const delta = visibleText.slice(emittedOpenAiText.length)
            if (delta) {
              emittedOpenAiText = visibleText
              await emitEvent({ ...event, message: delta, payload: { ...(event.payload || {}), text: delta } }, handlers)
            }
          } else {
            await emitEvent(event, handlers)
          }
        }
      }
      splitIndex = buffer.indexOf('\n\n')
    }
  }
}

async function ensureSessionToken(inviteCode: string) {
  const existingToken = getInviteSessionToken()
  if (existingToken) {
    return existingToken
  }
  const session = await startInviteSession(inviteCode)
  return session.session_token
}

function mapExampleKey(batteryId: string) {
  if (batteryId.includes('aging')) {
    return 'aging_001'
  }
  if (batteryId.includes('fault')) {
    return 'fault_001'
  }
  return 'normal_001'
}

function defaultMessages(question: string): ChatCompletionMessage[] {
  return [{ role: 'user', content: question }]
}

export async function runChatStream(request: ChatRequest, handlers: ChatHandlers) {
  const sessionToken = await ensureSessionToken(request.inviteCode)
  const response = await fetch(`${API_BASE}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${sessionToken}`,
    },
    signal: request.signal,
    body: JSON.stringify({
      stream: true,
      messages: request.messages || defaultMessages(request.question),
      metadata: {
        dataset_id: request.datasetId,
        example_key: mapExampleKey(request.batteryId),
      },
    }),
  })

  if (!response.ok || !response.body) {
    throw new ApiError(response.status, (await response.text()) || response.statusText)
  }

  await consumeSseStream(response.body, handlers)
}
