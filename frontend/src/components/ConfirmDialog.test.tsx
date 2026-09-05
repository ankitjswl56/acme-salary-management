import type { ComponentProps } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmDialog } from './ConfirmDialog'

function setup(overrides: Partial<ComponentProps<typeof ConfirmDialog>> = {}) {
  const onConfirm = vi.fn()
  const onCancel = vi.fn()
  render(
    <ConfirmDialog
      open
      title="Remove item"
      onConfirm={onConfirm}
      onCancel={onCancel}
      {...overrides}
    >
      Are you sure?
    </ConfirmDialog>,
  )
  return { onConfirm, onCancel }
}

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    render(
      <ConfirmDialog open={false} title="x" onConfirm={vi.fn()} onCancel={vi.fn()}>
        body
      </ConfirmDialog>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows the title and body, and focuses Cancel so Enter cannot accidentally confirm', async () => {
    setup()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Remove item')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
  })

  it('calls onConfirm / onCancel from their buttons', async () => {
    const user = userEvent.setup()
    const { onConfirm } = setup()
    await user.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('Escape cancels', async () => {
    const user = userEvent.setup()
    const { onCancel } = setup()
    await user.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('clicking the backdrop cancels, clicking inside the dialog does not', async () => {
    const user = userEvent.setup()
    const { onCancel } = setup()
    await user.click(screen.getByText('Are you sure?'))
    expect(onCancel).not.toHaveBeenCalled()

    await user.click(screen.getByRole('dialog').parentElement!) // the backdrop
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('disables both buttons and shows the busy label while confirming', () => {
    setup({ confirming: true, confirmingLabel: 'Removing…', confirmLabel: 'Remove' })
    expect(screen.getByRole('button', { name: 'Removing…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
  })

  it('uses custom labels', () => {
    setup({ confirmLabel: 'Delete forever', cancelLabel: 'Keep it' })
    expect(screen.getByRole('button', { name: 'Delete forever' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Keep it' })).toBeInTheDocument()
  })
})