import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AdminUser } from '../types/api'
import { UsersPage } from './UsersPage'

vi.mock('../api/users', () => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUserRole: vi.fn(),
  deleteUser: vi.fn(),
}))
vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ auth: { email: 'admin@acme-corp.example', role: 'admin', token: 't' } }),
}))

import { createUser, deleteUser, listUsers, updateUserRole } from '../api/users'

const listMock = vi.mocked(listUsers)
const createMock = vi.mocked(createUser)
const updateMock = vi.mocked(updateUserRole)
const deleteMock = vi.mocked(deleteUser)

const USERS: AdminUser[] = [
  { id: 1, email: 'admin@acme-corp.example', role: 'admin' },
  { id: 2, email: 'hr@acme-corp.example', role: 'hr_manager' },
]

beforeEach(() => {
  vi.clearAllMocks()
  listMock.mockResolvedValue(USERS)
})

describe('UsersPage', () => {
  it('lists users and marks the current account, which has no role picker or Remove', async () => {
    render(<UsersPage />)

    const selfRow = (await screen.findByText(/admin@acme-corp\.example/)).closest('tr')!
    expect(within(selfRow).getByText('(you)')).toBeInTheDocument()
    expect(within(selfRow).queryByRole('combobox')).not.toBeInTheDocument()
    expect(within(selfRow).queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument()

    const otherRow = screen.getByText('hr@acme-corp.example').closest('tr')!
    expect(within(otherRow).getByRole('combobox')).toBeInTheDocument()
    expect(within(otherRow).getByRole('button', { name: 'Remove' })).toBeInTheDocument()
  })

  it('creates a user from the form and refetches', async () => {
    const user = userEvent.setup()
    createMock.mockResolvedValue({ id: 3, email: 'new@acme-corp.example', role: 'hr_manager' })
    render(<UsersPage />)
    await screen.findByText('hr@acme-corp.example')

    await user.type(screen.getByLabelText('Email'), 'new@acme-corp.example')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Create user' }))

    await waitFor(() =>
      expect(createMock).toHaveBeenCalledWith({
        email: 'new@acme-corp.example',
        password: 'password123',
        role: 'hr_manager',
      }),
    )
    expect(listMock).toHaveBeenCalledTimes(2) // mount + after create
  })

  it('shows the backend message when a role change is rejected', async () => {
    const user = userEvent.setup()
    const { ApiError } = await import('../api/client')
    updateMock.mockRejectedValue(new ApiError(400, "You can't change your own role away from admin"))
    render(<UsersPage />)
    await screen.findByText('hr@acme-corp.example')

    const otherRow = screen.getByText('hr@acme-corp.example').closest('tr')!
    await user.selectOptions(within(otherRow).getByRole('combobox'), 'admin')

    expect(await screen.findByText(/can't change your own role/i)).toBeInTheDocument()
    expect(updateMock).toHaveBeenCalledWith(2, 'admin')
  })

  it('confirms before removing a user', async () => {
    const user = userEvent.setup()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    deleteMock.mockResolvedValue(undefined)
    render(<UsersPage />)
    await screen.findByText('hr@acme-corp.example')

    const otherRow = screen.getByText('hr@acme-corp.example').closest('tr')!
    await user.click(within(otherRow).getByRole('button', { name: 'Remove' }))

    expect(confirmSpy).toHaveBeenCalled()
    await waitFor(() => expect(deleteMock).toHaveBeenCalledWith(2))
    confirmSpy.mockRestore()
  })
})