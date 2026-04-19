import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { AdminLoginPage } from './AdminLoginPage'

describe('AdminLoginPage', () => {
  beforeEach(() => {
    window.sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('navigates into admin after a successful login', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          access_token: 'admin-session-token',
          admin_username: 'admin',
        }),
      })),
    )

    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <Routes>
          <Route path="/admin/login" element={<AdminLoginPage />} />
          <Route path="/admin" element={<h1>后台概览</h1>} />
        </Routes>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: '登录后台' }))

    await waitFor(() => expect(screen.getByRole('heading', { name: '后台概览' })).toBeInTheDocument())
    expect(window.sessionStorage.getItem('chargellm.demo.admin-token')).toBe('admin-session-token')
  })
})
