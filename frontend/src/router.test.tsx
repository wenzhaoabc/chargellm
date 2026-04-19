import { render, screen } from '@testing-library/react'
import { AppRouter } from './router'

function renderAt(path: string) {
  window.history.pushState({}, '', path)
  return render(<AppRouter />)
}

describe('AppRouter', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('uses the product landing page as the first entry route', async () => {
    renderAt('/')

    expect(await screen.findByRole('heading', { name: '电动自行车电池健康诊断大模型' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '立即体验' })).toHaveLength(1)
  })

  it('renders the chat workspace on /chat', async () => {
    renderAt('/chat')

    expect(await screen.findByRole('heading', { name: '电池健康诊断 AI 助手' })).toBeInTheDocument()
  })

  it('shows the admin login page first when /admin has no temporary token', async () => {
    renderAt('/admin')

    expect(await screen.findByRole('heading', { name: '输入管理员账号和密码' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '后台概览' })).not.toBeInTheDocument()
  })
})
