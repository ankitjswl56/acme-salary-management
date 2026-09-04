import type {
  AnalyticsDashboard,
  ChangeType,
  CountryPayroll,
  CountrySalaryStats,
  DepartmentSalaryStats,
  GenderHeadcount,
  GenderSalaryStats,
  NLQueryResponse,
  QuarterlyPayroll,
  SalaryChangeFeedItem,
  SalaryDistributionBand,
} from '../types/api'
import { apiFetch } from './client'

// Wrappers for the analytics endpoints (GET /analytics/*). Parallel to
// api/employees.ts - one thin function per endpoint, the query layer and
// privacy rules all live in the backend.

// Natural-language query: POST a plain-English question, get back the
// analytics view the model picked plus its result. Read-only.
export function askAnalytics(question: string) {
  return apiFetch<NLQueryResponse>('/analytics/ask', { method: 'POST', body: { question } })
}

// One request for the whole dashboard on load. The per-view wrappers below
// are still used when a card's filter moves off its default.
export function getDashboard() {
  return apiFetch<AnalyticsDashboard>('/analytics/dashboard')
}

export function getSalaryByCountry() {
  return apiFetch<CountrySalaryStats[]>('/analytics/salary-by-country')
}

export function getSalaryByDepartment() {
  return apiFetch<DepartmentSalaryStats[]>('/analytics/salary-by-department')
}

export function getHeadcountPayrollByCountry() {
  return apiFetch<CountryPayroll[]>('/analytics/headcount-payroll-by-country')
}

export function getSalaryDistribution() {
  return apiFetch<SalaryDistributionBand[]>('/analytics/salary-distribution')
}

export function getGenderRatio(department?: string) {
  return apiFetch<GenderHeadcount[]>('/analytics/gender-ratio', {
    params: { department },
  })
}

export interface SalaryByGenderParams {
  department?: string
  role?: string
  minGroupSize?: number
}

export function getSalaryByGender({ department, role, minGroupSize }: SalaryByGenderParams = {}) {
  return apiFetch<GenderSalaryStats[]>('/analytics/salary-by-gender', {
    params: { department, role, min_group_size: minGroupSize },
  })
}

export interface RecentChangesParams {
  months?: number
  changeType?: ChangeType
  limit?: number
}

export function getRecentChanges({ months, changeType, limit }: RecentChangesParams = {}) {
  return apiFetch<SalaryChangeFeedItem[]>('/analytics/recent-changes', {
    params: { months, change_type: changeType, limit },
  })
}

export function getPayrollTrend(quarters?: number) {
  return apiFetch<QuarterlyPayroll[]>('/analytics/payroll-trend', {
    params: { quarters },
  })
}