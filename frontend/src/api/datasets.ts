import { getInviteSessionToken } from './auth'
import { apiFetch } from './client'
import type { BatteryExample, BatteryStatus } from './types'

type DatasetApiRow = {
  id: number
  sample_key: string
  title: string
  problem_type: string
  capacity_range: string
  description: string
  source: 'demo_case' | 'user_upload' | 'mysql_import'
  is_active: boolean
  sort_order: number
  series: {
    time_offset_min: number[]
    voltage_series: number[]
    current_series: number[]
    power_series: number[]
  }
}

export type DatasetUploadPayload = {
  sessionToken: string
  name: string
  fileName: string
  content: string
}

function inferStatus(problemType: string): BatteryStatus {
  if (/故障|异常|风险/.test(problemType)) {
    return 'fault'
  }
  if (/老化|衰减/.test(problemType)) {
    return 'aging'
  }
  if (/正常/.test(problemType)) {
    return 'normal'
  }
  return 'nonstandard'
}

export function mapDataset(row: DatasetApiRow): BatteryExample {
  const processId = `${row.sample_key}-p1`
  return {
    id: `dataset-${row.id}`,
    datasetId: row.id,
    sampleKey: row.sample_key,
    name: row.title,
    status: inferStatus(row.problem_type),
    label: row.problem_type,
    capacityRange: row.capacity_range,
    shortSummary: row.description,
    longSummary: row.description,
    processCount: 1,
    highlightedProcessId: processId,
    source: row.source,
    isActive: row.is_active,
    sortOrder: row.sort_order,
    processes: [
      {
        processId,
        title: row.source === 'user_upload' ? '导入充电过程' : '脱敏充电过程',
        timeOffsetMin: row.series.time_offset_min,
        voltage: row.series.voltage_series,
        current: row.series.current_series,
        power: row.series.power_series,
        note: row.description,
      },
    ],
  }
}

export async function listDatasets(sessionToken = getInviteSessionToken()): Promise<BatteryExample[]> {
  if (!sessionToken) {
    return []
  }
  const response = await apiFetch<{ items: DatasetApiRow[] }>('/datasets', {
    headers: {
      Authorization: `Bearer ${sessionToken}`,
    },
  })
  return response.items.map(mapDataset)
}

export async function uploadDataset(payload: DatasetUploadPayload): Promise<BatteryExample> {
  const row = await apiFetch<DatasetApiRow>('/datasets/upload', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${payload.sessionToken}`,
    },
    body: JSON.stringify({
      name: payload.name,
      file_name: payload.fileName,
      content: payload.content,
    }),
  })
  return mapDataset(row)
}
