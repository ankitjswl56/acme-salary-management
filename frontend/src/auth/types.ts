// Mirrors backend/app/models/enums.py's UserRole.
export type UserRole = 'admin' | 'hr_manager' | 'executive_viewer'

export interface AuthState {
  token: string
  email: string
  role: UserRole
}

// Mirrors backend/app/schemas/auth.py's LoginResponse.
export interface LoginResponse {
  access_token: string
  token_type: string
  email: string
  role: UserRole
}