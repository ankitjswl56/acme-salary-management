import { clearStoredAuth, getStoredAuth } from '../auth/storage'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface ApiFetchOptions {
  method?: string
  body?: unknown
  params?: Record<string, string | number | boolean | undefined | null>
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { method = 'GET', body, params } = options
  const url = new URL(`${API_URL}${path}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const auth = getStoredAuth()
  const headers: Record<string, string> = {}
  if (auth?.token) headers.Authorization = `Bearer ${auth.token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  // A 401 means the token is missing/expired/invalid - clear it and let
  // AuthContext (listening for this event) redirect to /login.
  if (response.status === 401) {
    clearStoredAuth()
    window.dispatchEvent(new Event('acme:unauthorized'))
  }

  const text = await response.text()
  const data: unknown = text ? JSON.parse(text) : null

  if (!response.ok) {
    const detail =
      data && typeof data === 'object' && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : response.statusText
    throw new ApiError(response.status, detail)
  }

  return data as T
}