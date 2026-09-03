import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function HomePage() {
  const { auth } = useAuth()

  if (!auth) {
    return <Navigate to="/login" replace />
  }

  if (auth.role === 'admin' || auth.role === 'hr_manager') {
    return <Navigate to="/employees" replace />
  }
  return <Navigate to="/analytics" replace />
}