import { LineChart } from '@mui/x-charts/LineChart'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import { visuallyHidden } from '@mui/utils'
import { getPayrollTrend } from '../../api/analytics'
import { formatCount, formatSignedPercent, formatUsd, formatUsdCompact } from '../../lib/format'
import { useChartTokens } from '../../theme'
import { ChartCard } from './ChartCard'
import { useAnalyticsQuery } from './useAnalyticsQuery'

const QUARTERS = 8

function fetchTrend() {
  return getPayrollTrend(QUARTERS)
}

// View 8: total payroll run-rate at each quarter end, oldest first. Plotted
// as a line on a non-zero axis so the growth *slope* is legible - a filled
// area to zero would flatten an 8% move into a straight line.
export function PayrollTrendCard() {
  const { data, loading, error } = useAnalyticsQuery(fetchTrend, 'payroll-trend')
  const tokens = useChartTokens()

  const rows = data ?? []
  const chartData = rows.map((r) => ({
    quarter: r.quarter,
    total_payroll_usd: r.total_payroll_usd,
  }))

  const values = rows.map((r) => r.total_payroll_usd)
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 0
  const pad = (max - min) * 0.15 || max * 0.05

  let insight = ''
  if (rows.length >= 2) {
    const change = values[0] ? (values[values.length - 1] - values[0]) / values[0] : 0
    insight = `${formatSignedPercent(change)} over ${rows.length} quarters (${rows[0].quarter} → ${rows[rows.length - 1].quarter}).`
  }

  const table = (
    <Table size="small" sx={{ '& td, & th': { fontVariantNumeric: 'tabular-nums' } }}>
      <caption style={visuallyHidden}>Total payroll by quarter, oldest first.</caption>
      <TableHead>
        <TableRow>
          <TableCell>Quarter</TableCell>
          <TableCell align="right">Employees</TableCell>
          <TableCell align="right">Total payroll (USD)</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.quarter}>
            <TableCell component="th" scope="row">
              {row.quarter}
            </TableCell>
            <TableCell align="right">{formatCount(row.headcount)}</TableCell>
            <TableCell align="right">{formatUsd(row.total_payroll_usd)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <ChartCard
      title="Payroll cost trend"
      description={insight || 'Total USD payroll run-rate at each quarter end.'}
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      table={table}
    >
      <LineChart
        dataset={chartData}
        height={210}
        colors={[tokens.seriesA]}
        xAxis={[{ scaleType: 'point', dataKey: 'quarter', tickLabelStyle: { fontSize: 11 } }]}
        yAxis={[
          {
            valueFormatter: (v: number) => formatUsdCompact(v),
            min: Math.max(0, min - pad),
            max: max + pad,
            width: 52,
          },
        ]}
        series={[
          {
            dataKey: 'total_payroll_usd',
            label: 'Total payroll',
            showMark: true,
            valueFormatter: (v) => (v == null ? '—' : formatUsd(v)),
          },
        ]}
        margin={{ left: 0, right: 40, top: 12, bottom: 4 }}
        hideLegend
      />
    </ChartCard>
  )
}