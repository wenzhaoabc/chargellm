import { afterEach, describe, expect, it, vi } from 'vitest'
import { getAdminToken, setAdminToken } from './admin'
import { getInviteSessionToken, startInviteSession } from './auth'

describe('temporary token storage', () => {
  afterEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('stores admin tokens in session storage only', () => {
    setAdminToken('admin-session-token')

    expect(getAdminToken()).toBe('admin-session-token')
    expect(window.sessionStorage.getItem('chargellm.demo.admin-token')).toBe('admin-session-token')
    expect(window.localStorage.getItem('chargellm.demo.admin-token')).toBeNull()
  })

  it('stores invite session tokens in session storage only', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          invite_code: 'PUBLIC-BETA-001',
          session_token: 'invite-session-token',
          quota_total: 10,
          quota_used: 1,
          quota_remaining: 9,
        }),
      })),
    )

    await startInviteSession('PUBLIC-BETA-001')

    expect(getInviteSessionToken()).toBe('invite-session-token')
    expect(window.sessionStorage.getItem('chargellm.demo.invite-session-token')).toBe('invite-session-token')
    expect(window.localStorage.getItem('chargellm.demo.invite-session-token')).toBeNull()
  })
})
