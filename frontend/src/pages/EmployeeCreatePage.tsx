import { Link, useNavigate } from 'react-router-dom'
import { EmployeeForm, type EmployeeFormValues } from '../components/EmployeeForm'
import { createEmployee } from '../api/employees'

export function EmployeeCreatePage() {
  const navigate = useNavigate()

  async function handleSubmit(values: EmployeeFormValues) {
    const created = await createEmployee({
      name: values.name,
      email: values.email,
      country: values.country,
      department: values.department,
      role: values.role,
      gender: values.gender || null,
      hire_date: values.hire_date,
      status: values.status,
    })
    navigate(`/employees/${created.id}`, { replace: true })
  }

  return (
    <div>
      <p>
        <Link to="/employees">← Back to employees</Link>
      </p>
      <h1>New employee</h1>
      <EmployeeForm submitLabel="Create employee" onSubmit={handleSubmit} />
    </div>
  )
}