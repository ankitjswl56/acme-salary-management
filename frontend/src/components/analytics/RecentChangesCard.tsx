import { useState } from 'react'
import Chip from '@mui/material/Chip'
import MenuItem from '@mui/material/MenuItem'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import { getRecentChanges } from '../../api/analytics'
import { changeTypeLabel, formatUsd } from '../../lib/format'
import type { ChangeType } from '../../types/api'
import { ChartCard } from './ChartCard'
import { useAnalyticsQuery } from './useAnalyticsQuery'

const MONTHS = [3, 6, 12]
const CHANGE_TYPES: ChangeType[] = ['hire', 'raise', 'promotion', 'correction', 'cola']
const ALL = '__all__'
const LIMIT = 50

// View 7: raw feed of recent salary records - an ops/audit view, so it
// follows the actual records rather than the "current salary" resolution.
export function RecentChangesCard() {
  const [months, setMonths] = useState(3)
  const [changeType, setChangeType] = useState<string>(ALL)

  const { data, loading, error } = useAnalyticsQuery(
    () =>
      getRecentChanges({
        months,
        changeType: changeType === ALL ? undefined : (changeType as ChangeType),
        limit: LIMIT,
      }),
    `recent:${months}:${changeType}`,
  )

  const rows = data ?? []

  const filters = (
    <>
      <TextField
        select
        size="small"
        label="Window"
        value={months}
        onChange={(e) => setMonths(Number(e.target.value))}
        sx={{ minWidth: 140 }}
      >
        {MONTHS.map((m) => (
          <MenuItem key={m} value={m}>
            Last {m} months
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        size="small"
        label="Change type"
        value={changeType}
        onChange={(e) => setChangeType(e.target.value)}
        sx={{ minWidth: 160 }}
      >
        <MenuItem value={ALL}>All types</MenuItem>
        {CHANGE_TYPES.map((t) => (
          <MenuItem key={t} value={t}>
            {changeTypeLabel(t)}
          </MenuItem>
        ))}
      </TextField>
    </>
  )

  return (
    <ChartCard
      title="Recent salary changes"
      description={`Salary records dated within the selected window (up to ${LIMIT}).`}
      loading={loading}
      error={error}
      isEmpty={rows.length === 0}
      actions={filters}
    >
      <TableContainer sx={{ maxHeight: 460 }}>
        <Table size="small" stickyHeader sx={{ '& td:last-of-type, & th:last-of-type, & td:nth-of-type(6), & th:nth-of-type(6)': { fontVariantNumeric: 'tabular-nums' } }}>
          <TableHead>
            <TableRow>
              <TableCell>Effective</TableCell>
              <TableCell>Employee</TableCell>
              <TableCell>Department</TableCell>
              <TableCell>Country</TableCell>
              <TableCell>Type</TableCell>
              <TableCell align="right">Amount</TableCell>
              <TableCell align="right">USD</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={`${row.employee_id}-${row.effective_date}-${i}`} hover>
                <TableCell>{row.effective_date}</TableCell>
                <TableCell>{row.employee_name}</TableCell>
                <TableCell>{row.department}</TableCell>
                <TableCell>{row.country}</TableCell>
                <TableCell>
                  <Chip label={changeTypeLabel(row.change_type)} size="small" variant="outlined" />
                </TableCell>
                <TableCell align="right">
                  {row.amount.toLocaleString()} {row.currency}
                </TableCell>
                <TableCell align="right">{formatUsd(row.amount_usd)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </ChartCard>
  )
}