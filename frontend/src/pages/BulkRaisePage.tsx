import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { applyBulkRaise, getFilterOptions } from '../api/employees'
import type { BulkRaiseResponse, ChangeType, CountryOption } from '../types/api'

export function BulkRaisePage() {
  const [percentage, setPercentage] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [changeType, setChangeType] = useState<ChangeType>('raise')
  const [country, setCountry] = useState('')
  const [department, setDepartment] = useState('')

  const [countries, setCountries] = useState<CountryOption[]>([])
  const [departments, setDepartments] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<BulkRaiseResponse | null>(null)

  useEffect(() => {
    getFilterOptions()
      .then((data) => {
        setCountries(data.countries)
        setDepartments(data.departments)
      })
      .catch(() => {
        // Non-critical: dropdowns just stay empty if this fails.
      })
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setResult(null)

    const scope =
      [country && `country = ${country}`, department && `department = ${department}`].filter(Boolean).join(', ') ||
      'all active employees'
    const confirmed = window.confirm(
      `Apply a ${percentage}% ${changeType} effective ${effectiveDate} to active employees matching: ${scope}?\n\nThis creates a new salary record for every matching employee and can't be undone with one click.`,
    )
    if (!confirmed) return

    setSubmitting(true)
    try {
      const data = await applyBulkRaise({
        percentage: Number(percentage),
        effective_date: effectiveDate,
        change_type: changeType,
        country: country || undefined,
        department: department || undefined,
      })
      setResult(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <p>
        <Link to="/employees">← Back to employees</Link>
      </p>
      <h1>Bulk raise</h1>
      <p className="muted">
        Applies a uniform percentage change to every active employee matching the filters below.
        Leave country/department blank to apply organization-wide. Inactive employees are never
        included.
      </p>

      <form className="card stacked-form employee-form" onSubmit={handleSubmit}>
        <label>
          Change type
          <select value={changeType} onChange={(event) => setChangeType(event.target.value as ChangeType)}>
            <option value="raise">Raise</option>
            <option value="cola">Cost-of-living adjustment</option>
          </select>
        </label>

        <label>
          Percentage increase
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={percentage}
            onChange={(event) => setPercentage(event.target.value)}
            placeholder="e.g. 5 for a 5% raise"
            required
          />
        </label>

        <label>
          Effective date
          <input
            type="date"
            value={effectiveDate}
            onChange={(event) => setEffectiveDate(event.target.value)}
            required
          />
        </label>

        <label>
          Country <span className="muted">(optional)</span>
          <select value={country} onChange={(event) => setCountry(event.target.value)}>
            <option value="">All countries</option>
            {countries.map(({ code, name }) => (
              <option key={code} value={code}>
                {name} ({code})
              </option>
            ))}
          </select>
        </label>

        <label>
          Department <span className="muted">(optional)</span>
          <select value={department} onChange={(event) => setDepartment(event.target.value)}>
            <option value="">All departments</option>
            {departments.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        {error && <p className="login-error">{error}</p>}

        <button type="submit" disabled={submitting}>
          {submitting ? 'Applying…' : 'Apply raise'}
        </button>
      </form>

      {result && (
        <div className="card result-card">
          <h2>Result</h2>
          <p>
            {result.applied_count} of {result.matched_count} matching employees updated.
          </p>
          {result.skipped_no_current_salary > 0 && (
            <p className="muted">
              {result.skipped_no_current_salary} skipped — no current salary on record yet.
            </p>
          )}
          {result.skipped_effective_date_before_hire > 0 && (
            <p className="muted">
              {result.skipped_effective_date_before_hire} skipped — effective date is before hire date.
            </p>
          )}
        </div>
      )}
    </div>
  )
}