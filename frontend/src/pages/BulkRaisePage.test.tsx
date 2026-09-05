import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { BulkRaisePage } from './BulkRaisePage'

vi.mock('../api/employees', () => ({
  getFilterOptions: vi.fn(),
  applyBulkRaise: vi.fn(),
}))

import { applyBulkRaise, getFilterOptions } from '../api/employees'

const getFilterOptionsMock = vi.mocked(getFilterOptions)
const applyBulkRaiseMock = vi.mocked(applyBulkRaise)

function renderPage() {
  return render(<BulkRaisePage />, { wrapper: MemoryRouter })
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/percentage increase/i), '5')
  const dateInput = screen.getByLabelText(/effective date/i)
  await user.clear(dateInput)
  await user.type(dateInput, '2026-01-01')
}

beforeEach(() => {
  getFilterOptionsMock.mockResolvedValue({ countries: [], departments: [] })
})

describe('BulkRaisePage', () => {
  it('shows a confirm dialog naming the scope instead of applying immediately', async () => {
    const user = userEvent.setup()
    renderPage()
    await fillRequiredFields(user)

    await user.click(screen.getByRole('button', { name: 'Apply raise' }))

    expect(applyBulkRaiseMock).not.toHaveBeenCalled()
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('5% raise')
    expect(dialog).toHaveTextContent('all active employees')
  })

  it('cancelling the dialog does not call the API', async () => {
    const user = userEvent.setup()
    renderPage()
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: 'Apply raise' }))
    await screen.findByRole('dialog')

    await user.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(applyBulkRaiseMock).not.toHaveBeenCalled()
  })

  it('confirming applies the raise and renders the result', async () => {
    const user = userEvent.setup()
    applyBulkRaiseMock.mockResolvedValue({
      matched_count: 100,
      applied_count: 98,
      skipped_no_current_salary: 1,
      skipped_effective_date_before_hire: 1,
    })
    renderPage()
    await fillRequiredFields(user)
    await user.click(screen.getByRole('button', { name: 'Apply raise' }))
    const dialog = await screen.findByRole('dialog')

    // Both the form's submit button and the dialog's confirm button are
    // labelled "Apply raise" - scope to the dialog to click the right one.
    await user.click(within(dialog).getByRole('button', { name: 'Apply raise' }))

    await waitFor(() =>
      expect(applyBulkRaiseMock).toHaveBeenCalledWith({
        percentage: 5,
        effective_date: '2026-01-01',
        change_type: 'raise',
        country: undefined,
        department: undefined,
      }),
    )
    expect(await screen.findByText(/98 of 100 matching employees updated/)).toBeInTheDocument()
    expect(screen.getByText(/1 skipped — no current salary/)).toBeInTheDocument()
  })
})