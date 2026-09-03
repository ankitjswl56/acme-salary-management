import { useState } from 'react'
import { BarChart } from '@mui/x-charts/BarChart'
import Box from '@mui/material/Box'
import MenuItem from '@mui/material/MenuItem'
import Stack from '@mui/material/Stack'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { visuallyHidden } from '@mui/utils'
import { getSalaryByGender } from '../../api/analytics'
import { formatCount, formatUsd, formatUsdCompact, genderLabel } from '../../lib/format'
import type { GenderSalaryStats } from '../../types/api'
import { useChartTokens } from '../../theme'
import { ChartCard } from './ChartCard'
import { HatchSwatch } from './SuppressedNote'
import { useAnalyticsQuery } from './useAnalyticsQuery'

const ALL = '__all__'
const DEFAULT_MIN_GROUP_SIZE = 5
const GROUP_SIZES = [5, 10, 20]

// View 6: average current USD salary by gender, within an optional department
// scope. A group's figure is suppressed by the backend when its headcount is
// below the minimum - an average over a handful of people can expose an
// individual's pay. Suppressed groups are shown as a labelled state, never as
// a zero bar and never dropped silently.
//
// `initialData` is the all-departments / min-group-size-5 result from the one
// dashboard request; changing either filter fires this card's own fetch.
export function SalaryByGenderCard({
  initialData,
  departments,
  loading: pageLoading = false,
}: {
  initialData: GenderSalaryStats[]
  departments: string[]
  loading?: boolean
}) {
  const [department, setDepartment] = useState(ALL)
  const [minGroupSize, setMinGroupSize] = useState(DEFAULT_MIN_GROUP_SIZE)
  const isDefault = department === ALL && minGroupSize === DEFAULT_MIN_GROUP_SIZE
  const scoped = department === ALL ? undefined : department

  const { data, loading: queryLoading, error } = useAnalyticsQuery(
    () =>
      isDefault
        ? Promise.resolve(initialData)
        : getSalaryByGender({ department: scoped, minGroupSize }),
    `salary-by-gender:${department}:${minGroupSize}`,
  )
  const tokens = useChartTokens()

  const rows = isDefault ? initialData : (data ?? [])
  const loading = isDefault ? pageLoading : queryLoading
  const shown = rows.filter((r) => !r.suppressed && r.avg_salary_usd != null)
  const suppressed = rows.filter((r) => r.suppressed)
  const chartData = [...shown]
    .sort((a, b) => (b.avg_salary_usd ?? 0) - (a.avg_salary_usd ?? 0))
    .map((r) => ({ label: genderLabel(r.gender), avg_salary_usd: r.avg_salary_usd as number }))

  const filters = (
    <>
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
      <TextField
        select
        size="small"
        label="Min. group size"
        value={minGroupSize}
        onChange={(e) => setMinGroupSize(Number(e.target.value))}
        sx={{ minWidth: 140 }}
      >
        {GROUP_SIZES.map((n) => (
          <MenuItem key={n} value={n}>
            {n}
          </MenuItem>
        ))}
      </TextField>
    </>
  )

  const table = (
    <Table size="small" sx={{ '& td, & th': { fontVariantNumeric: 'tabular-nums' } }}>
      <caption style={visuallyHidden}>
        Average USD salary by gender. Groups below the minimum size are not shown.
      </caption>
      <TableHead>
        <TableRow>
          <TableCell>Gender</TableCell>
          <TableCell align="right">Headcount</TableCell>
          <TableCell align="right">Average salary</TableCell>
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
              {row.suppressed || row.avg_salary_usd == null ? (
                <Box component="span" sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
                  <HatchSwatch size={10} />
                  <Typography variant="caption" color="text.secondary">
                    Not shown
                  </Typography>
                </Box>
              ) : (
                formatUsd(row.avg_salary_usd)
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )

  return (
    <ChartCard
      title="Average salary by gender"
      description={`Within the selected scope. Groups under ${minGroupSize} people are withheld to protect individual pay.`}
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      actions={filters}
      table={table}
    >
      {chartData.length > 0 ? (
        <BarChart
          dataset={chartData}
          layout="horizontal"
          height={Math.max(150, chartData.length * 44 + 60)}
          colors={[tokens.seriesA]}
          yAxis={[{ scaleType: 'band', dataKey: 'label', width: 120 }]}
          xAxis={[{ valueFormatter: (v: number) => formatUsdCompact(v) }]}
          series={[
            {
              dataKey: 'avg_salary_usd',
              label: 'Average salary',
              valueFormatter: (v) => (v == null ? '—' : formatUsd(v)),
            },
          ]}
          margin={{ left: 0, right: 16, top: 8, bottom: 24 }}
          hideLegend
        />
      ) : (
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No group in this scope meets the minimum size of {minGroupSize}.
          </Typography>
        </Box>
      )}

      {suppressed.length > 0 && (
        <Stack spacing={0.5} sx={{ mt: 1.5 }}>
          {suppressed.map((row) => (
            <Box key={row.gender} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
              <HatchSwatch />
              <Typography variant="caption" color="text.secondary">
                {genderLabel(row.gender)} ({formatCount(row.headcount)}) — withheld, fewer than{' '}
                {minGroupSize} in group
              </Typography>
            </Box>
          ))}
        </Stack>
      )}
    </ChartCard>
  )
}