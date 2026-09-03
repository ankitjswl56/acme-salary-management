import type { ReactNode } from 'react'
import Box from '@mui/material/Box'
import Skeleton from '@mui/material/Skeleton'
import Typography from '@mui/material/Typography'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import { useChartTokens } from '../../theme'

export interface StatDelta {
  /** Pre-formatted, signed, e.g. "+3.6%". */
  label: string
  direction: 'up' | 'down' | 'flat'
  /** e.g. "vs. last quarter". */
  caption: string
}

interface StatTileProps {
  label: string
  value: string
  /** The headline tile renders larger; it's the one deliberately bold moment. */
  emphasis?: 'headline' | 'regular'
  delta?: StatDelta
  sparkline?: ReactNode
  loading?: boolean
}

export function StatTile({
  label,
  value,
  emphasis = 'regular',
  delta,
  sparkline,
  loading = false,
}: StatTileProps) {
  const tokens = useChartTokens()
  const headline = emphasis === 'headline'

  // "Down" is the only direction allowed the reserved alert color; "up" stays
  // factual ink - a rising payroll isn't inherently good or bad.
  const deltaColor =
    delta?.direction === 'down' ? tokens.alert : 'text.secondary'
  const DeltaIcon = delta?.direction === 'down' ? ArrowDownwardIcon : ArrowUpwardIcon

  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="overline" component="div" color="text.secondary">
        {label}
      </Typography>

      {loading ? (
        <Skeleton variant="text" width={headline ? 200 : 120} height={headline ? 56 : 40} />
      ) : (
        <Typography
          component="div"
          sx={{
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
            letterSpacing: '-0.01em',
            lineHeight: 1.1,
            fontSize: headline ? 'clamp(2.25rem, 4vw, 2.9rem)' : '1.6rem',
            color: 'text.primary',
          }}
        >
          {value}
        </Typography>
      )}

      {headline && !loading && (
        // Brass rule under the single most important figure - the one place
        // the "value" colour appears in the page chrome.
        <Box sx={{ width: 44, height: 3, mt: 1, borderRadius: 1, bgcolor: tokens.seriesB }} />
      )}

      {(delta || sparkline) && !loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.75 }}>
          {delta && delta.direction !== 'flat' && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25, color: deltaColor }}>
              <DeltaIcon sx={{ fontSize: '1rem' }} />
              <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>
                {delta.label}
              </Typography>
            </Box>
          )}
          {delta && (
            <Typography variant="caption" color="text.secondary">
              {delta.caption}
            </Typography>
          )}
          {sparkline && <Box sx={{ ml: 'auto', display: 'flex' }}>{sparkline}</Box>}
        </Box>
      )}
    </Box>
  )
}