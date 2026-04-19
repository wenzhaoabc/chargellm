import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { LandingPage } from './LandingPage'

describe('LandingPage', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('introduces the product before asking for an invite code', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { name: '电动自行车电池健康诊断大模型' })).toBeInTheDocument()
    expect(screen.getByText(/基于海量专家标注数据/)).toBeInTheDocument()
    expect(screen.getByText('联系团队获取试用邀请码')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('请输入管理员分配的邀请码')).not.toBeInTheDocument()
    const experienceButtons = screen.getAllByRole('button', { name: '立即体验' })
    expect(experienceButtons).toHaveLength(1)
    await user.click(experienceButtons[0])
    expect(screen.getByRole('group', { name: '邀请码体验入口' })).toBeInTheDocument()
    expect(screen.getByPlaceholderText('请输入管理员分配的邀请码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '解锁体验' })).toBeInTheDocument()
    await user.click(experienceButtons[0])
    expect(screen.queryByPlaceholderText('请输入管理员分配的邀请码')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '技术原理' })).toBeInTheDocument()
    expect(screen.getByText('以海量专家诊断样本训练电池健康识别能力，沉淀老化、故障和异常充电知识。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '模型运作架构' })).toBeInTheDocument()
    expect(screen.getByText('充电历史数据')).toBeInTheDocument()
    expect(screen.getByText('诊断结论')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '核心能力' })).toBeInTheDocument()
    expect(screen.getByText('老化趋势识别')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '应用场景' })).toBeInTheDocument()
    expect(screen.getByText('政府监管单位')).toBeInTheDocument()
    expect(screen.getByText('充电桩运营商')).toBeInTheDocument()
    expect(screen.getByText('个人用户')).toBeInTheDocument()
  })

  it('navigates to chat after a valid invite code is confirmed', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          invite_code: 'PUBLIC-DEMO-001',
          session_token: 'public-session-token',
          usage_limit: 50,
          usage_count: 0,
          per_user_quota: 10,
        }),
      })),
    )

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/chat" element={<h1>电池诊断对话</h1>} />
        </Routes>
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: '立即体验' }))
    await user.type(screen.getByPlaceholderText('请输入管理员分配的邀请码'), 'PUBLIC-DEMO-001')
    await user.click(screen.getByRole('button', { name: '解锁体验' }))

    await waitFor(() => expect(screen.getByRole('heading', { name: '电池诊断对话' })).toBeInTheDocument())
    expect(window.sessionStorage.getItem('chargellm.demo.invite-session-token')).toBe('public-session-token')
  })

  it('shows a clear error when the invite code is rejected', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ detail: 'invite_not_found' }),
      })),
    )

    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: '立即体验' }))
    await user.type(screen.getByPlaceholderText('请输入管理员分配的邀请码'), 'WRONG-CODE')
    await user.click(screen.getByRole('button', { name: '解锁体验' }))

    expect(await screen.findByText('邀请码不存在或已停用，请核对后重新输入。')).toBeInTheDocument()
  })
})
