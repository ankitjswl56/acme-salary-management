import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import type { UserRole } from '../auth/types'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { auth } = useAuth()
  const location = useLocation()

  if (!auth) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (allowedRoles && !allowedRoles.includes(auth.role)) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}