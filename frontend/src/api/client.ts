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

// FastAPI's `detail` is a plain string for most errors (404, 409, our own
// raised HTTPExceptions), but a list of {loc, msg, type} objects for
// pydantic validation errors (422) - forms are the first place we're
// likely to actually hit that shape, so handle both.
function extractErrorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== 'object' || !('detail' in data)) {
    return fallback
  }

  const detail = (data as { detail: unknown }).detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        item && typeof item === 'object' && 'msg' in item ? String((item as { msg: unknown }).msg) : null,
      )
      .filter((msg): msg is string => msg !== null)
    if (messages.length > 0) {
      return messages.join('; ')
    }
  }
  return fallback
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

  // FormData (file uploads) is sent as-is - fetch sets the multipart
  // Content-Type (with the correct boundary) itself, and setting it
  // manually here would break that.
  const isFormData = body instanceof FormData
  if (body !== undefined && !isFormData) headers['Content-Type'] = 'application/json'

  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
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
    throw new ApiError(response.status, extractErrorMessage(data, response.statusText))
  }

  return data as T
}