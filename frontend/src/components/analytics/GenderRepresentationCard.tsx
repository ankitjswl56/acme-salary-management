import { useState } from 'react'
import { BarChart } from '@mui/x-charts/BarChart'
import MenuItem from '@mui/material/MenuItem'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import { visuallyHidden } from '@mui/utils'
import { getGenderRatio } from '../../api/analytics'
import { formatCount, formatPercent1, genderLabel } from '../../lib/format'
import type { GenderHeadcount } from '../../types/api'
import { useChartTokens } from '../../theme'
import { ChartCard } from './ChartCard'
import { useAnalyticsQuery } from './useAnalyticsQuery'

const ALL = '__all__'

// View 5: gender representation by headcount. It's a count, so it's always
// safe to show at any group size (unlike average pay - see SalaryByGenderCard).
// Single-hue bars, sorted by headcount; share is shown as a label / column.
//
// `initialData` is the all-departments result from the one dashboard request;
// picking a department is the only thing that fires this card's own fetch.
export function GenderRepresentationCard({
  initialData,
  departments,
  loading: pageLoading = false,
}: {
  initialData: GenderHeadcount[]
  departments: string[]
  loading?: boolean
}) {
  const [department, setDepartment] = useState(ALL)
  const isDefault = department === ALL

  const { data, loading: queryLoading, error } = useAnalyticsQuery(
    () => (isDefault ? Promise.resolve(initialData) : getGenderRatio(department)),
    `gender-ratio:${department}`,
  )
  const tokens = useChartTokens()

  // At the default scope the card mirrors the dashboard payload live; a
  // department pick switches to this card's own fetched result.
  const source = isDefault ? initialData : (data ?? [])
  const loading = isDefault ? pageLoading : queryLoading
  const rows = [...source].sort((a, b) => b.headcount - a.headcount)
  const total = rows.reduce((sum, r) => sum + r.headcount, 0)
  const chartData = rows.map((r) => ({ label: genderLabel(r.gender), headcount: r.headcount }))

  const departmentFilter = (
    <TextField
      select
      size="small"
      label="Department"
      value={department}
      onChange={(e) => setDepartment(e.target.value)}
      sx={{ minWidth: 200 }}
    >
      <MenuItem value={ALL}>All departments</MenuItem>
      {departments.map((d) => (
        <MenuItem key={d} value={d}>
          {d}
        </MenuItem>
      ))}
    </TextField>
  )

  const table = (
    <Table size="small" sx={{ '& td, & th': { fontVariantNumeric: 'tabular-nums' } }}>
      <caption style={visuallyHidden}>Headcount by gender, highest first.</caption>
      <TableHead>
        <TableRow>
          <TableCell>Gender</TableCell>
          <TableCell align="right">Headcount</TableCell>
          <TableCell align="right">Share</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.gender}>
            <TableCell component="th" scope="row">
              {genderLabel(row.gender)}
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
      title="Gender representation"
      description="Active-employee headcount by gender."
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      actions={departmentFilter}
      table={table}
    >
      <BarChart
        dataset={chartData}
        layout="horizontal"
        height={Math.max(160, chartData.length * 44 + 60)}
        colors={[tokens.seriesA]}
        yAxis={[{ scaleType: 'band', dataKey: 'label', width: 120 }]}
        xAxis={[{ valueFormatter: (v: number) => formatCount(v) }]}
        series={[
          {
            dataKey: 'headcount',
            label: 'Headcount',
            valueFormatter: (v) =>
              v == null ? '—' : `${formatCount(v)} (${total ? formatPercent1(v / total) : '—'})`,
            barLabel: (item) =>
              total && item.value ? formatPercent1(item.value / total) : null,
            barLabelPlacement: 'outside',
          },
        ]}
        margin={{ left: 0, right: 48, top: 8, bottom: 24 }}
        hideLegend
        sx={{ '& .MuiBarLabel-root': { fontSize: 11, fill: tokens.muted } }}
      />
    </ChartCard>
  )
}