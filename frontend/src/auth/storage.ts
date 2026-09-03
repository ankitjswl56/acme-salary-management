import type { AuthState } from './types'

const STORAGE_KEY = 'acme_salary_auth'

export function getStoredAuth(): AuthState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthState) : null
  } catch {
    return null
  }
}

export function setStoredAuth(auth: AuthState): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
}

export function clearStoredAuth(): void {
  localStorage.removeItem(STORAGE_KEY)
}