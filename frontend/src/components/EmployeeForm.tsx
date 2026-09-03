import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getFilterOptions } from '../api/employees'
import type { CountryOption, EmployeeStatus, Gender } from '../types/api'

export interface EmployeeFormValues {
  name: string
  email: string
  country: string
  department: string
  role: string
  gender: Gender | ''
  hire_date: string
  status: EmployeeStatus
}

const EMPTY_VALUES: EmployeeFormValues = {
  name: '',
  email: '',
  country: '',
  department: '',
  role: '',
  gender: '',
  hire_date: '',
  status: 'active',
}

interface EmployeeFormProps {
  initialValues?: Partial<EmployeeFormValues>
  submitLabel: string
  onSubmit: (values: EmployeeFormValues) => Promise<void>
}

export function EmployeeForm({ initialValues, submitLabel, onSubmit }: EmployeeFormProps) {
  const [values, setValues] = useState<EmployeeFormValues>({ ...EMPTY_VALUES, ...initialValues })
  const [countries, setCountries] = useState<CountryOption[]>([])
  const [departments, setDepartments] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Dropdown, matching the list-filter page's country/department selects
  // and the Status select below. Note: sourced from data actually in use,
  // so a completely empty, unseeded database would have no options here -
  // acceptable since this app is always seeded before real use.
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

  function update<K extends keyof EmployeeFormValues>(key: K, value: EmployeeFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await onSubmit(values)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <form className="card stacked-form employee-form" onSubmit={handleSubmit}>
      <label>
        Name
        <input value={values.name} onChange={(event) => update('name', event.target.value)} required />
      </label>

      <label>
        Email
        <input
          type="email"
          value={values.email}
          onChange={(event) => update('email', event.target.value)}
          required
        />
      </label>

      <label>
        Country
        <select value={values.country} onChange={(event) => update('country', event.target.value)} required>
          <option value="" disabled>
            Select a country
          </option>
          {countries.map(({ code, name }) => (
            <option key={code} value={code}>
              {name} ({code})
            </option>
          ))}
        </select>
      </label>

      <label>
        Department
        <select
          value={values.department}
          onChange={(event) => update('department', event.target.value)}
          required
        >
          <option value="" disabled>
            Select a department
          </option>
          {departments.map((department) => (
            <option key={department} value={department}>
              {department}
            </option>
          ))}
        </select>
      </label>

      <label>
        Role / title
        <input value={values.role} onChange={(event) => update('role', event.target.value)} required />
      </label>

      <label>
        Gender
        <select value={values.gender} onChange={(event) => update('gender', event.target.value as Gender | '')}>
          <option value="">Not specified</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
          <option value="other">Other</option>
          <option value="prefer_not_to_say">Prefer not to say</option>
        </select>
      </label>

      <label>
        Hire date
        <input
          type="date"
          value={values.hire_date}
          onChange={(event) => update('hire_date', event.target.value)}
          required
        />
      </label>

      <label>
        Status
        <select value={values.status} onChange={(event) => update('status', event.target.value as EmployeeStatus)}>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </label>

      {error && <p className="login-error">{error}</p>}

      <button type="submit" disabled={submitting}>
        {submitting ? 'Saving…' : submitLabel}
      </button>
    </form>
  )
}