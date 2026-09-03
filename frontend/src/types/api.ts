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

// Distinct country/department values actually in use, for filter dropdowns
// - not a hardcoded list, since country/department aren't locked to a fixed
// enum on the backend the way gender/status/change_type are. Employee.country
// stores a reference-data code (e.g. "US"); the backend resolves each to its
// display name for the dropdown label, while `code` stays what's sent back
// as the actual filter value.
export interface CountryOption {
  code: string
  name: string
}

export interface EmployeeFilterOptions {
  countries: CountryOption[]
  departments: string[]
}

export interface SalaryRecordCreate {
  amount: number
  currency: string
  effective_date: string
  change_type: ChangeType
  // Set alongside change_type "promotion" to update Employee.role in the
  // same request - see app/schemas/salary_record.py.
  new_role?: string | null
}

export interface SalaryRecordRead {
  id: number
  employee_id: number
  amount: number
  currency: string
  amount_usd_snapshot: number
  fx_rate_to_usd: number
  effective_date: string
  change_type: ChangeType
  created_at: string
}

export interface BulkRaiseRequest {
  percentage: number
  effective_date: string
  change_type: ChangeType
  country?: string
  department?: string
  // No status field: always scoped to active employees, not a selectable
  // filter - see app/schemas/bulk.py.
}

export interface BulkRaiseResponse {
  matched_count: number
  applied_count: number
  skipped_no_current_salary: number
  skipped_effective_date_before_hire: number
}

export interface CsvImportRowError {
  row_number: number
  reason: string
}

export interface CsvImportResponse {
  total_rows: number
  created_count: number
  errors: CsvImportRowError[]
  salary_warnings: CsvImportRowError[]
}

// --- Analytics: the 8 fixed dashboard views ---
// Mirrors backend/app/schemas/analytics.py. All 8 are GET /analytics/*,
// reachable by any authenticated role (including executive_viewer - this is
// the only part of the app that role can see).

export interface CountrySalaryStats {
  country: string
  headcount: number
  avg_salary_usd: number
  median_salary_usd: number
}

export interface DepartmentSalaryStats {
  department: string
  headcount: number
  avg_salary_usd: number
  median_salary_usd: number
}

export interface CountryPayroll {
  country: string
  headcount: number
  total_payroll_usd: number
}

export interface SalaryDistributionBand {
  band: string
  headcount: number
}

// gender comes across as a Gender value or the literal "unspecified" (rows
// with no gender recorded) - the backend groups nulls under that label.
export type GenderLabel = Gender | 'unspecified'

export interface GenderHeadcount {
  gender: GenderLabel
  headcount: number
}

// avg_salary_usd is null (and suppressed true) whenever headcount is below
// min_group_size (default 5) - the min-group-size privacy rule, enforced in
// the backend query layer. Render this as a real "insufficient data" state,
// never coerce the null to 0.
export interface GenderSalaryStats {
  gender: GenderLabel
  headcount: number
  avg_salary_usd: number | null
  suppressed: boolean
}

export interface SalaryChangeFeedItem {
  employee_id: number
  employee_name: string
  department: string
  country: string
  change_type: ChangeType
  effective_date: string
  amount: number
  currency: string
  amount_usd: number
}

export interface QuarterlyPayroll {
  quarter: string
  headcount: number
  total_payroll_usd: number
}