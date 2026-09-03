// Shared number/label formatting for the analytics dashboard.

const USD_0 = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

const NUM_0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 })

/** Whole-dollar USD, e.g. "$98,200". */
export function formatUsd(value: number): string {
  return USD_0.format(value)
}

/** Compact USD for axis ticks and large totals, e.g. "$1.2M", "$690M". */
export function formatUsdCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000) return `$${Math.round(value / 1_000)}k`
  return `$${Math.round(value)}`
}

/** Thousands-separated integer, e.g. "10,000". */
export function formatCount(value: number): string {
  return NUM_0.format(value)
}

/** Fraction (0-1) as a whole-number percent, e.g. "47%". */
export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`
}

/** Fraction (0-1) as a one-decimal percent, e.g. "3.6%". */
export function formatPercent1(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`
}

/** Signed one-decimal percent for deltas, e.g. "+3.6%", "-1.2%". */
export function formatSignedPercent(fraction: number): string {
  const sign = fraction > 0 ? '+' : fraction < 0 ? '−' : ''
  return `${sign}${Math.abs(fraction * 100).toFixed(1)}%`
}

const GENDER_LABELS: Record<string, string> = {
  male: 'Male',
  female: 'Female',
  other: 'Other',
  prefer_not_to_say: 'Prefer not to say',
  unspecified: 'Unspecified',
}

export function genderLabel(value: string): string {
  return GENDER_LABELS[value] ?? value
}

const CHANGE_TYPE_LABELS: Record<string, string> = {
  hire: 'Hire',
  raise: 'Raise',
  promotion: 'Promotion',
  correction: 'Correction',
  cola: 'Cost-of-living',
}

export function changeTypeLabel(value: string): string {
  return CHANGE_TYPE_LABELS[value] ?? value
}