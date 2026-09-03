import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { EmployeesPage } from './pages/EmployeesPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'

function AppRoutes() {
  const { auth } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={auth ? <Navigate to="/" replace /> : <LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route element={<ProtectedRoute allowedRoles={['admin', 'hr_manager']} />}>
            <Route path="/employees" element={<EmployeesPage />} />
          </Route>
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App