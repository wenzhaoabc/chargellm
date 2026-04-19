import { afterEach, describe, expect, it, vi } from 'vitest'
import { listDatasets, uploadDataset } from './datasets'

const datasetRow = {
  id: 1,
  sample_key: 'field-001',
  title: '现场样本',
  problem_type: '正常',
  capacity_range: '80-90%',
  description: '脱敏充电过程',
  source: 'user_upload',
  is_active: true,
  sort_order: 0,
  series: {
    time_offset_min: [0, 5],
    voltage_series: [48.2, 49.1],
    current_series: [8.1, 7.4],
    power_series: [390, 362],
  },
}

describe('datasets api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends demo session tokens through Authorization headers', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ items: [datasetRow] }),
    }))
    vi.stubGlobal('fetch', fetchMock)

    await listDatasets('demo-session-token')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/datasets',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer demo-session-token',
        }),
      }),
    )
    expect(fetchMock.mock.calls[0][0]).not.toContain('session_token')
  })

  it('does not include demo session tokens in dataset upload bodies', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => datasetRow,
    }))
    vi.stubGlobal('fetch', fetchMock)

    await uploadDataset({
      sessionToken: 'demo-session-token',
      name: '现场样本',
      fileName: 'sample.json',
      content: '{"voltage_series":[48.2]}',
    })

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers.Authorization).toBe('Bearer demo-session-token')
    expect(init.body).not.toContain('sessionToken')
    expect(init.body).not.toContain('session_token')
  })
})
