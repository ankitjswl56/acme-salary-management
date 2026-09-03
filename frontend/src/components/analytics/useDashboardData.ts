import { getDashboard } from '../../api/analytics'
import type { AnalyticsDashboard } from '../../types/api'
import { useAnalyticsQuery } from './useAnalyticsQuery'

/**
 * The whole dashboard in one request. `AnalyticsPage` calls this once and
 * fans the slices out to the cards as props; a card only issues its own
 * request when the user moves a filter off its default.
 */
export function useDashboardData() {
  return useAnalyticsQuery<AnalyticsDashboard>(getDashboard, 'dashboard')
}