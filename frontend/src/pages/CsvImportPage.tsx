import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { importEmployeesCsv } from '../api/employees'
import type { CsvImportResponse } from '../types/api'

const TEMPLATE_HEADER = 'name,email,country,department,role,gender,hire_date,status,amount,currency'
const TEMPLATE_EXAMPLE =
  'Ada Lovelace,ada.lovelace@acme-corp.example,US,Engineering,Software Engineer I,female,2026-09-01,active,95000,USD'

function downloadTemplate() {
  const blob = new Blob([`${TEMPLATE_HEADER}\n${TEMPLATE_EXAMPLE}\n`], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'employee-import-template.csv'
  link.click()
  URL.revokeObjectURL(url)
}

export function CsvImportPage() {
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<CsvImportResponse | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file) return

    setError('')
    setResult(null)
    setSubmitting(true)
    try {
      const data = await importEmployeesCsv(file)
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
      <h1>Import employees from CSV</h1>
      <p className="muted">
        Each row creates one employee, and — if both amount and currency are provided — an
        initial "hire" salary record too. Required columns: name, email, country, department,
        role, hire_date. Optional: gender, status, amount, currency. A bad row is skipped and
        reported; it doesn't stop the rest of the file from importing.
      </p>
      <p>
        <button type="button" className="secondary" onClick={downloadTemplate}>
          Download CSV template
        </button>
      </p>

      <form className="card stacked-form employee-form" onSubmit={handleSubmit}>
        <label>
          CSV file
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
          />
        </label>

        {error && <p className="login-error">{error}</p>}

        <button type="submit" disabled={submitting || !file}>
          {submitting ? 'Importing…' : 'Import'}
        </button>
      </form>

      {result && (
        <div className="card result-card">
          <h2>Result</h2>
          <p>
            {result.created_count} of {result.total_rows} rows imported.
          </p>

          {result.salary_warnings.length > 0 && (
            <>
              <h3>Created without a starting salary</h3>
              <ul>
                {result.salary_warnings.map((warning) => (
                  <li key={warning.row_number}>
                    Row {warning.row_number}: {warning.reason}
                  </li>
                ))}
              </ul>
            </>
          )}

          {result.errors.length > 0 && (
            <>
              <h3>Rows skipped</h3>
              <ul>
                {result.errors.map((rowError) => (
                  <li key={rowError.row_number}>
                    Row {rowError.row_number}: {rowError.reason}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  )
}