import { apiFetch } from './client'
import { getInviteSessionToken } from './auth'

export type ChargeSeries = {
  time_offset_min: number[]
  powers: number[]
  voltages: (number | null)[]
  currents: (number | null)[]
}

export type ChargeOrder = {
  order_no: string
  supplier_code: string | null
  supplier_name: string | null
  user_name: string | null
  user_phone: string | null
  charge_start_time: string | null
  charge_end_time: string | null
  charge_capacity: number | null
  series: ChargeSeries
}

export type ChargeOrderListResponse = {
  phone_masked: string
  orders: ChargeOrder[]
}

export async function fetchChargeOrders(phone: string): Promise<ChargeOrderListResponse> {
  const token = getInviteSessionToken()
  return apiFetch<ChargeOrderListResponse>('/charge/orders', {
    method: 'POST',
    body: JSON.stringify({ phone }),
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}
