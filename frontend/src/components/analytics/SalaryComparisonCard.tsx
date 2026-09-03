import { BarChart } from '@mui/x-charts/BarChart'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import { visuallyHidden } from '@mui/utils'
import { formatCount, formatUsd, formatUsdCompact } from '../../lib/format'
import { useChartTokens } from '../../theme'
import { ChartCard } from './ChartCard'

interface SalaryComparisonRow {
  headcount: number
  avg_salary_usd: number
  median_salary_usd: number
}

interface SalaryComparisonCardProps<T extends SalaryComparisonRow> {
  title: string
  description: string
  /** Column/axis header for the grouping dimension, e.g. "Country". */
  dimensionLabel: string
  data: T[]
  loading?: boolean
  error?: string
  /** Pulls the dimension value off a row, e.g. `(r) => r.country`. */
  getLabel: (row: T) => string
}

const ROW_PX = 19
const CHART_CHROME_PX = 84

// Views 1 & 2: avg & median current USD salary by country / by department.
// Bars are sorted by median (descending) so the chart itself states the
// ranking - median, not mean, because it's the more robust "typical pay"
// figure (a few large salaries skew the mean).
export function SalaryComparisonCard<T extends SalaryComparisonRow>({
  title,
  description,
  dimensionLabel,
  data,
  loading = false,
  error = '',
  getLabel,
}: SalaryComparisonCardProps<T>) {
  const tokens = useChartTokens()

  const rows = [...data].sort((a, b) => b.median_salary_usd - a.median_salary_usd)
  const chartData = rows.map((row) => ({
    label: getLabel(row),
    avg_salary_usd: row.avg_salary_usd,
    median_salary_usd: row.median_salary_usd,
  }))
  const chartHeight = Math.max(220, rows.length * 2 * ROW_PX + CHART_CHROME_PX)

  const table = (
    <Table size="small" sx={{ '& td, & th': { fontVariantNumeric: 'tabular-nums' } }}>
      <caption style={visuallyHidden}>
        {title}, sorted by median salary, highest first.
      </caption>
      <TableHead>
        <TableRow>
          <TableCell>{dimensionLabel}</TableCell>
          <TableCell align="right">Headcount</TableCell>
          <TableCell align="right">Average</TableCell>
          <TableCell align="right">Median</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={getLabel(row)}>
            <TableCell component="th" scope="row">
              {getLabel(row)}
            </TableCell>
            <TableCell align="right">{formatCount(row.headcount)}</TableCell>
            <TableCell align="right">{formatUsd(row.avg_salary_usd)}</TableCell>
            <TableCell align="right">{formatUsd(row.median_salary_usd)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <ChartCard
      title={title}
      description={description}
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      table={table}
    >
      <BarChart
        dataset={chartData}
        layout="horizontal"
        height={chartHeight}
        colors={[tokens.seriesA, tokens.seriesB]}
        borderRadius={3}
        yAxis={[
          { scaleType: 'band', dataKey: 'label', width: 92, categoryGapRatio: 0.4, barGapRatio: 0.15 },
        ]}
        xAxis={[{ valueFormatter: (v: number) => formatUsdCompact(v) }]}
        series={[
          {
            dataKey: 'avg_salary_usd',
            label: 'Average',
            valueFormatter: (v) => (v == null ? '—' : formatUsd(v)),
          },
          {
            dataKey: 'median_salary_usd',
            label: 'Median',
            valueFormatter: (v) => (v == null ? '—' : formatUsd(v)),
          },
        ]}
        margin={{ left: 0, right: 28, top: 8, bottom: 24 }}
      />
    </ChartCard>
  )
}