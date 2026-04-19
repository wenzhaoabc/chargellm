import { render, screen } from '@testing-library/react'
import { HistoryPage } from './HistoryPage'

describe('HistoryPage', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('renders saved diagnosis conversations instead of static mock records', () => {
    window.localStorage.setItem(
      'chargellm.demo.conversation-history',
      JSON.stringify([
        {
          id: 'conversation-1',
          title: '请保存这次诊断对话',
          createdAt: '2026-04-18 20:00',
          turns: [
            {
              id: 'turn-1',
              question: '请保存这次诊断对话',
              batteryName: '政府抽检高风险样本',
              batteryLabel: '异常衰减',
              answer: '模型判断该电池存在老化趋势。',
              diagnosis: {
                label: '模型诊断老化',
                capacityRange: '55-70%',
                confidence: 0.91,
                reason: '模型发现充电末段异常。',
                keyProcesses: ['aging_001-p2'],
              },
            },
          ],
        },
      ]),
    )

    render(<HistoryPage />)

    expect(screen.getAllByText('请保存这次诊断对话').length).toBeGreaterThan(0)
    expect(screen.getByText('模型诊断老化')).toBeInTheDocument()
    expect(screen.queryByText('本地 mock 数据')).not.toBeInTheDocument()
  })
})
