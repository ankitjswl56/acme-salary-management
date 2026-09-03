import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { BulkRaisePage } from './pages/BulkRaisePage'
import { EmployeeCreatePage } from './pages/EmployeeCreatePage'
import { EmployeeDetailPage } from './pages/EmployeeDetailPage'
import { EmployeeEditPage } from './pages/EmployeeEditPage'
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
            <Route path="/employees/new" element={<EmployeeCreatePage />} />
            <Route path="/employees/bulk-raise" element={<BulkRaisePage />} />
            <Route path="/employees/:id" element={<EmployeeDetailPage />} />
            <Route path="/employees/:id/edit" element={<EmployeeEditPage />} />
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