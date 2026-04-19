import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import { ChatPage } from './ChatPage'

const datasetMocks = vi.hoisted(() => ({
  listDatasets: vi.fn(async () => [
    {
      id: 'dataset-1',
      datasetId: 1,
      sampleKey: 'gov-risk-001',
      name: '政府抽检高风险样本',
      status: 'aging',
      label: '异常衰减',
      capacityRange: '60-80%',
      shortSummary: '来自抽检数据的脱敏演示样本',
      longSummary: '来自真实抽检数据的脱敏曲线，用于展示模型对异常衰减趋势的识别能力。',
      processCount: 1,
      highlightedProcessId: 'gov-risk-001-p1',
      source: 'demo_case',
      processes: [
        {
          processId: 'gov-risk-001-p1',
          title: '脱敏充电过程',
          timeOffsetMin: [0, 10, 20],
          voltage: [46.1, 47.0, 47.5],
          current: [10.0, 9.6, 8.9],
          power: [461, 451, 423],
        },
      ],
    },
  ]),
  uploadDataset: vi.fn(async () => ({
    id: 'dataset-9',
    datasetId: 9,
    sampleKey: 'user-upload-001',
    name: 'field.csv',
    status: 'nonstandard',
    label: '用户导入数据',
    capacityRange: '未知',
    shortSummary: '客户侧自主导入的脱敏充电过程数据。',
    longSummary: '客户侧自主导入的脱敏充电过程数据。',
    processCount: 1,
    highlightedProcessId: 'user-upload-001-p1',
    source: 'user_upload',
    processes: [
      {
        processId: 'user-upload-001-p1',
        title: '导入充电过程',
        timeOffsetMin: [0, 5],
        voltage: [47.8, 48.4],
        current: [9.2, 8.8],
        power: [440, 426],
      },
    ],
  })),
}))

const chatMocks = vi.hoisted(() => ({
  runChatStream: vi.fn(async (_request, handlers) => {
    handlers.onEvent({ type: 'status', message: '已读取充电历史数据' })
    handlers.onEvent({ type: 'status', message: '正在调用多模态诊断大模型' })
    handlers.onEvent({ type: 'token', message: '模型判断该电池存在老化趋势。' })
    handlers.onFinal({
      label: '模型诊断老化',
      capacityRange: '55-70%',
      confidence: 0.91,
      reason: '模型发现充电末段异常。',
      keyProcesses: ['aging_001-p2'],
    })
  }),
}))

vi.mock('@/api/chat', () => ({
  runChatStream: chatMocks.runChatStream,
}))

vi.mock('@/api/datasets', () => ({
  listDatasets: datasetMocks.listDatasets,
  uploadDataset: datasetMocks.uploadDataset,
}))

describe('ChatPage', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
    vi.clearAllMocks()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn(async () => undefined),
      },
    })
  })

  it('renders a ChatGPT-like battery diagnosis conversation surface', async () => {
    render(<ChatPage />)

    expect(screen.getByRole('heading', { name: '电池健康诊断 AI 助手' })).toBeInTheDocument()
    expect(await screen.findByText('今天想分析哪组电池数据？')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /当前数据：政府抽检高风险样本/ })).toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: '专业数据源' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '添加图片或文件' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /发送/ })).toBeDisabled()
  })

  it('lets the user switch professional dataset context before asking', async () => {
    const user = userEvent.setup()
    render(<ChatPage />)

    await user.click(await screen.findByRole('button', { name: /当前数据：政府抽检高风险样本/ }))
    await user.click(await screen.findByRole('button', { name: /选择数据源：政府抽检高风险样本/ }))

    expect(screen.getByText('异常衰减')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '脱敏充电过程' })).toBeInTheDocument()
  })

  it('uploads customer CSV data as a selectable diagnosis context', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem('chargellm.demo.invite-code', 'DEMO-VLLM-001')
    window.sessionStorage.setItem('chargellm.demo.invite-session-token', 'demo-session')
    render(<ChatPage />)

    const file = new File(['time_offset_min,voltage,current,power\n0,47.8,9.2,440'], 'field.csv', {
      type: 'text/csv',
    })
    fireEvent.change(screen.getByLabelText('添加图片或文件', { selector: 'input' }), {
      target: { files: [file] },
    })

    await waitFor(() => expect(datasetMocks.uploadDataset).toHaveBeenCalledWith({
      sessionToken: 'demo-session',
      fileName: 'field.csv',
      name: 'field.csv',
      content: expect.stringContaining('time_offset_min'),
    }))
    await waitFor(() => expect(screen.getAllByText('field.csv').length).toBeGreaterThan(0))
  })

  it('renders model thinking like a collapsible ChatGPT process summary', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem('chargellm.demo.invite-code', 'DEMO-VLLM-001')
    window.sessionStorage.setItem('chargellm.demo.invite-session-token', 'demo-session')
    render(<ChatPage />)

    const input = screen.getByPlaceholderText('询问电池老化、故障、容量区间或异常充电过程')
    await user.clear(input)
    await user.type(input, '请结合真实充电数据判断是否老化')
    await user.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('模型判断该电池存在老化趋势。')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('已分析 2 项数据特征')).toBeInTheDocument())
    expect(screen.getByText('诊断摘要')).toBeInTheDocument()
    expect(screen.getByText('已读取充电历史数据')).toBeInTheDocument()
    expect(screen.queryByText('status')).not.toBeInTheDocument()
  })

  it('starts a new conversation while keeping the completed turn in history storage', async () => {
    const user = userEvent.setup()
    window.localStorage.setItem('chargellm.demo.invite-code', 'DEMO-VLLM-001')
    window.sessionStorage.setItem('chargellm.demo.invite-session-token', 'demo-session')
    render(<ChatPage />)

    const input = screen.getByPlaceholderText('询问电池老化、故障、容量区间或异常充电过程')
    await user.clear(input)
    await user.type(input, '请保存这次诊断对话')
    await user.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('模型诊断老化')).toBeInTheDocument()
    const history = JSON.parse(window.localStorage.getItem('chargellm.demo.conversation-history') || '[]')
    expect(history[0].turns[0].question).toBe('请保存这次诊断对话')
    expect(history[0].turns[0].diagnosis.label).toBe('模型诊断老化')

    await user.click(screen.getByRole('button', { name: '新建对话' }))

    expect(screen.queryByText('请保存这次诊断对话')).not.toBeInTheDocument()
    expect(screen.getByText('今天想分析哪组电池数据？')).toBeInTheDocument()
  })

  it('copies and retries completed assistant messages', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn(async () => undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText,
      },
    })
    window.localStorage.setItem('chargellm.demo.invite-code', 'DEMO-VLLM-001')
    window.sessionStorage.setItem('chargellm.demo.invite-session-token', 'demo-session')
    render(<ChatPage />)

    const input = screen.getByPlaceholderText('询问电池老化、故障、容量区间或异常充电过程')
    await user.clear(input)
    await user.type(input, '请重新检查这块电池')
    await user.click(screen.getByRole('button', { name: '发送' }))

    expect(await screen.findByText('模型判断该电池存在老化趋势。')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '复制回答' }))
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('模型判断该电池存在老化趋势。'))

    await user.click(screen.getByRole('button', { name: '重新生成' }))
    await waitFor(() => expect(chatMocks.runChatStream).toHaveBeenCalledTimes(2))
  })
})
