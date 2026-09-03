import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const navLinkClassName = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : undefined)

export function Layout() {
  const { auth, logout } = useAuth()

  // ProtectedRoute guarantees auth is set before Layout ever renders; this
  // guard just satisfies TypeScript's narrowing (and stays safe if that
  // routing guarantee ever changes).
  if (!auth) {
    return null
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">ACME Salary Management</span>
        <nav className="app-nav">
          {(auth.role === 'admin' || auth.role === 'hr_manager') && (
            <NavLink to="/employees" className={navLinkClassName}>
              Employees
            </NavLink>
          )}
          <NavLink to="/analytics" className={navLinkClassName}>
            Analytics
          </NavLink>
        </nav>
        <div className="app-user">
          <span>
            {auth.email} <span className="muted">({auth.role})</span>
          </span>
          <button type="button" className="secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}