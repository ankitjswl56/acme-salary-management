import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { getEmployee, updateEmployee } from '../api/employees'
import { EmployeeForm, type EmployeeFormValues } from '../components/EmployeeForm'
import type { EmployeeDetail } from '../types/api'

export function EmployeeEditPage() {
  const { id } = useParams<{ id: string }>()
  const employeeId = Number(id)
  const navigate = useNavigate()

  const [employee, setEmployee] = useState<EmployeeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')

    getEmployee(employeeId)
      .then((data) => {
        if (!cancelled) setEmployee(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Failed to load this employee.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [employeeId])

  async function handleSubmit(values: EmployeeFormValues) {
    await updateEmployee(employeeId, {
      name: values.name,
      email: values.email,
      country: values.country,
      department: values.department,
      role: values.role,
      gender: values.gender || null,
      hire_date: values.hire_date,
      status: values.status,
    })
    navigate(`/employees/${employeeId}`, { replace: true })
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
        <Link to={`/employees/${employeeId}`}>← Back to employee</Link>
      </p>
      <h1>Edit {employee.name}</h1>
      <EmployeeForm
        submitLabel="Save changes"
        initialValues={{
          name: employee.name,
          email: employee.email,
          country: employee.country,
          department: employee.department,
          role: employee.role,
          gender: employee.gender ?? '',
          hire_date: employee.hire_date,
          status: employee.status,
        }}
        onSubmit={handleSubmit}
      />
    </div>
  )
}