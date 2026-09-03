import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { getFilterOptions, listEmployees } from '../api/employees'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { CountryOption, EmployeeRead, EmployeeStatus } from '../types/api'

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
const DEFAULT_PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300

function parsePage(value: string | null): number {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1
}

function parsePageSize(value: string | null): number {
  const parsed = Number(value)
  return PAGE_SIZE_OPTIONS.includes(parsed) ? parsed : DEFAULT_PAGE_SIZE
}

// Filters and pagination live in the URL (not just component state), so a
// browser refresh keeps the same view instead of silently resetting it,
// and the current view is bookmarkable/shareable as an ordinary link.
export function EmployeesPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const country = searchParams.get('country') ?? ''
  const department = searchParams.get('department') ?? ''
  const status = (searchParams.get('status') ?? '') as EmployeeStatus | ''
  const page = parsePage(searchParams.get('page'))
  const pageSize = parsePageSize(searchParams.get('pageSize'))

  // Raw search text is local state, not read from the URL on every
  // keystroke - only the debounced value is written back to the URL, so
  // typing doesn't spam browser history or fire a request per letter.
  const [searchInput, setSearchInput] = useState(searchParams.get('search') ?? '')
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS)

  const [pageInput, setPageInput] = useState(String(page))
  useEffect(() => setPageInput(String(page)), [page])

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

  // Once the debounce settles, push the search text into the URL (if it
  // actually changed) and reset back to page 1 - a new search could land
  // on a now out-of-range page otherwise.
  useEffect(() => {
    if (debouncedSearch === (searchParams.get('search') ?? '')) return
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous)
        if (debouncedSearch) next.set('search', debouncedSearch)
        else next.delete('search')
        next.set('page', '1')
        return next
      },
      { replace: true },
    )
    // Only the debounced value should trigger this - searchParams/setSearchParams
    // intentionally excluded to avoid re-running on every URL change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch])

  function updateFilter(key: string, value: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      if (value) next.set(key, value)
      else next.delete(key)
      next.set('page', '1')
      return next
    })
  }

  function updatePageSize(value: string) {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      next.set('pageSize', value)
      next.set('page', '1')
      return next
    })
  }

  function goToPage(target: number) {
    const clamped = Math.max(1, Math.min(target, totalPages))
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous)
      next.set('page', String(clamped))
      return next
    })
  }

  function handlePageInputSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    goToPage(Number(pageInput))
  }

  function handleReset() {
    setSearchInput('')
    setSearchParams({})
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    listEmployees({
      search: debouncedSearch || undefined,
      country: country || undefined,
      department: department || undefined,
      status: status || undefined,
      skip: (page - 1) * pageSize,
      limit: pageSize,
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
  }, [debouncedSearch, country, department, status, page, pageSize])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  const hasActiveFilters = Boolean(searchInput || country || department || status)

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
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
        />
        <select value={country} onChange={(event) => updateFilter('country', event.target.value)}>
          <option value="">All countries</option>
          {countries.map(({ code, name }) => (
            <option key={code} value={code}>
              {name} ({code})
            </option>
          ))}
        </select>
        <select value={department} onChange={(event) => updateFilter('department', event.target.value)}>
          <option value="">All departments</option>
          {departments.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <select value={status} onChange={(event) => updateFilter('status', event.target.value)}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
        <button type="button" className="secondary" onClick={handleReset} disabled={!hasActiveFilters}>
          Reset
        </button>
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
            <label className="page-size-select">
              Rows per page
              <select value={pageSize} onChange={(event) => updatePageSize(event.target.value)}>
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </label>

            <span className="muted">
              {from}–{to} of {total}
            </span>

            <button className="secondary" disabled={page <= 1} onClick={() => goToPage(page - 1)}>
              Previous
            </button>

            <form className="page-jump" onSubmit={handlePageInputSubmit}>
              <span className="muted">Page</span>
              <input
                type="number"
                min={1}
                max={totalPages}
                value={pageInput}
                onChange={(event) => setPageInput(event.target.value)}
              />
              <span className="muted">of {totalPages}</span>
              <button type="submit" className="secondary">
                Go
              </button>
            </form>

            <button className="secondary" disabled={page >= totalPages} onClick={() => goToPage(page + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}