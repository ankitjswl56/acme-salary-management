import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../api/client'
import type { NLQueryResponse } from '../../types/api'
import { NLQueryBox } from './NLQueryBox'

vi.mock('../../api/analytics', () => ({ askAnalytics: vi.fn() }))
import { askAnalytics } from '../../api/analytics'
const askMock = vi.mocked(askAnalytics)

const okResponse: NLQueryResponse = {
  status: 'ok',
  question: 'average salary by country',
  function: 'salary_by_country',
  parameters: {},
  data: [
    { country: 'US', headcount: 3198, avg_salary_usd: 91405, median_salary_usd: 82360 },
    { country: 'DE', headcount: 730, avg_salary_usd: 85575, median_salary_usd: 77667 },
  ],
  message: null,
  notes: [],
}

beforeEach(() => {
  askMock.mockReset()
})

describe('NLQueryBox', () => {
  it('disables Ask until a question is typed', async () => {
    const user = userEvent.setup()
    render(<NLQueryBox />)

    const button = screen.getByRole('button', { name: 'Ask' })
    expect(button).toBeDisabled()

    await user.type(screen.getByLabelText('Analytics question'), 'hello')
    expect(button).toBeEnabled()
  })

  it('submits the question and renders the result table with formatted figures', async () => {
    const user = userEvent.setup()
    askMock.mockResolvedValue(okResponse)
    render(<NLQueryBox />)

    await user.type(screen.getByLabelText('Analytics question'), 'average salary by country')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(askMock).toHaveBeenCalledWith('average salary by country')
    expect(await screen.findByText('salary_by_country')).toBeInTheDocument() // function chip
    expect(screen.getByText('Avg Salary Usd')).toBeInTheDocument() // column header
    expect(screen.getByText('$91,405')).toBeInTheDocument() // formatted cell
    expect(screen.getByRole('table')).toBeInTheDocument()
  })

  it('shows coercion notes when the backend adjusted a parameter', async () => {
    const user = userEvent.setup()
    askMock.mockResolvedValue({
      ...okResponse,
      function: 'payroll_trend',
      parameters: { quarters: 40 },
      notes: ["capped 'quarters' at the maximum of 40"],
    })
    render(<NLQueryBox />)

    await user.type(screen.getByLabelText('Analytics question'), 'payroll trend forever')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(/capped 'quarters' at the maximum of 40/)).toBeInTheDocument()
    expect(screen.getByText('quarters: 40')).toBeInTheDocument()
  })

  it('renders the fixed refusal for an out-of-scope question, with no table', async () => {
    const user = userEvent.setup()
    askMock.mockResolvedValue({
      status: 'out_of_scope',
      question: 'weather?',
      function: null,
      parameters: null,
      data: null,
      message: 'I can only answer questions about salary data — try asking about pay by country.',
      notes: [],
    })
    render(<NLQueryBox />)

    await user.type(screen.getByLabelText('Analytics question'), 'weather?')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(/I can only answer questions about salary data/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('maps a 503 to a friendly unavailable message rather than the raw detail', async () => {
    const user = userEvent.setup()
    askMock.mockRejectedValue(new ApiError(503, 'OPENROUTER_API_KEY is not set'))
    render(<NLQueryBox />)

    await user.type(screen.getByLabelText('Analytics question'), 'average salary by country')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText(/language model is unavailable right now/i)).toBeInTheDocument()
    expect(screen.queryByText(/OPENROUTER_API_KEY/)).not.toBeInTheDocument()
  })

  it('surfaces a non-503 ApiError message (e.g. a 422)', async () => {
    const user = userEvent.setup()
    askMock.mockRejectedValue(new ApiError(422, 'question must not be blank'))
    render(<NLQueryBox />)

    await user.type(screen.getByLabelText('Analytics question'), 'x')
    await user.click(screen.getByRole('button', { name: 'Ask' }))

    expect(await screen.findByText('question must not be blank')).toBeInTheDocument()
  })

  it('runs an example chip as a query', async () => {
    const user = userEvent.setup()
    askMock.mockResolvedValue(okResponse)
    render(<NLQueryBox />)

    await user.click(screen.getByRole('button', { name: 'Average salary by country' }))

    expect(askMock).toHaveBeenCalledWith('Average salary by country')
    expect(await screen.findByText('salary_by_country')).toBeInTheDocument()
  })
})