import type {
  EmployeeCreate,
  EmployeeDetail,
  EmployeeFilterOptions,
  EmployeeListResponse,
  EmployeeRead,
  EmployeeStatus,
  EmployeeUpdate,
  SalaryRecordRead,
} from '../types/api'
import { apiFetch } from './client'

export interface EmployeeListParams {
  [key: string]: string | number | boolean | undefined | null
  search?: string
  country?: string
  department?: string
  status?: EmployeeStatus | ''
  skip?: number
  limit?: number
}

export function listEmployees(params: EmployeeListParams = {}) {
  return apiFetch<EmployeeListResponse>('/employees', { params })
}

export function getFilterOptions() {
  return apiFetch<EmployeeFilterOptions>('/employees/filters')
}

export function getEmployee(id: number) {
  return apiFetch<EmployeeDetail>(`/employees/${id}`)
}

export function getSalaryHistory(id: number) {
  return apiFetch<SalaryRecordRead[]>(`/employees/${id}/salary-records`)
}

export function createEmployee(data: EmployeeCreate) {
  return apiFetch<EmployeeRead>('/employees', { method: 'POST', body: data })
}

export function updateEmployee(id: number, data: EmployeeUpdate) {
  return apiFetch<EmployeeRead>(`/employees/${id}`, { method: 'PATCH', body: data })
}