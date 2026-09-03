// Mirrors backend/app/schemas/employee.py and backend/app/models/enums.py.
// Keep in sync by hand — no shared codegen between the two yet.

export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say'

export type EmployeeStatus = 'active' | 'inactive'

// ChangeType.raise_'s wire value is "raise" (see enums.py's enum_column
// comment) - the Python member name differs from the value on the backend,
// but the value is what actually crosses the API boundary.
export type ChangeType = 'hire' | 'raise' | 'promotion' | 'correction' | 'cola'

// Dates cross the wire as ISO "YYYY-MM-DD" strings (Pydantic's default date
// serialization), not Date objects - typed as `string` throughout, parsed
// only where a component actually needs a Date.

export interface EmployeeCreate {
  name: string
  email: string
  country: string
  department: string
  role: string
  gender?: Gender | null
  hire_date: string
  status?: EmployeeStatus
}

export interface EmployeeUpdate {
  name?: string
  email?: string
  country?: string
  department?: string
  role?: string
  gender?: Gender | null
  hire_date?: string
  status?: EmployeeStatus
}

export interface EmployeeRead {
  id: number
  name: string
  email: string
  country: string
  department: string
  role: string
  gender: Gender | null
  hire_date: string
  status: EmployeeStatus
}

export interface CurrentSalaryRead {
  amount: number
  currency: string
  amount_usd_snapshot: number
  effective_date: string
  change_type: ChangeType
}

export interface EmployeeDetail extends EmployeeRead {
  current_salary: CurrentSalaryRead | null
}

export interface EmployeeListResponse {
  total: number
  items: EmployeeRead[]
}