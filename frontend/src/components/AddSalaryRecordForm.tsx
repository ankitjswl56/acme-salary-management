import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getSupportedCurrencies } from '../api/reference'
import type { ChangeType, SalaryRecordCreate } from '../types/api'

const CHANGE_TYPE_LABELS: Record<ChangeType, string> = {
  hire: 'Hire',
  raise: 'Raise',
  promotion: 'Promotion',
  correction: 'Correction',
  cola: 'Cost-of-living adjustment',
}

interface AddSalaryRecordFormProps {
  // "Hire" only makes sense as an employee's very first salary record -
  // offering it once history already exists would let someone record a
  // second "hire" for an already-employed person, which the backend now
  // rejects anyway (see create_salary_record), but hiding it here means
  // the form doesn't offer a choice that's always going to fail.
  hasExistingHistory: boolean
  onSubmit: (values: SalaryRecordCreate) => Promise<void>
  onCancel: () => void
}

export function AddSalaryRecordForm({ hasExistingHistory, onSubmit, onCancel }: AddSalaryRecordFormProps) {
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [changeType, setChangeType] = useState<ChangeType>(hasExistingHistory ? 'raise' : 'hire')
  const [newRole, setNewRole] = useState('')

  const availableChangeTypes = hasExistingHistory
    ? (Object.keys(CHANGE_TYPE_LABELS) as ChangeType[]).filter((type) => type !== 'hire')
    : (Object.keys(CHANGE_TYPE_LABELS) as ChangeType[])

  const [currencies, setCurrencies] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getSupportedCurrencies()
      .then(setCurrencies)
      .catch(() => {
        // Non-critical: dropdown just stays empty if this fails.
      })
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await onSubmit({
        amount: Number(amount),
        currency,
        effective_date: effectiveDate,
        change_type: changeType,
        new_role: changeType === 'promotion' && newRole ? newRole : undefined,
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      setSubmitting(false)
    }
  }

  return (
    <form className="card stacked-form salary-record-form" onSubmit={handleSubmit}>
      <label>
        Change type
        <select value={changeType} onChange={(event) => setChangeType(event.target.value as ChangeType)}>
          {availableChangeTypes.map((type) => (
            <option key={type} value={type}>
              {CHANGE_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </label>

      {changeType === 'promotion' && (
        <label>
          New role / title <span className="muted">(optional)</span>
          <input
            value={newRole}
            onChange={(event) => setNewRole(event.target.value)}
            placeholder="Leave blank to keep the current title"
          />
        </label>
      )}

      <label>
        Amount
        <input
          type="number"
          min="0"
          step="0.01"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          required
        />
      </label>

      <label>
        Currency
        <select value={currency} onChange={(event) => setCurrency(event.target.value)} required>
          <option value="" disabled>
            Select a currency
          </option>
          {currencies.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </label>

      <label>
        Effective date
        <input
          type="date"
          value={effectiveDate}
          onChange={(event) => setEffectiveDate(event.target.value)}
          required
        />
      </label>

      {error && <p className="login-error">{error}</p>}

      <div className="form-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Add record'}
        </button>
        <button type="button" className="secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}