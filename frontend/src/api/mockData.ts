import type {
  AdminInviteRow,
  AdminRunRow,
  AdminUserRow,
  BatteryExample,
  ChargingProcess,
  InviteState,
} from './types'

const timeAxis = (count: number, step = 5, start = 0) =>
  Array.from({ length: count }, (_, index) => start + index * step)

const buildSeries = (base: number, drift: number, wobble: number, count = 12) =>
  Array.from({ length: count }, (_, index) => {
    const local = Math.sin(index / 2.2) * wobble + Math.cos(index / 3.4) * wobble * 0.35
    return Number((base + drift * index + local).toFixed(2))
  })

const buildProcess = (
  processId: string,
  title: string,
  config: {
    offsetStart?: number
    voltageBase: number
    voltageDrift: number
    voltageWobble: number
    currentBase: number
    currentDrift: number
    currentWobble: number
    powerBase: number
    powerDrift: number
    powerWobble: number
    note?: string
  },
): ChargingProcess => {
  const pointCount = 12
  const offsetStart = config.offsetStart ?? 0
  return {
    processId,
    title,
    timeOffsetMin: timeAxis(pointCount, 5, offsetStart),
    voltage: buildSeries(config.voltageBase, config.voltageDrift, config.voltageWobble, pointCount),
    current: buildSeries(config.currentBase, config.currentDrift, config.currentWobble, pointCount),
    power: buildSeries(config.powerBase, config.powerDrift, config.powerWobble, pointCount),
    note: config.note,
  }
}

export const demoBatteries: BatteryExample[] = [
  {
    id: 'battery-normal-001',
    name: '示例电池 A',
    status: 'normal',
    label: '正常',
    capacityRange: '90-100%',
    shortSummary: '多次充电过程稳定，电压、电流、功率变化平滑。',
    longSummary: '该样本的充电过程连续稳定，曲线形态一致，适合作为正常参考样本。',
    processCount: 5,
    highlightedProcessId: 'p-a3',
    processes: [
      buildProcess('p-a1', '第 1 次充电', {
        offsetStart: 0,
        voltageBase: 3.7,
        voltageDrift: 0.02,
        voltageWobble: 0.03,
        currentBase: 1.8,
        currentDrift: 0.01,
        currentWobble: 0.06,
        powerBase: 6.2,
        powerDrift: 0.02,
        powerWobble: 0.1,
      }),
      buildProcess('p-a2', '第 2 次充电', {
        offsetStart: 2,
        voltageBase: 3.72,
        voltageDrift: 0.019,
        voltageWobble: 0.028,
        currentBase: 1.78,
        currentDrift: 0.009,
        currentWobble: 0.055,
        powerBase: 6.15,
        powerDrift: 0.018,
        powerWobble: 0.09,
      }),
      buildProcess('p-a3', '第 3 次充电', {
        offsetStart: 0,
        voltageBase: 3.74,
        voltageDrift: 0.018,
        voltageWobble: 0.026,
        currentBase: 1.79,
        currentDrift: 0.008,
        currentWobble: 0.05,
        powerBase: 6.18,
        powerDrift: 0.016,
        powerWobble: 0.08,
        note: '当前样本默认展示。',
      }),
      buildProcess('p-a4', '第 4 次充电', {
        offsetStart: 1,
        voltageBase: 3.75,
        voltageDrift: 0.017,
        voltageWobble: 0.024,
        currentBase: 1.8,
        currentDrift: 0.008,
        currentWobble: 0.048,
        powerBase: 6.2,
        powerDrift: 0.015,
        powerWobble: 0.078,
      }),
      buildProcess('p-a5', '第 5 次充电', {
        offsetStart: 0,
        voltageBase: 3.76,
        voltageDrift: 0.016,
        voltageWobble: 0.022,
        currentBase: 1.81,
        currentDrift: 0.007,
        currentWobble: 0.045,
        powerBase: 6.22,
        powerDrift: 0.014,
        powerWobble: 0.075,
      }),
    ],
  },
  {
    id: 'battery-aging-002',
    name: '示例电池 B',
    status: 'aging',
    label: '电池老化',
    capacityRange: '60-80%',
    shortSummary: '后期充电时间拉长，功率和电流响应变弱。',
    longSummary: '多次充电中能看到形态漂移，属于更适合做老化趋势演示的样本。',
    processCount: 6,
    highlightedProcessId: 'p-b4',
    processes: [
      buildProcess('p-b1', '第 1 次充电', {
        offsetStart: 0,
        voltageBase: 3.66,
        voltageDrift: 0.018,
        voltageWobble: 0.035,
        currentBase: 1.72,
        currentDrift: 0.004,
        currentWobble: 0.07,
        powerBase: 6.0,
        powerDrift: 0.006,
        powerWobble: 0.11,
      }),
      buildProcess('p-b2', '第 2 次充电', {
        offsetStart: 3,
        voltageBase: 3.67,
        voltageDrift: 0.017,
        voltageWobble: 0.036,
        currentBase: 1.69,
        currentDrift: 0.003,
        currentWobble: 0.072,
        powerBase: 5.92,
        powerDrift: 0.004,
        powerWobble: 0.12,
      }),
      buildProcess('p-b3', '第 3 次充电', {
        offsetStart: 0,
        voltageBase: 3.69,
        voltageDrift: 0.016,
        voltageWobble: 0.04,
        currentBase: 1.66,
        currentDrift: 0.002,
        currentWobble: 0.074,
        powerBase: 5.85,
        powerDrift: 0.002,
        powerWobble: 0.125,
      }),
      buildProcess('p-b4', '第 4 次充电', {
        offsetStart: 0,
        voltageBase: 3.71,
        voltageDrift: 0.014,
        voltageWobble: 0.042,
        currentBase: 1.61,
        currentDrift: 0.001,
        currentWobble: 0.076,
        powerBase: 5.75,
        powerDrift: 0.001,
        powerWobble: 0.13,
        note: '后期变化更明显。',
      }),
      buildProcess('p-b5', '第 5 次充电', {
        offsetStart: 2,
        voltageBase: 3.72,
        voltageDrift: 0.013,
        voltageWobble: 0.043,
        currentBase: 1.58,
        currentDrift: 0,
        currentWobble: 0.078,
        powerBase: 5.7,
        powerDrift: 0,
        powerWobble: 0.135,
      }),
      buildProcess('p-b6', '第 6 次充电', {
        offsetStart: 0,
        voltageBase: 3.73,
        voltageDrift: 0.012,
        voltageWobble: 0.045,
        currentBase: 1.56,
        currentDrift: -0.001,
        currentWobble: 0.08,
        powerBase: 5.62,
        powerDrift: -0.002,
        powerWobble: 0.14,
      }),
    ],
  },
  {
    id: 'battery-fault-003',
    name: '示例电池 C',
    status: 'fault',
    label: '电池故障',
    capacityRange: '40-60%',
    shortSummary: '充电中存在局部突变与波动，适合做故障演示。',
    longSummary: '这一组样本包含局部异常波动，便于演示模型如何给出故障判断。',
    processCount: 4,
    highlightedProcessId: 'p-c2',
    processes: [
      buildProcess('p-c1', '第 1 次充电', {
        offsetStart: 0,
        voltageBase: 3.58,
        voltageDrift: 0.012,
        voltageWobble: 0.07,
        currentBase: 1.45,
        currentDrift: 0.015,
        currentWobble: 0.14,
        powerBase: 5.3,
        powerDrift: 0.02,
        powerWobble: 0.23,
      }),
      buildProcess('p-c2', '第 2 次充电', {
        offsetStart: 1,
        voltageBase: 3.61,
        voltageDrift: 0.01,
        voltageWobble: 0.078,
        currentBase: 1.41,
        currentDrift: 0.012,
        currentWobble: 0.15,
        powerBase: 5.18,
        powerDrift: 0.016,
        powerWobble: 0.26,
        note: '局部异常波动较明显。',
      }),
      buildProcess('p-c3', '第 3 次充电', {
        offsetStart: 0,
        voltageBase: 3.63,
        voltageDrift: 0.011,
        voltageWobble: 0.082,
        currentBase: 1.38,
        currentDrift: 0.009,
        currentWobble: 0.16,
        powerBase: 5.08,
        powerDrift: 0.013,
        powerWobble: 0.27,
      }),
      buildProcess('p-c4', '第 4 次充电', {
        offsetStart: 4,
        voltageBase: 3.64,
        voltageDrift: 0.009,
        voltageWobble: 0.085,
        currentBase: 1.35,
        currentDrift: 0.008,
        currentWobble: 0.17,
        powerBase: 5.0,
        powerDrift: 0.011,
        powerWobble: 0.28,
      }),
    ],
  },
]

