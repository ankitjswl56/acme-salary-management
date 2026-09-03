import { getSalaryByDepartment } from '../../api/analytics'
import { useAnalyticsQuery } from './useAnalyticsQuery'

/**
 * Department names for the equity-view filters. Sourced from the
 * by-department analytics endpoint (reachable by every role) rather than
 * /employees/filters, which executive_viewer can't call.
 */
export function useDepartmentOptions(): string[] {
  const { data } = useAnalyticsQuery(getSalaryByDepartment, 'dept-options')
  return (data ?? []).map((row) => row.department).sort()
}