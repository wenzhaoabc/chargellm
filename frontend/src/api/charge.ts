import { adminRuns, demoBatteries } from './mockData'
import type { BatteryExample } from './types'

export function listExampleBatteries(): BatteryExample[] {
  return demoBatteries
}

export function getBatteryById(batteryId: string): BatteryExample | undefined {
  return demoBatteries.find((item) => item.id === batteryId)
}

export function getDefaultBattery(): BatteryExample {
  return demoBatteries[0]
}

export function listRecentHistory() {
  return adminRuns.slice(0, 3)
}

export function queryChargingRecordsByPhoneMock(phone: string) {
  const maskedPhone = phone.trim() || '未填写'
  return {
    phone: maskedPhone,
    items: [
      {
        recordId: 'rec-20260412-01',
        batteryId: 'battery-aging-002',
        lastChargeAt: '2026-04-10 08:20',
        status: '电池老化',
      },
      {
        recordId: 'rec-20260412-02',
        batteryId: 'battery-normal-001',
        lastChargeAt: '2026-04-11 12:05',
        status: '正常',
      },
    ],
    message: '手机号验证通过后可切换为真实查询接口。',
  }
}
