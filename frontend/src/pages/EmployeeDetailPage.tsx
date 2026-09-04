import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { createSalaryRecord, getEmployee, getSalaryHistory } from '../api/employees'
import { AddSalaryRecordForm } from '../components/AddSalaryRecordForm'
import type { EmployeeDetail, SalaryRecordCreate, SalaryRecordRead } from '../types/api'

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const employeeId = Number(id)

  const [employee, setEmployee] = useState<EmployeeDetail | null>(null)
  const [history, setHistory] = useState<SalaryRecordRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)

  const load = useCallback(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    Promise.all([getEmployee(employeeId), getSalaryHistory(employeeId)])
      .then(([employeeData, historyData]) => {
        if (cancelled) return
        setEmployee(employeeData)
        setHistory(historyData)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof ApiError ? err.message : 'Failed to load this employee.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [employeeId])

  useEffect(() => load(), [load])

  async function handleAddSalaryRecord(values: SalaryRecordCreate) {
    await createSalaryRecord(employeeId, values)
    setShowAddForm(false)
    load() // current salary and history may both have changed
  }

  if (loading) {
    return <p className="muted">Loading…</p>
  }

  if (error) {
    return <p className="login-error">{error}</p>
  }

  if (!employee) {
    return null
  }

  return (
    <div>
      <p>
        <Link to="/employees">← Back to employees</Link>
      </p>
      <div className="page-header">
        <h1>{employee.name}</h1>
        <Link to={`/employees/${employee.id}/edit`}>
          <button type="button" className="secondary">
            Edit
          </button>
        </Link>
      </div>

      <div className="card detail-grid">
        <span className="muted">Email</span>
        <span>{employee.email}</span>
        <span className="muted">Country</span>
        <span>{employee.country}</span>
        <span className="muted">Department</span>
        <span>{employee.department}</span>
        <span className="muted">Role</span>
        <span>{employee.role}</span>
        <span className="muted">Gender</span>
        <span>{employee.gender ?? '—'}</span>
        <span className="muted">Hire date</span>
        <span>{employee.hire_date}</span>
        <span className="muted">Status</span>
        <span>
          <span className={`status-badge ${employee.status}`}>{employee.status}</span>
        </span>
      </div>

      <h2>Current salary</h2>
      {employee.current_salary ? (
        <div className="card">
          <p>
            {employee.current_salary.amount.toLocaleString()} {employee.current_salary.currency}{' '}
            <span className="muted">
              (≈ {employee.current_salary.amount_usd_snapshot.toLocaleString()} USD)
            </span>
          </p>
          <p className="muted">
            Effective {employee.current_salary.effective_date} · {employee.current_salary.change_type}
          </p>
        </div>
      ) : (
        <p className="muted">No current salary on record.</p>
      )}

      <div className="page-header">
        <h2>Salary history</h2>
        {!showAddForm && (
          <button type="button" onClick={() => setShowAddForm(true)}>
            Add salary record
          </button>
        )}
      </div>

      {showAddForm && (
        <AddSalaryRecordForm
          hasExistingHistory={history.length > 0}
          onSubmit={handleAddSalaryRecord}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      <table>
        <thead>
          <tr>
            <th>Effective date</th>
            <th>Type</th>
            <th>Amount</th>
            <th>USD equivalent</th>
          </tr>
        </thead>
        <tbody>
          {history.map((record) => (
            <tr key={record.id}>
              <td>{record.effective_date}</td>
              <td>{record.change_type}</td>
              <td>
                {record.amount.toLocaleString()} {record.currency}
              </td>
              <td>{record.amount_usd_snapshot.toLocaleString()}</td>
            </tr>
          ))}
          {history.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                No salary history.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}