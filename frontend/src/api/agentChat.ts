import { fetchEventSource } from '@microsoft/fetch-event-source'
import { API_BASE } from './client'
import { apiFetch } from './client'
import { getInviteSessionToken } from './auth'

export type AgentChatMessage = {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
}

export type AgentEvent =
  | { type: 'token'; text: string }
  | { type: 'tool_call'; id: string; name: string; arguments: string }
  | {
      type: 'tool_result'
      id: string
      name: string
      display: string
      data: Record<string, unknown>
      is_error: boolean
    }
  | { type: 'safety'; stage: 'input' | 'output'; reason: string; label?: string }
  | { type: 'status'; message: string; chat_session_id?: number }
  | { type: 'error'; message: string; errorType?: string }
  | { type: 'done'; status: 'ok' | 'blocked' | 'failed' | 'max_iters' }

export type AgentStreamHandlers = {
  onEvent?: (event: AgentEvent) => void
  onError?: (error: Error) => void
}

export type AgentStreamRequest = {
  messages: AgentChatMessage[]
  user_phone?: string
  system_prompt?: string
  signal?: AbortSignal
}

class FatalError extends Error {}

export async function streamAgentChat(req: AgentStreamRequest, handlers: AgentStreamHandlers) {
  const sessionToken = getInviteSessionToken()
  if (!sessionToken) {
    throw new Error('missing_session_token')
  }
  await fetchEventSource(`${API_BASE}/chat/agent/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${sessionToken}`,
    },
    body: JSON.stringify({
      messages: req.messages,
      user_phone: req.user_phone,
      system_prompt: req.system_prompt,
    }),
    signal: req.signal,
    openWhenHidden: true,
    async onopen(response) {
      if (!response.ok) {
        const text = await response.text()
        throw new FatalError(text || response.statusText)
      }
    },
    onmessage(msg) {
      if (!msg.event) return
      let payload: Record<string, unknown> = {}
      try {
        payload = msg.data ? JSON.parse(msg.data) : {}
      } catch {
        return
      }
      const evt = normalizeEvent(msg.event, payload)
      if (evt) handlers.onEvent?.(evt)
    },
    onerror(err) {
      handlers.onError?.(err instanceof Error ? err : new Error(String(err)))
      if (err instanceof FatalError) throw err
    },
  })
}

function normalizeEvent(name: string, data: Record<string, unknown>): AgentEvent | null {
  switch (name) {
    case 'token':
      return { type: 'token', text: String(data.text || '') }
    case 'tool_call':
      return {
        type: 'tool_call',
        id: String(data.id || ''),
        name: String(data.name || ''),
        arguments: String(data.arguments || ''),
      }
    case 'tool_result':
      return {
        type: 'tool_result',
        id: String(data.id || ''),
        name: String(data.name || ''),
        display: String(data.display || ''),
        data: (data.data as Record<string, unknown>) || {},
        is_error: Boolean(data.is_error),
      }
    case 'safety':
      return {
        type: 'safety',
        stage: (data.stage as 'input' | 'output') || 'output',
        reason: String(data.reason || ''),
        label: data.label ? String(data.label) : undefined,
      }
    case 'status':
      return {
        type: 'status',
        message: String(data.message || ''),
        chat_session_id: typeof data.chat_session_id === 'number' ? data.chat_session_id : undefined,
      }
    case 'error':
      return {
        type: 'error',
        message: String(data.message || ''),
        errorType: data.type ? String(data.type) : undefined,
      }
    case 'done':
      return { type: 'done', status: (data.status as 'ok' | 'blocked' | 'failed' | 'max_iters') || 'ok' }
    default:
      return null
  }
}

export async function generateChatTitle(payload: {
  user_message: string
  assistant_message: string
  chat_session_id?: number | null
}): Promise<string> {
  const token = getInviteSessionToken()
  const resp = await apiFetch<{ title: string }>('/chat/title', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify(payload),
  })
  return resp.title
}
