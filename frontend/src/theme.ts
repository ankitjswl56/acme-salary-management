import { createTheme, useTheme, type Theme } from '@mui/material/styles'

// The Phase 1-6 pages are styled by src/index.css, which keys off the OS
// `prefers-color-scheme`. The MUI theme (Phase 7 dashboard only) follows the
// same signal so the two styling systems agree on light vs dark. No
// CssBaseline is used - it would restyle the hand-rolled pages.

const SYSTEM_SANS = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'

// --- Dashboard visual language -------------------------------------------------
// Bond-indigo + brass-gold on a near-white surface: a "statement / ledger"
// pairing, deliberately not the default chart-library blue+orange. Series
// hexes are validated with the dataviz palette checker (CVD deltaE >= 18 both
// modes, contrast >= 3:1). See docs/design-notes.md for the rationale.

interface ChartTokens {
  /** Primary series - single-series bars, and "Average" in a 2-series chart. */
  seriesA: string
  /** Secondary series - "Median" in a 2-series chart. */
  seriesB: string
  /** Axis lines, ticks, and chart text. */
  ink: string
  /** Gridlines, secondary labels. */
  muted: string
  /** Suppressed / no-data fill (paired with a hatch pattern + literal text). */
  suppressed: string
  /** Reserved: the one place a value can be "bad" - a QoQ payroll drop. */
  alert: string
}

const CHART_TOKENS: Record<'light' | 'dark', ChartTokens> = {
  light: {
    seriesA: '#3A4E9C',
    seriesB: '#BE8636',
    ink: '#1B2733',
    muted: '#5B6570',
    suppressed: '#8A9199',
    alert: '#B23B3B',
  },
  dark: {
    seriesA: '#7C8EDC',
    seriesB: '#BE8636',
    ink: '#E6E9EC',
    muted: '#8A929C',
    suppressed: '#8A9199',
    alert: '#D97A6A',
  },
}

export function buildTheme(mode: 'light' | 'dark'): Theme {
  const dark = mode === 'dark'
  return createTheme({
    palette: {
      mode,
      // Matches --accent in index.css so buttons/links look the same across
      // the two styling systems.
      primary: { main: dark ? '#a78bfa' : '#6d28d9' },
      background: {
        default: dark ? '#14161c' : '#f7f7f9',
        paper: dark ? '#1c1f28' : '#ffffff',
      },
      divider: dark ? '#2c2f3a' : '#e2e2e7',
      text: {
        primary: dark ? '#e6e9ec' : '#1b2733',
        secondary: dark ? '#8a929c' : '#5b6570',
      },
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: SYSTEM_SANS,
      // The small-caps "ledger" label that sits above a figure.
      overline: {
        fontSize: '0.72rem',
        fontWeight: 600,
        letterSpacing: '0.06em',
        lineHeight: 1.4,
      },
    },
    components: {
      // Depth comes from a hairline border + the surface/page contrast, not
      // from elevation. No drop shadows anywhere on the dashboard.
      MuiCard: {
        defaultProps: { variant: 'outlined', elevation: 0 },
        styleOverrides: { root: { boxShadow: 'none', backgroundImage: 'none' } },
      },
      MuiPaper: {
        styleOverrides: { root: { backgroundImage: 'none' } },
      },
    },
  })
}

/** Chart color/ink tokens for the active light/dark mode. */
export function useChartTokens(): ChartTokens {
  const theme = useTheme()
  return CHART_TOKENS[theme.palette.mode === 'dark' ? 'dark' : 'light']
}