// Formatting for the NL-query result table. Split out from NLQueryBox so the
// column/value logic can be unit-tested without rendering.

/** snake_case / snake_case_usd -> "Snake Case". */
export function titleCase(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Render one cell. Money-ish columns get USD; other numbers get grouping;
 *  null/undefined shows an em dash. */
export function formatCell(key: string, value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    return key.endsWith('_usd') || key.includes('payroll') || key.includes('salary')
      ? value.toLocaleString('en-US', {
          style: 'currency',
          currency: 'USD',
          maximumFractionDigits: 0,
        })
      : value.toLocaleString('en-US')
  }
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return String(value)
}

/** Columns for a result table: the union of keys across all rows, first-seen
 *  order. Returns null when `data` isn't a non-empty array of objects. */
export function inferColumns(data: unknown): string[] | null {
  if (!Array.isArray(data) || data.length === 0) return null
  if (typeof data[0] !== 'object' || data[0] === null) return null
  const rows = data as Array<Record<string, unknown>>
  return Array.from(new Set(rows.flatMap((row) => Object.keys(row))))
}