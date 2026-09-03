import { apiFetch } from './client'

export function getSupportedCurrencies() {
  return apiFetch<string[]>('/reference/currencies')
}