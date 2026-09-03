import { useId, useState, type ReactNode } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Collapse from '@mui/material/Collapse'
import CircularProgress from '@mui/material/CircularProgress'
import Typography from '@mui/material/Typography'
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined'

interface ChartCardProps {
  title: string
  description?: string
  loading?: boolean
  error?: string
  /** True when the request succeeded but returned nothing to plot. */
  isEmpty?: boolean
  /** Filter controls, rendered in one row under the header. */
  actions?: ReactNode
  /** Plain data table for this view - every chart ships one (a11y / exact numbers). */
  table?: ReactNode
  children: ReactNode
}

export function ChartCard({
  title,
  description,
  loading = false,
  error = '',
  isEmpty = false,
  actions,
  table,
  children,
}: ChartCardProps) {
  const [showTable, setShowTable] = useState(false)
  const tableId = useId()

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flex: 1, '&:last-child': { pb: 2 } }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 1,
            mb: description ? 0.5 : 1.5,
          }}
        >
          <Typography variant="subtitle2" component="h3" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
          {table && (
            <Button
              size="small"
              color="inherit"
              aria-expanded={showTable}
              aria-controls={tableId}
              startIcon={<TableChartOutlinedIcon fontSize="small" />}
              onClick={() => setShowTable((v) => !v)}
              sx={{ flexShrink: 0, mt: -0.5, color: 'text.secondary' }}
            >
              {showTable ? 'Hide data' : 'Show data'}
            </Button>
          )}
        </Box>

        {description && (
          <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1.5 }}>
            {description}
          </Typography>
        )}

        {actions && (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2 }}>{actions}</Box>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={28} />
          </Box>
        ) : error ? (
          <Alert severity="error" variant="outlined">
            {error}
          </Alert>
        ) : isEmpty ? (
          <Box sx={{ py: 6, textAlign: 'center', color: 'text.secondary' }}>
            No data to display.
          </Box>
        ) : (
          <>
            {children}
            {table && (
              <Collapse in={showTable} unmountOnExit id={tableId}>
                <Box sx={{ mt: 2, overflowX: 'auto' }}>{table}</Box>
              </Collapse>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}