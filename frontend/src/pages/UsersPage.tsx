import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createUser, deleteUser, listUsers, updateUserRole } from '../api/users'
import { useAuth } from '../auth/AuthContext'
import { ConfirmDialog } from '../components/ConfirmDialog'
import type { AdminUser, UserRole } from '../types/api'

const ROLES: { value: UserRole; label: string }[] = [
  { value: 'admin', label: 'Admin' },
  { value: 'hr_manager', label: 'HR Manager' },
  { value: 'executive_viewer', label: 'Executive Viewer' },
]

const roleLabel = (role: UserRole) => ROLES.find((r) => r.value === role)?.label ?? role

// Admin-only. RBAC is enforced by the backend and by the route guard in
// App.tsx; this page just talks to /users. It sits next to Employees in the
// nav, so it keeps the hand-rolled CSS the other list/CRUD pages use rather
// than pulling in MUI for one screen.
export function UsersPage() {
  const { auth } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState('')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('hr_manager')
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [rowError, setRowError] = useState('')
  const [pendingDelete, setPendingDelete] = useState<AdminUser | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function refresh() {
    setLoading(true)
    setListError('')
    try {
      setUsers(await listUsers())
    } catch (err) {
      setListError(err instanceof ApiError ? err.message : 'Failed to load users.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setFormError('')
    try {
      await createUser({ email: email.trim(), password, role })
      setEmail('')
      setPassword('')
      setRole('hr_manager')
      await refresh()
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : 'Failed to create the user.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRoleChange(user: AdminUser, nextRole: UserRole) {
    setRowError('')
    try {
      await updateUserRole(user.id, nextRole)
      await refresh()
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : 'Failed to change the role.')
      await refresh()
    }
  }

  function requestDelete(user: AdminUser) {
    setRowError('')
    setPendingDelete(user)
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await deleteUser(pendingDelete.id)
      setPendingDelete(null)
      await refresh()
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : 'Failed to remove the user.')
      setPendingDelete(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Users</h1>
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        Create sign-in accounts and set their role. Admins can manage users; HR managers and
        executive viewers cannot reach this page.
      </p>

      <form className="card stacked-form" style={{ maxWidth: 460 }} onSubmit={handleCreate}>
        <h2 style={{ marginTop: 0 }}>Add a user</h2>
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="person@acme-corp.example"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </label>
        <label>
          Role
          <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        {formError && <p className="login-error">{formError}</p>}
        <div>
          <button type="submit" disabled={submitting}>
            {submitting ? 'Creating…' : 'Create user'}
          </button>
        </div>
      </form>

      {rowError && <p className="login-error">{rowError}</p>}

      {loading ? (
        <p className="muted">Loading…</p>
      ) : listError ? (
        <p className="login-error">{listError}</p>
      ) : (
        <table style={{ marginTop: '1.5rem' }}>
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {users.map((user) => {
              const isSelf = user.email === auth?.email
              return (
                <tr key={user.id}>
                  <td>
                    {user.email}
                    {isSelf && <span className="muted"> (you)</span>}
                  </td>
                  <td>
                    {isSelf ? (
                      roleLabel(user.role)
                    ) : (
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user, e.target.value as UserRole)}
                        aria-label={`Role for ${user.email}`}
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {!isSelf && (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => requestDelete(user)}
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Remove user"
        confirmLabel="Remove"
        confirmingLabel="Removing…"
        confirming={deleting}
        danger
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      >
        Remove {pendingDelete?.email}? They will lose all access immediately, and this can't be
        undone.
      </ConfirmDialog>
    </div>
  )
}