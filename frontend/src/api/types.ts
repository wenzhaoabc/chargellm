export type CapacityRange = string

export type BatteryStatus = 'normal' | 'aging' | 'fault' | 'nonstandard'

export interface ChargingProcess {
  processId: string
  title: string
  timeOffsetMin: number[]
  voltage: number[]
  current: number[]
  power: number[]
  note?: string
}

export interface BatteryExample {
  id: string
  datasetId?: number
  sampleKey?: string
  name: string
  status: BatteryStatus
  label: string
  capacityRange: CapacityRange
  shortSummary: string
  longSummary: string
  processCount: number
  highlightedProcessId: string
  source?: 'demo_case' | 'user_upload' | 'mysql_import'
  isActive?: boolean
  sortOrder?: number
  processes: ChargingProcess[]
}

export interface InviteState {
  code: string
  active: boolean
  usageLimit: number
  usageCount: number
}

export interface ChatRequest {
  batteryId: string
  datasetId?: number
  question: string
  inviteCode: string
  messages?: ChatCompletionMessage[]
  signal?: AbortSignal
}

export type ChatCompletionContentPart =
  | { type: 'text'; text: string }
  | { type: 'image_url'; image_url: { url: string } }
  | { type: string; [key: string]: unknown }

export interface ChatCompletionMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content?: string | ChatCompletionContentPart[] | null
  name?: string
  tool_call_id?: string
  tool_calls?: Record<string, unknown>[]
}

export type ChatEventType = 'status' | 'tool' | 'token' | 'final' | 'error'

export interface ChatEvent {
  type: ChatEventType
  message: string
  payload?: Record<string, unknown>
}

export interface DiagnosisResult {
  label: string
  capacityRange: CapacityRange
  confidence: number
  reason: string
  keyProcesses: string[]
}

export interface AdminInviteRow {
  id: number
  code: string
  name: string
  usageLimit: number
  usageCount: number
  perUserQuota: number
  status: 'active' | 'paused'
  expiresAt: string
}

export interface AdminUserRow {
  phone: string
  nickname: string
  role: 'user' | 'admin'
  inviteCode: string
  quotaUsed: number
  quotaTotal: number
  lastSeen: string
}

export interface AdminRunRow {
  id: string
  phone: string
  batteryId: string
  label: string
  capacityRange: CapacityRange | [number, number]
  status: 'success' | 'failed'
  createdAt: string
}
