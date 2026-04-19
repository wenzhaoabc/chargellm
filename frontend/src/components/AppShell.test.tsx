import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './AppShell'

describe('AppShell', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('renders a focused ChatGPT-like conversation shell with history only', async () => {
    const user = userEvent.setup()
    const opened: string[] = []
    const created: string[] = []
    window.localStorage.setItem(
      'chargellm.demo.conversation-history',
      JSON.stringify([
        {
          id: 'conversation-1',
          title: '政府抽检样本诊断',
          createdAt: '2026-04-18 20:00',
          updatedAt: '2026-04-18 20:00',
          turns: [],
        },
      ]),
    )
    window.addEventListener('chargellm.demo.open-conversation', (event) => {
      opened.push((event as CustomEvent<{ conversationId: string }>).detail.conversationId)
    })
    window.addEventListener('chargellm.demo.new-conversation', () => {
      created.push('new')
    })

    render(
      <MemoryRouter initialEntries={['/chat']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/chat" element={<div>workspace</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByRole('button', { name: /新建对话/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /搜索对话/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '真实记录' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '诊断历史' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /政府抽检样本诊断/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: '管理员' })).not.toBeInTheDocument()
    expect(screen.getByText('电池健康诊断 AI')).toBeInTheDocument()
    expect(screen.getByText('workspace')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /政府抽检样本诊断/ }))
    expect(opened).toEqual(['conversation-1'])
    await user.click(screen.getByRole('button', { name: /新建对话/ }))
    expect(created).toEqual(['new'])
  })
})
