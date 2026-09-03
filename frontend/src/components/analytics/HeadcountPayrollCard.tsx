import { BarChart } from '@mui/x-charts/BarChart'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import { visuallyHidden } from '@mui/utils'
import { formatCount, formatPercent1, formatUsd, formatUsdCompact } from '../../lib/format'
import type { CountryPayroll } from '../../types/api'
import { useChartTokens } from '../../theme'
import { ChartCard } from './ChartCard'

const ROW_PX = 24
const CHART_CHROME_PX = 64

// View 3: total payroll *cost* by country - the sum of everyone's pay, i.e.
// headcount x salary. This is a breakdown of the headline total-payroll
// figure, NOT the same thing as "Pay by country" (view 1), which is the
// average/median salary of one person. Sorted by payroll, descending.
export function HeadcountPayrollCard({
  data,
  loading = false,
  error = '',
}: {
  data: CountryPayroll[]
  loading?: boolean
  error?: string
}) {
  const tokens = useChartTokens()

  const rows = [...data].sort((a, b) => b.total_payroll_usd - a.total_payroll_usd)
  const totalPayroll = rows.reduce((sum, r) => sum + r.total_payroll_usd, 0)
  const maxPayroll = rows.length ? Math.max(...rows.map((r) => r.total_payroll_usd)) : 0
  const chartData = rows.map((r) => ({ label: r.country, total_payroll_usd: r.total_payroll_usd }))
  const chartHeight = Math.max(200, rows.length * ROW_PX + CHART_CHROME_PX)

  const leader = rows[0]
  const insight = leader
    ? `Total USD wage bill (headcount × pay), not per-person salary. ${leader.country} is ${
        totalPayroll ? formatPercent1(leader.total_payroll_usd / totalPayroll) : '—'
      } of the ${formatUsdCompact(totalPayroll)} total.`
    : 'Total USD wage bill by country.'

  const table = (
    <Table size="small" sx={{ '& td, & th': { fontVariantNumeric: 'tabular-nums' } }}>
      <caption style={visuallyHidden}>
        Headcount and total payroll by country, highest payroll first.
      </caption>
      <TableHead>
        <TableRow>
          <TableCell>Country</TableCell>
          <TableCell align="right">Headcount</TableCell>
          <TableCell align="right">Total payroll (USD)</TableCell>
          <TableCell align="right">Share</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.country}>
            <TableCell component="th" scope="row">
              {row.country}
            </TableCell>
            <TableCell align="right">{formatCount(row.headcount)}</TableCell>
            <TableCell align="right">{formatUsd(row.total_payroll_usd)}</TableCell>
            <TableCell align="right">
              {totalPayroll ? formatPercent1(row.total_payroll_usd / totalPayroll) : '—'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <ChartCard
      title="Total payroll by country"
      description={insight}
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      table={table}
    >
      <BarChart
        dataset={chartData}
        layout="horizontal"
        height={chartHeight}
        colors={[tokens.seriesA]}
        yAxis={[{ scaleType: 'band', dataKey: 'label', width: 44 }]}
        xAxis={[{ valueFormatter: (v: number) => formatUsdCompact(v), max: maxPayroll * 1.15 }]}
        series={[
          {
            dataKey: 'total_payroll_usd',
            label: 'Total payroll',
            valueFormatter: (v) => (v == null ? '—' : formatUsd(v)),
            barLabel: (item) =>
              totalPayroll && item.value ? formatPercent1(item.value / totalPayroll) : null,
            barLabelPlacement: 'outside',
          },
        ]}
        margin={{ left: 0, right: 76, top: 8, bottom: 24 }}
        hideLegend
        sx={{ '& .MuiBarLabel-root': { fontSize: 10, fill: tokens.muted } }}
      />
    </ChartCard>
  )
}