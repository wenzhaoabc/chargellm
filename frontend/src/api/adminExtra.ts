import { apiFetch } from './client'
import { getAdminToken } from './admin'

function adminHeaders() {
  return { Authorization: `Bearer ${getAdminToken()}` }
}

// -------- system prompts --------

export type SystemPrompt = {
  id: number
  scope: string
  title: string
  content: string
  is_active: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

export async function listSystemPrompts(): Promise<SystemPrompt[]> {
  return apiFetch('/admin/prompts', { headers: adminHeaders() })
}

export async function createSystemPrompt(payload: {
  scope?: string
  title: string
  content: string
  is_active?: boolean
  sort_order?: number
}): Promise<SystemPrompt> {
  return apiFetch('/admin/prompts', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
}

export async function updateSystemPrompt(id: number, payload: Partial<Omit<SystemPrompt, 'id' | 'created_at' | 'updated_at'>>) {
  return apiFetch<SystemPrompt>(`/admin/prompts/${id}`, {
    method: 'PATCH',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
}

export async function deleteSystemPrompt(id: number) {
  return apiFetch<{ status: string }>(`/admin/prompts/${id}`, {
    method: 'DELETE',
    headers: adminHeaders(),
  })
}

// -------- welcome --------

export type WelcomeMessage = {
  id: number
  title: string
  content: string
  sort_order: number
  is_active: boolean
}

export async function listWelcomeMessages(): Promise<WelcomeMessage[]> {
  return apiFetch('/admin/welcome', { headers: adminHeaders() })
}

export async function createWelcomeMessage(payload: { title: string; content: string; sort_order?: number; is_active?: boolean }) {
  return apiFetch<WelcomeMessage>('/admin/welcome', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
}

export async function updateWelcomeMessage(id: number, payload: Partial<Omit<WelcomeMessage, 'id'>>) {
  return apiFetch<WelcomeMessage>(`/admin/welcome/${id}`, {
    method: 'PATCH',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
}

export async function deleteWelcomeMessage(id: number) {
  return apiFetch<{ status: string }>(`/admin/welcome/${id}`, {
    method: 'DELETE',
    headers: adminHeaders(),
  })
}

// -------- users --------

export type AdminUser = {
  id: number
  phone: string | null
  phone_masked: string | null
  username: string | null
  role: string
  is_active: boolean
  usage_quota_total: number
  usage_quota_used: number
  created_at: string
}

export async function listAdminUsersBackend(params: { phone?: string; role?: string; limit?: number; offset?: number } = {}) {
  const qs = new URLSearchParams()
  if (params.phone) qs.set('phone', params.phone)
  if (params.role) qs.set('role', params.role)
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  if (params.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<{ items: AdminUser[]; total: number }>(`/admin/users${query}`, {
    headers: adminHeaders(),
  })
}

export async function updateAdminUser(id: number, payload: { is_active?: boolean; usage_quota_total?: number }) {
  return apiFetch<AdminUser>(`/admin/users/${id}`, {
    method: 'PATCH',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
}

// -------- conversations --------

export type AdminConversation = {
  id: number
  title: string
  created_at: string
  phone: string | null
  phone_masked: string | null
  user_id: number | null
  message_count: number
}

export async function listAdminConversations(params: { phone?: string; limit?: number; offset?: number } = {}) {
  const qs = new URLSearchParams()
  if (params.phone) qs.set('phone', params.phone)
  if (params.limit !== undefined) qs.set('limit', String(params.limit))
  if (params.offset !== undefined) qs.set('offset', String(params.offset))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiFetch<{ items: AdminConversation[]; total: number }>(`/admin/conversations${query}`, {
    headers: adminHeaders(),
  })
}

export type AdminConversationDetail = {
  id: number
  title: string
  created_at: string
  messages: Array<{
    id: number
    role: string
    content: string
    metadata: Record<string, unknown> | null
    created_at: string
  }>
}

export async function getAdminConversation(id: number) {
  return apiFetch<AdminConversationDetail>(`/admin/conversations/${id}`, {
    headers: adminHeaders(),
  })
}
