import { describe, expect, it } from 'vitest'
import { formatCell, inferColumns, titleCase } from './nlQueryFormat'

describe('titleCase', () => {
  it('turns snake_case into spaced Title Case', () => {
    expect(titleCase('country')).toBe('Country')
    expect(titleCase('avg_salary_usd')).toBe('Avg Salary Usd')
    expect(titleCase('total_payroll_usd')).toBe('Total Payroll Usd')
  })
})

describe('formatCell', () => {
  it('formats money-ish columns as whole-dollar USD', () => {
    expect(formatCell('avg_salary_usd', 91405)).toBe('$91,405')
    expect(formatCell('total_payroll_usd', 1234567)).toBe('$1,234,567')
    expect(formatCell('median_salary', 50000)).toBe('$50,000') // matched via "salary"
  })

  it('groups other numbers without a currency symbol', () => {
    expect(formatCell('headcount', 3198)).toBe('3,198')
    expect(formatCell('quarters', 8)).toBe('8')
  })

  it('shows an em dash for null/undefined (e.g. a suppressed average)', () => {
    expect(formatCell('avg_salary_usd', null)).toBe('—')
    expect(formatCell('avg_salary_usd', undefined)).toBe('—')
  })

  it('renders booleans and strings plainly', () => {
    expect(formatCell('suppressed', true)).toBe('yes')
    expect(formatCell('suppressed', false)).toBe('no')
    expect(formatCell('gender', 'female')).toBe('female')
    expect(formatCell('quarter', '2026-Q3')).toBe('2026-Q3')
  })
})

describe('inferColumns', () => {
  it('returns the union of keys across rows, first-seen order', () => {
    const rows = [
      { country: 'US', headcount: 1 },
      { country: 'DE', headcount: 2, note: 'x' },
    ]
    expect(inferColumns(rows)).toEqual(['country', 'headcount', 'note'])
  })

  it('returns null for anything that is not a non-empty array of objects', () => {
    expect(inferColumns([])).toBeNull()
    expect(inferColumns('nope')).toBeNull()
    expect(inferColumns([1, 2, 3])).toBeNull()
    expect(inferColumns(null)).toBeNull()
    expect(inferColumns({ country: 'US' })).toBeNull()
  })
})