import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { GenderRepresentationCard } from '../components/analytics/GenderRepresentationCard'
import { HeadcountPayrollCard } from '../components/analytics/HeadcountPayrollCard'
import { HeadlineBand } from '../components/analytics/HeadlineBand'
import { PayrollTrendCard } from '../components/analytics/PayrollTrendCard'
import { RecentChangesCard } from '../components/analytics/RecentChangesCard'
import { SalaryByGenderCard } from '../components/analytics/SalaryByGenderCard'
import { SalaryComparisonCard } from '../components/analytics/SalaryComparisonCard'
import { SalaryDistributionCard } from '../components/analytics/SalaryDistributionCard'
import { useDashboardData } from '../components/analytics/useDashboardData'

const twoCol = {
  display: 'grid',
  gap: 2,
  gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
}

// Phase 7 dashboard, ordered as a narrative: the headline spend, where that
// spend goes (total payroll by country) and how it has moved (trend), then
// how individuals are paid (per-employee pay by country/department, and the
// org-wide spread), then a named "Pay equity" section, then the audit feed.
// Reachable by every authenticated role - the only surface executive_viewer
// can see.
//
// The whole page is one request (GET /analytics/dashboard). Each card renders
// from a slice of that payload; the three filterable cards only issue their
// own request when a filter moves off its default.
export function AnalyticsPage() {
  const { data, loading, error } = useDashboardData()

  const departments = data
    ? [...new Set(data.salary_by_department.map((row) => row.department))].sort()
    : []

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }} gutterBottom>
        Analytics
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3, maxWidth: 680 }}>
        How the organization pays people — headline spend, salary distribution, and pay-equity
        checks. All figures are normalized to USD at the exchange rate captured when each record
        was created.
      </Typography>

      {error && (
        <Alert severity="error" variant="outlined" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <HeadlineBand
        byCountry={data?.headcount_payroll_by_country ?? []}
        trend={data?.payroll_trend ?? []}
        loading={loading}
      />

      {/* Where the headline spend goes, then how it's moved over time. */}
      <Stack spacing={2}>
        <HeadcountPayrollCard data={data?.headcount_payroll_by_country ?? []} loading={loading} />
        <PayrollTrendCard data={data?.payroll_trend ?? []} loading={loading} />
      </Stack>

      {/* How individuals are paid - average/median for one person, by group. */}
      <Box sx={{ ...twoCol, mt: 2 }}>
        <SalaryComparisonCard
          title="Pay by country (per employee)"
          description="Average and median of one active employee's current USD salary — not total cost. Highest median first."
          dimensionLabel="Country"
          data={data?.salary_by_country ?? []}
          loading={loading}
          getLabel={(row) => row.country}
        />
        <SalaryComparisonCard
          title="Pay by department (per employee)"
          description="Average and median of one active employee's current USD salary. Highest median first."
          dimensionLabel="Department"
          data={data?.salary_by_department ?? []}
          loading={loading}
          getLabel={(row) => row.department}
        />
      </Box>

      <Box sx={{ mt: 2 }}>
        <SalaryDistributionCard data={data?.salary_distribution ?? []} loading={loading} />
      </Box>

      <Box
        sx={{
          mt: 5,
          mb: 2,
          pb: 1,
          borderBottom: 2,
          borderColor: 'text.primary',
        }}
      >
        <Typography variant="h6" component="h2" sx={{ fontWeight: 700 }}>
          Pay equity
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 680, mt: 0.5 }}>
          Representation is a headcount, always shown. Average pay by gender is withheld for any
          group below the minimum size, so a figure can't expose one person's salary.
        </Typography>
      </Box>

      <Box sx={twoCol}>
        <GenderRepresentationCard
          initialData={data?.gender_ratio ?? []}
          departments={departments}
          loading={loading}
        />
        <SalaryByGenderCard
          initialData={data?.salary_by_gender ?? []}
          departments={departments}
          loading={loading}
        />
      </Box>

      <Box sx={{ mt: 2 }}>
        <RecentChangesCard initialData={data?.recent_changes ?? []} loading={loading} />
      </Box>
    </Box>
  )
}