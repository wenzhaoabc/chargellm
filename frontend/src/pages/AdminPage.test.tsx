import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AdminPage } from './AdminPage'

const apiMocks = vi.hoisted(() => ({
  createAdminInvite: vi.fn(),
  deleteAdminInvite: vi.fn(),
  updateAdminInvite: vi.fn(),
  createAdminDataset: vi.fn(),
  updateAdminDataset: vi.fn(),
  deleteAdminDataset: vi.fn(),
  importAdminDatasetFromMysql: vi.fn(),
}))

vi.mock('@/api/admin', () => ({
  getAdminToken: () => 'admin-token',
  listAdminInvites: vi.fn(async () => [
    {
      id: 1,
      code: 'PUBLIC-BETA-001',
      name: '公开体验码',
      usageLimit: 20,
      usageCount: 3,
      perUserQuota: 10,
      status: 'active',
      expiresAt: '长期',
    },
  ]),
  createAdminInvite: apiMocks.createAdminInvite,
  updateAdminInvite: apiMocks.updateAdminInvite,
  deleteAdminInvite: apiMocks.deleteAdminInvite,
  listAdminDatasets: vi.fn(async () => [
    {
      id: 'dataset-1',
      datasetId: 1,
      sampleKey: 'gov-risk-001',
      name: '政府抽检高风险样本',
      status: 'aging',
      label: '异常衰减',
      capacityRange: '60-80%',
      shortSummary: '来自抽检数据的脱敏演示样本',
      longSummary: '来自抽检数据的脱敏演示样本',
      processCount: 1,
      highlightedProcessId: 'gov-risk-001-p1',
      source: 'demo_case',
      isActive: true,
      sortOrder: 1,
      processes: [
        {
          processId: 'gov-risk-001-p1',
          title: '脱敏充电过程',
          timeOffsetMin: [0, 10],
          voltage: [46.1, 47.0],
          current: [10.0, 9.6],
          power: [461, 451],
        },
      ],
    },
  ]),
  createAdminDataset: apiMocks.createAdminDataset,
  updateAdminDataset: apiMocks.updateAdminDataset,
  deleteAdminDataset: apiMocks.deleteAdminDataset,
  importAdminDatasetFromMysql: apiMocks.importAdminDatasetFromMysql,
  listAdminUsers: vi.fn(() => [
    {
      phone: '13800000000',
      nickname: '政府监管试用账号',
      role: 'user',
      inviteCode: 'PUBLIC-BETA-001',
      quotaUsed: 6,
      quotaTotal: 10,
      lastSeen: '2026-04-16 19:30',
    },
  ]),
  listAdminRuns: vi.fn(() => [
    {
      id: 'run-001',
      phone: '13800000000',
      batteryId: 'BAT-2026-001',
      label: '电池老化',
      capacityRange: [130, 180],
      status: 'success',
      createdAt: '2026-04-16 19:32',
    },
  ]),
}))

describe('AdminPage', () => {
  it('manages invite codes, call quotas, users and conversation history', async () => {
    const user = userEvent.setup()
    apiMocks.updateAdminInvite.mockResolvedValue({
      id: 1,
      code: 'PUBLIC-BETA-001',
      name: '政府监管试用码',
      usageLimit: 50,
      usageCount: 3,
      perUserQuota: 8,
      status: 'active',
      expiresAt: '长期',
    })
    apiMocks.createAdminDataset.mockResolvedValue({
      id: 'dataset-2',
      datasetId: 2,
      sampleKey: 'enterprise-001',
      name: '企业运营异常样本',
      status: 'fault',
      label: '充电异常',
      capacityRange: '40-60%',
      shortSummary: '运营侧脱敏样本',
      longSummary: '运营侧脱敏样本',
      processCount: 1,
      highlightedProcessId: 'enterprise-001-p1',
      source: 'demo_case',
      isActive: true,
      sortOrder: 2,
      processes: [],
    })

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('ChargeLLM Admin')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: '后台模块导航' })).toBeInTheDocument()
    expect(screen.getByRole('banner', { name: '后台顶部栏' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: '后台概览' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '邀请码管理' })).toBeInTheDocument()
    expect(screen.getByText('调用次数控制')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '用户与配额' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '用户历史对话记录' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: '演示数据管理' })).toBeInTheDocument()
    expect(screen.getByText('政府抽检高风险样本')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '从平台抽取数据' })).toBeInTheDocument()
    expect(screen.getByText('BAT-2026-001')).toBeInTheDocument()

    const inviteCard = screen.getByLabelText('邀请码 PUBLIC-BETA-001 管理')
    await user.clear(within(inviteCard).getByLabelText('PUBLIC-BETA-001 名称'))
    await user.type(within(inviteCard).getByLabelText('PUBLIC-BETA-001 名称'), '政府监管试用码')
    await user.clear(within(inviteCard).getByLabelText('PUBLIC-BETA-001 总调用次数'))
    await user.type(within(inviteCard).getByLabelText('PUBLIC-BETA-001 总调用次数'), '50')
    await user.clear(within(inviteCard).getByLabelText('PUBLIC-BETA-001 单用户调用次数'))
    await user.type(within(inviteCard).getByLabelText('PUBLIC-BETA-001 单用户调用次数'), '8')
    await user.click(within(inviteCard).getByRole('button', { name: '保存修改 PUBLIC-BETA-001' }))

    expect(apiMocks.updateAdminInvite).toHaveBeenCalledWith(1, {
      name: '政府监管试用码',
      max_uses: 50,
      per_user_quota: 8,
      is_active: true,
    })
    expect(await screen.findByText('邀请码已更新')).toBeInTheDocument()

    await user.clear(screen.getByLabelText('演示数据标题'))
    await user.type(screen.getByLabelText('演示数据标题'), '企业运营异常样本')
    fireEvent.change(
      screen.getByLabelText('演示数据内容'),
      {
        target: {
          value:
            '{"time_offset_min":[0,10],"voltage_series":[46.1,47.0],"current_series":[10,9.6],"power_series":[461,451]}',
        },
      },
    )
    await user.click(screen.getByRole('button', { name: '新增演示数据' }))

    expect(apiMocks.createAdminDataset).toHaveBeenCalledWith({
      title: '企业运营异常样本',
      problem_type: '待诊断',
      capacity_range: '待评估',
      description: '专业演示数据',
      sort_order: 0,
      is_active: true,
      file_name: 'dataset.json',
      content: expect.stringContaining('time_offset_min'),
    })
  })
})
