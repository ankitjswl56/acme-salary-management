import { BarChart } from '@mui/x-charts/BarChart'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import { visuallyHidden } from '@mui/utils'
import { getSalaryDistribution } from '../../api/analytics'
import { formatCount, formatPercent1 } from '../../lib/format'
import { useChartTokens } from '../../theme'
import { ChartCard } from './ChartCard'
import { useAnalyticsQuery } from './useAnalyticsQuery'

// View 4: org-wide histogram of current USD salary. Bands stay in their
// natural low-to-high order - they're ordinal, not something to rank.
export function SalaryDistributionCard() {
  const { data, loading, error } = useAnalyticsQuery(getSalaryDistribution, 'salary-distribution')
  const tokens = useChartTokens()

  const rows = data ?? []
  const total = rows.reduce((sum, r) => sum + r.headcount, 0)
  const chartData = rows.map((r) => ({ band: r.band, headcount: r.headcount }))

  const table = (
    <Table size="small" sx={{ '& td, & th': { fontVariantNumeric: 'tabular-nums' } }}>
      <caption style={visuallyHidden}>Employee count by salary band, low to high.</caption>
      <TableHead>
        <TableRow>
          <TableCell>Band</TableCell>
          <TableCell align="right">Employees</TableCell>
          <TableCell align="right">Share</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.band}>
            <TableCell component="th" scope="row">
              {row.band}
            </TableCell>
            <TableCell align="right">{formatCount(row.headcount)}</TableCell>
            <TableCell align="right">
              {total ? formatPercent1(row.headcount / total) : '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <ChartCard
      title="Salary distribution"
      description="Active employees by current USD salary band."
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      table={table}
    >
      <BarChart
        dataset={chartData}
        height={280}
        colors={[tokens.seriesA]}
        xAxis={[{ scaleType: 'band', dataKey: 'band', tickLabelStyle: { fontSize: 11 } }]}
        yAxis={[{ width: 44 }]}
        series={[
          {
            dataKey: 'headcount',
            label: 'Employees',
            valueFormatter: (v) => (v == null ? '—' : formatCount(v)),
          },
        ]}
        margin={{ left: 0, right: 8, top: 12, bottom: 32 }}
        hideLegend
      />
    </ChartCard>
  )
}