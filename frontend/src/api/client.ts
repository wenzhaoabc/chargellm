export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new ApiError(response.status, text || response.statusText)
  }

  return response.json() as Promise<T>
}
