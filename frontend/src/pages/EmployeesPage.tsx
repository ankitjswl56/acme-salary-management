import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { getFilterOptions, listEmployees } from '../api/employees'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { CountryOption, EmployeeRead, EmployeeStatus } from '../types/api'

const PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300

export function EmployeesPage() {
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, SEARCH_DEBOUNCE_MS)
  const [country, setCountry] = useState('')
  const [department, setDepartment] = useState('')
  const [status, setStatus] = useState<EmployeeStatus | ''>('')
  const [page, setPage] = useState(0)

  const [countries, setCountries] = useState<CountryOption[]>([])
  const [departments, setDepartments] = useState<string[]>([])

  const [items, setItems] = useState<EmployeeRead[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Dropdown options change rarely (only when a new country/department
  // shows up in the data) - fetched once, not on every filter change.
  useEffect(() => {
    getFilterOptions()
      .then((data) => {
        setCountries(data.countries)
        setDepartments(data.departments)
      })
      .catch(() => {
        // Non-critical: filters just fall back to empty dropdowns.
      })
  }, [])

  // A filter change should reset back to page 0 - otherwise a narrower
  // filter could land on a now-empty page past the new result count.
  useEffect(() => {
    setPage(0)
  }, [debouncedSearch, country, department, status])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    listEmployees({
      search: debouncedSearch || undefined,
      country: country || undefined,
      department: department || undefined,
      status: status || undefined,
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        if (cancelled) return
        setItems(data.items)
        setTotal(data.total)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load employees.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedSearch, country, department, status, page])

  const from = total === 0 ? 0 : page * PAGE_SIZE + 1
  const to = Math.min(total, (page + 1) * PAGE_SIZE)

  return (
    <div>
      <div className="page-header">
        <h1>Employees</h1>
        <div className="page-header-actions">
          <Link to="/employees/import">
            <button type="button" className="secondary">
              Import CSV
            </button>
          </Link>
          <Link to="/employees/bulk-raise">
            <button type="button" className="secondary">
              Bulk raise
            </button>
          </Link>
          <Link to="/employees/new">
            <button type="button">New employee</button>
          </Link>
        </div>
      </div>

      <div className="filters">
        <input
          placeholder="Search name or email"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select value={country} onChange={(event) => setCountry(event.target.value)}>
          <option value="">All countries</option>
          {countries.map(({ code, name }) => (
            <option key={code} value={code}>
              {name} ({code})
            </option>
          ))}
        </select>
        <select value={department} onChange={(event) => setDepartment(event.target.value)}>
          <option value="">All departments</option>
          {departments.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value as EmployeeStatus | '')}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      {error && <p className="login-error">{error}</p>}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Country</th>
                <th>Department</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map((employee) => (
                <tr key={employee.id}>
                  <td>
                    <Link to={`/employees/${employee.id}`}>{employee.name}</Link>
                  </td>
                  <td>{employee.email}</td>
                  <td>{employee.country}</td>
                  <td>{employee.department}</td>
                  <td>{employee.role}</td>
                  <td>{employee.status}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
                    No employees match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="pagination">
            <span className="muted">
              {from}–{to} of {total}
            </span>
            <button className="secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <button className="secondary" disabled={to >= total} onClick={() => setPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}