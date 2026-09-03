import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { useChartTokens } from '../../theme'

/** 45-degree hatch swatch - the pattern channel for a suppressed value, so it
 * never reads as a real (zero) bar and never relies on color alone. */
export function HatchSwatch({ size = 12 }: { size?: number }) {
  const { suppressed } = useChartTokens()
  return (
    <Box
      component="span"
      aria-hidden
      sx={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '2px',
        border: `1px solid ${suppressed}`,
        backgroundImage: `repeating-linear-gradient(45deg, ${suppressed} 0 1.5px, transparent 1.5px 4px)`,
      }}
    />
  )
}

/** Inline explanation shown wherever the min-group-size rule suppresses a
 * figure - pattern + literal text, per the privacy rule in CLAUDE.md. */
export function SuppressedNote({ minGroupSize }: { minGroupSize: number }) {
  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
      <HatchSwatch />
      <Typography variant="caption" color="text.secondary">
        Not shown — fewer than {minGroupSize} in group
      </Typography>
    </Box>
  )
}