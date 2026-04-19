import { adminRuns, adminUsers } from './mockData'
import { mapDataset } from './datasets'
import type { AdminInviteRow, AdminRunRow, AdminUserRow, BatteryExample } from './types'
import { apiFetch } from './client'

const ADMIN_TOKEN_KEY = 'chargellm.demo.admin-token'

export function getAdminToken() {
  if (typeof window === 'undefined') {
    return ''
  }
  return window.sessionStorage.getItem(ADMIN_TOKEN_KEY) || ''
}

export function setAdminToken(token: string) {
  if (typeof window === 'undefined') {
    return
  }
  window.sessionStorage.setItem(ADMIN_TOKEN_KEY, token)
}

export async function loginAdmin(username: string, password: string) {
  const response = await apiFetch<{ access_token: string; admin_username: string }>('/auth/admin/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  setAdminToken(response.access_token)
  return response
}

type AdminInviteApiRow = {
  id: number
  code: string
  name: string
  max_uses: number
  used_uses: number
  per_user_quota: number
  expires_at: string | null
  is_active: boolean
}

type CreateInvitePayload = {
  name: string
  code?: string
  max_uses?: number
  per_user_quota?: number
}

type UpdateInvitePayload = {
  name?: string
  max_uses?: number
  per_user_quota?: number
  expires_at?: string | null
  is_active?: boolean
}

function adminHeaders() {
  return { Authorization: `Bearer ${getAdminToken()}` }
}

function mapInvite(row: AdminInviteApiRow): AdminInviteRow {
  return {
    id: row.id,
    code: row.code,
    name: row.name,
    usageLimit: row.max_uses,
    usageCount: row.used_uses,
    perUserQuota: row.per_user_quota,
    status: row.is_active ? 'active' : 'paused',
    expiresAt: row.expires_at || '长期',
  }
}

export async function listAdminInvites(): Promise<AdminInviteRow[]> {
  if (!getAdminToken()) {
    return []
  }
  const rows = await apiFetch<AdminInviteApiRow[]>('/admin/invites', {
    headers: adminHeaders(),
  })
  return rows.map(mapInvite)
}

export async function createAdminInvite(payload: CreateInvitePayload): Promise<AdminInviteRow> {
  const row = await apiFetch<AdminInviteApiRow>('/admin/invites', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
  return mapInvite(row)
}

export async function updateAdminInvite(inviteId: number, payload: UpdateInvitePayload): Promise<AdminInviteRow> {
  const row = await apiFetch<AdminInviteApiRow>(`/admin/invites/${inviteId}`, {
    method: 'PATCH',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
  return mapInvite(row)
}

export async function deleteAdminInvite(inviteId: number): Promise<void> {
  await apiFetch<{ status: string }>(`/admin/invites/${inviteId}`, {
    method: 'DELETE',
    headers: adminHeaders(),
  })
}

export function listAdminUsers(): AdminUserRow[] {
  return adminUsers
}

export function listAdminRuns(): AdminRunRow[] {
  return adminRuns
}

type DatasetApiRow = Parameters<typeof mapDataset>[0]

export async function listAdminDatasets(): Promise<BatteryExample[]> {
  if (!getAdminToken()) {
    return []
  }
  const rows = await apiFetch<DatasetApiRow[]>('/admin/datasets', {
    headers: adminHeaders(),
  })
  return rows.map(mapDataset)
}

export async function createAdminDataset(payload: {
  title: string
  problem_type: string
  capacity_range: string
  description: string
  sort_order: number
  is_active: boolean
  file_name: string
  content?: string
}): Promise<BatteryExample> {
  const row = await apiFetch<DatasetApiRow>('/admin/datasets', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
  return mapDataset(row)
}

export async function updateAdminDataset(
  datasetId: number,
  payload: {
    title?: string
    problem_type?: string
    capacity_range?: string
    description?: string
    sort_order?: number
    is_active?: boolean
    file_name?: string
    content?: string
  },
): Promise<BatteryExample> {
  const row = await apiFetch<DatasetApiRow>(`/admin/datasets/${datasetId}`, {
    method: 'PATCH',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
  return mapDataset(row)
}

export async function deleteAdminDataset(datasetId: number): Promise<void> {
  await apiFetch<{ status: string }>(`/admin/datasets/${datasetId}`, {
    method: 'DELETE',
    headers: adminHeaders(),
  })
}

export async function importAdminDatasetFromMysql(payload: {
  phone: string
  start_time: string
  end_time: string
  title?: string
}): Promise<BatteryExample> {
  const row = await apiFetch<DatasetApiRow>('/admin/datasets/mysql-import', {
    method: 'POST',
    headers: adminHeaders(),
    body: JSON.stringify(payload),
  })
  return mapDataset(row)
}
