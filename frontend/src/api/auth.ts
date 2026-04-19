import { apiFetch } from './client'

const INVITE_STORAGE_KEY = 'chargellm.demo.invite-code'
const INVITE_SESSION_STORAGE_KEY = 'chargellm.demo.invite-session-token'

type InviteStartResponse = {
  invite_code: string
  session_token: string
  quota_total: number
  quota_used: number
  quota_remaining: number
}

export function getInviteCode(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.localStorage.getItem(INVITE_STORAGE_KEY) || ''
}

export function setInviteCode(code: string) {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(INVITE_STORAGE_KEY, code.trim())
}

export function getInviteSessionToken(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.sessionStorage.getItem(INVITE_SESSION_STORAGE_KEY) || ''
}

export function clearInviteSession() {
  if (typeof window === 'undefined') {
    return
  }
  window.sessionStorage.removeItem(INVITE_SESSION_STORAGE_KEY)
}

export async function startInviteSession(inviteCode: string): Promise<InviteStartResponse> {
  const response = await apiFetch<InviteStartResponse>('/auth/invite/start', {
    method: 'POST',
    body: JSON.stringify({ invite_code: inviteCode.trim() }),
  })
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(INVITE_STORAGE_KEY, response.invite_code)
    window.sessionStorage.setItem(INVITE_SESSION_STORAGE_KEY, response.session_token)
  }
  return response
}

export function hasInviteAccess() {
  return getInviteCode().trim().length > 0 && getInviteSessionToken().trim().length > 0
}
