import { useEffect, useRef, type ReactNode } from 'react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  /** Body content - plain text or a couple of short paragraphs. */
  children: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  /** Busy label + disabled buttons while the confirmed action is in flight. */
  confirmingLabel?: string
  confirming?: boolean
  /** Red confirm button, for actions that remove/undo something. */
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** A real, styled confirmation dialog - replaces `window.confirm()`, whose
 *  browser-chrome popup looks out of place next to the rest of the app and
 *  can't show more than one line of plain text. Esc and a backdrop click
 *  both cancel; the Cancel button gets focus on open so an accidental Enter
 *  doesn't confirm a destructive action. */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  confirmingLabel = 'Working…',
  confirming = false,
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel()
      }}
    >
      <div className="modal card" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title">
        <h2 id="confirm-dialog-title">{title}</h2>
        <div className="modal-body">{children}</div>
        <div className="modal-actions">
          <button type="button" className="secondary" ref={cancelRef} onClick={onCancel} disabled={confirming}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={danger ? 'danger' : undefined}
            onClick={onConfirm}
            disabled={confirming}
          >
            {confirming ? confirmingLabel : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}