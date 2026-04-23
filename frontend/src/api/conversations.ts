import type { DiagnosisResult } from './types'

export const CONVERSATION_HISTORY_STORAGE_KEY = 'chargellm.demo.conversation-history'
export const ACTIVE_CONVERSATION_STORAGE_KEY = 'chargellm.demo.active-conversation'
export const CONVERSATION_HISTORY_CHANGED_EVENT = 'chargellm.demo.conversation-history-changed'
export const OPEN_CONVERSATION_EVENT = 'chargellm.demo.open-conversation'
export const NEW_CONVERSATION_EVENT = 'chargellm.demo.new-conversation'

export type ConversationTurnRecord = {
  id: string
  batteryId?: string
  question: string
  batteryName: string
  batteryLabel: string
  answer: string
  /** Optional structured diagnosis (legacy MVP). */
  diagnosis?: DiagnosisResult
}

export type ConversationRecord = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  turns: ConversationTurnRecord[]
  /** Backend ChatSession id, for /api/chat/title persistence + admin lookup. */
  chatSessionId?: number | null
}

export function createConversationId() {
  return `conversation-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function formatTime(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function listConversationHistory(): ConversationRecord[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(CONVERSATION_HISTORY_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function getConversationById(conversationId: string) {
  return listConversationHistory().find((record) => record.id === conversationId) || null
}

export function getActiveConversationId() {
  if (typeof window === 'undefined') return ''
  return window.localStorage.getItem(ACTIVE_CONVERSATION_STORAGE_KEY) || ''
}

export function setActiveConversationId(conversationId: string) {
  if (typeof window === 'undefined') return
  if (conversationId) {
    window.localStorage.setItem(ACTIVE_CONVERSATION_STORAGE_KEY, conversationId)
  } else {
    window.localStorage.removeItem(ACTIVE_CONVERSATION_STORAGE_KEY)
  }
}

export function notifyConversationHistoryChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(CONVERSATION_HISTORY_CHANGED_EVENT))
  }
}

function writeHistory(history: ConversationRecord[]) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(
    CONVERSATION_HISTORY_STORAGE_KEY,
    JSON.stringify(history.slice(0, 50)),
  )
  notifyConversationHistoryChanged()
}

export function appendConversationTurn(conversationId: string, turn: ConversationTurnRecord) {
  if (typeof window === 'undefined') return
  const now = formatTime(new Date())
  const history = listConversationHistory()
  const existing = history.find((record) => record.id === conversationId)
  const nextRecord: ConversationRecord = existing
    ? {
        ...existing,
        title: existing.title || turn.question,
        updatedAt: now,
        turns: [...existing.turns.filter((item) => item.id !== turn.id), turn],
      }
    : {
        id: conversationId,
        title: turn.question,
        createdAt: now,
        updatedAt: now,
        turns: [turn],
      }
  const nextHistory = [nextRecord, ...history.filter((record) => record.id !== conversationId)]
  writeHistory(nextHistory)
  setActiveConversationId(conversationId)
}

export function updateConversationTitle(conversationId: string, title: string) {
  const history = listConversationHistory()
  const existing = history.find((r) => r.id === conversationId)
  if (!existing) return
  const next = history.map((r) => (r.id === conversationId ? { ...r, title } : r))
  writeHistory(next)
}

export function setConversationChatSessionId(conversationId: string, chatSessionId: number) {
  const history = listConversationHistory()
  const existing = history.find((r) => r.id === conversationId)
  if (!existing) return
  if (existing.chatSessionId === chatSessionId) return
  const next = history.map((r) => (r.id === conversationId ? { ...r, chatSessionId } : r))
  writeHistory(next)
}

export function deleteConversation(conversationId: string) {
  const history = listConversationHistory()
  const next = history.filter((r) => r.id !== conversationId)
  writeHistory(next)
  if (getActiveConversationId() === conversationId) {
    setActiveConversationId('')
  }
}

export function renameConversation(conversationId: string, title: string) {
  updateConversationTitle(conversationId, title)
}

