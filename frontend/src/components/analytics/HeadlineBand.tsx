import Box from '@mui/material/Box'
import { formatCount, formatSignedPercent, formatUsdCompact } from '../../lib/format'
import type { CountryPayroll, QuarterlyPayroll } from '../../types/api'
import { useChartTokens } from '../../theme'
import { Sparkline } from './Sparkline'
import { StatTile, type StatDelta } from './StatTile'

// Number of trailing quarters shown in the run-rate sparkline.
const SPARK_QUARTERS = 6

// Tier 1: the three figures the whole dashboard is oriented around. Total
// payroll is the one deliberately bold element; everything below stays quiet.
export function HeadlineBand({
  byCountry,
  trend,
  loading = false,
}: {
  byCountry: CountryPayroll[]
  trend: QuarterlyPayroll[]
  loading?: boolean
}) {
  const tokens = useChartTokens()

  const totalPayroll = byCountry.reduce((sum, r) => sum + r.total_payroll_usd, 0)
  const totalHeadcount = byCountry.reduce((sum, r) => sum + r.headcount, 0)

  const sparkValues = trend.slice(-SPARK_QUARTERS).map((q) => q.total_payroll_usd)
  let delta: StatDelta | undefined
  if (trend.length >= 2) {
    const prev = trend[trend.length - 2].total_payroll_usd
    const curr = trend[trend.length - 1].total_payroll_usd
    const change = prev ? (curr - prev) / prev : 0
    delta = {
      label: formatSignedPercent(change),
      direction: change > 0.0005 ? 'up' : change < -0.0005 ? 'down' : 'flat',
      caption: 'vs. last quarter',
    }
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gap: { xs: 2, sm: 4 },
        gridTemplateColumns: { xs: '1fr', sm: '1.4fr 1fr 1.2fr' },
        py: 2.5,
        mb: 3,
        borderTop: 2,
        borderBottom: 1,
        borderColor: 'divider',
        borderTopColor: 'text.primary',
        '& > * + *': {
          sm: { pl: 4, borderLeft: 1, borderColor: 'divider' },
        },
      }}
    >
      <StatTile
        label="Total annual payroll"
        value={loading ? '' : formatUsdCompact(totalPayroll)}
        emphasis="headline"
        loading={loading}
      />
      <StatTile
        label="Active employees"
        value={loading ? '' : formatCount(totalHeadcount)}
        loading={loading}
      />
      <StatTile
        label="Payroll run-rate"
        value={loading ? '' : formatUsdCompact(sparkValues.at(-1) ?? 0)}
        delta={delta}
        sparkline={
          sparkValues.length >= 2 ? (
            <Sparkline values={sparkValues} color={tokens.seriesA} />
          ) : undefined
        }
        loading={loading}
      />
    </Box>
  )
}