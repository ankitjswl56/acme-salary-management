import { useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { askAnalytics } from '../../api/analytics'
import { ApiError } from '../../api/client'
import type { NLQueryResponse } from '../../types/api'
import { formatCell, inferColumns, titleCase } from './nlQueryFormat'

const EXAMPLES = [
  'Average salary by country',
  'Headcount and payroll per country',
  'Gender balance in Engineering',
  'Promotions in the last 12 months',
]

/** Renders the chosen view's output. Almost every analytics view returns an
 *  array of flat objects, so infer columns from the rows; anything else falls
 *  back to formatted JSON. */
function ResultData({ data }: { data: unknown }) {
  const columns = inferColumns(data)
  if (columns) {
    const rows = data as Array<Record<string, unknown>>
    return (
      <Box sx={{ overflowX: 'auto' }}>
        <Table size="small" aria-label="query result">
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell key={col} sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                  {titleCase(col)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={i}>
                {columns.map((col) => (
                  <TableCell key={col} sx={{ whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>
                    {formatCell(col, row[col])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    )
  }

  if (Array.isArray(data) && data.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No rows matched.
      </Typography>
    )
  }

  return (
    <Box
      component="pre"
      sx={{ m: 0, p: 1.5, bgcolor: 'action.hover', borderRadius: 1, overflowX: 'auto', fontSize: 13 }}
    >
      {JSON.stringify(data, null, 2)}
    </Box>
  )
}

// Phase 8 — the stretch natural-language query. Deliberately minimal: one
// input, one button, and a rendering of whatever analytics view the model
// mapped the question to. It's a demonstration of the LLM-to-fixed-function
// integration, not a chat surface — there's no history and no follow-ups.
export function NLQueryBox() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<NLQueryResponse | null>(null)

  async function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed || loading) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await askAnalytics(trimmed))
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.status === 503
            ? 'The language model is unavailable right now. Try again shortly.'
            : err.message
          : 'Something went wrong. Try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="subtitle2" component="h2" sx={{ fontWeight: 700 }}>
          Ask a question
        </Typography>
        <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1.5 }}>
          Plain English, mapped to one of the dashboard views on this page. Read-only — it can’t
          change any data.
        </Typography>

        <Box
          component="form"
          onSubmit={(e) => {
            e.preventDefault()
            void submit(question)
          }}
          sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}
        >
          <TextField
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. average salary by department"
            size="small"
            fullWidth
            sx={{ flex: 1, minWidth: 240 }}
            slotProps={{ htmlInput: { maxLength: 500, 'aria-label': 'Analytics question' } }}
          />
          <Button
            type="submit"
            variant="contained"
            disableElevation
            disabled={loading || !question.trim()}
            sx={{ flexShrink: 0 }}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : 'Ask'}
          </Button>
        </Box>

        <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: 'wrap', gap: 1 }}>
          {EXAMPLES.map((ex) => (
            <Chip
              key={ex}
              label={ex}
              size="small"
              variant="outlined"
              onClick={() => {
                setQuestion(ex)
                void submit(ex)
              }}
              disabled={loading}
            />
          ))}
        </Stack>

        {error && (
          <Alert severity="error" variant="outlined" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {result?.status === 'out_of_scope' && (
          <Alert severity="info" variant="outlined" sx={{ mt: 2 }}>
            {result.message}
          </Alert>
        )}

        {result?.status === 'ok' && (
          <Box sx={{ mt: 2 }}>
            <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap', gap: 0.5 }}>
              <Chip size="small" label={result.function} color="primary" variant="outlined" />
              {result.parameters &&
                Object.entries(result.parameters).map(([k, v]) => (
                  <Chip key={k} size="small" label={`${k}: ${String(v)}`} variant="outlined" />
                ))}
            </Stack>
            {result.notes.length > 0 && (
              <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 1 }}>
                {result.notes.join(' · ')}
              </Typography>
            )}
            <ResultData data={result.data} />
          </Box>
        )}
      </CardContent>
    </Card>
  )
}