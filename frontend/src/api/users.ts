import type { AdminUser, AdminUserCreate, UserRole } from '../types/api'
import { apiFetch } from './client'

// Admin-only user management. All of these 403 for hr_manager / exec.

export function listUsers() {
  return apiFetch<AdminUser[]>('/users')
}

export function createUser(data: AdminUserCreate) {
  return apiFetch<AdminUser>('/users', { method: 'POST', body: data })
}

export function updateUserRole(id: number, role: UserRole) {
  return apiFetch<AdminUser>(`/users/${id}`, { method: 'PATCH', body: { role } })
}

export function deleteUser(id: number) {
  return apiFetch<void>(`/users/${id}`, { method: 'DELETE' })
}