export const selectedInviteCode: InviteState = {
  code: '',
  active: false,
  usageLimit: 20,
  usageCount: 3,
}

export const adminInvites: AdminInviteRow[] = [
  {
    id: 1,
    code: 'PUBLIC-BETA-001',
    name: '公开体验码',
    usageLimit: 20,
    usageCount: 3,
    perUserQuota: 10,
    status: 'active',
    expiresAt: '2026-12-31 23:59',
  },
  {
    id: 2,
    code: 'VIP-AGING-001',
    name: '老化演示码',
    usageLimit: 12,
    usageCount: 6,
    perUserQuota: 10,
    status: 'active',
    expiresAt: '2026-08-01 23:59',
  },
  {
    id: 3,
    code: 'FAULT-LAB-002',
    name: '故障验证码',
    usageLimit: 8,
    usageCount: 8,
    perUserQuota: 10,
    status: 'paused',
    expiresAt: '2026-05-15 23:59',
  },
]

export const adminUsers: AdminUserRow[] = [
  {
    phone: '138****0001',
    nickname: '张先生',
    role: 'user',
    inviteCode: 'PUBLIC-BETA-001',
    quotaUsed: 3,
    quotaTotal: 20,
    lastSeen: '2026-04-12 10:12',
  },
  {
    phone: '139****0026',
    nickname: '王女士',
    role: 'user',
    inviteCode: 'VIP-AGING-001',
    quotaUsed: 4,
    quotaTotal: 12,
    lastSeen: '2026-04-12 09:40',
  },
  {
    phone: '136****0099',
    nickname: '管理员',
    role: 'admin',
    inviteCode: '-',
    quotaUsed: 0,
    quotaTotal: 0,
    lastSeen: '2026-04-12 08:30',
  },
]

export const adminRuns: AdminRunRow[] = [
  {
    id: 'run-1021',
    phone: '138****0001',
    batteryId: 'battery-normal-001',
    label: '正常',
    capacityRange: '90-100%',
    status: 'success',
    createdAt: '2026-04-12 10:15',
  },
  {
    id: 'run-1022',
    phone: '139****0026',
    batteryId: 'battery-aging-002',
    label: '电池老化',
    capacityRange: '60-80%',
    status: 'success',
    createdAt: '2026-04-12 09:44',
  },
  {
    id: 'run-1023',
    phone: '138****0001',
    batteryId: 'battery-fault-003',
    label: '电池故障',
    capacityRange: '40-60%',
    status: 'failed',
    createdAt: '2026-04-12 09:05',
  },
]
