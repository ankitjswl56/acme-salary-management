import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { apiFetch } from '../api/client'
import { clearStoredAuth, getStoredAuth, setStoredAuth } from './storage'
import type { AuthState, LoginResponse } from './types'

interface AuthContextValue {
  auth: AuthState | null
  login: (email: string, password: string) => Promise<AuthState>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(() => getStoredAuth())

  const logout = useCallback(() => {
    clearStoredAuth()
    setAuth(null)
  }, [])

  useEffect(() => {
    window.addEventListener('acme:unauthorized', logout)
    return () => window.removeEventListener('acme:unauthorized', logout)
  }, [logout])

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    const nextAuth: AuthState = { token: data.access_token, email: data.email, role: data.role }
    setStoredAuth(nextAuth)
    setAuth(nextAuth)
    return nextAuth
  }, [])

  return <AuthContext.Provider value={{ auth, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}