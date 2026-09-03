import { useEffect, useState } from 'react'
import { ApiError } from '../../api/client'

interface QueryState<T> {
  data: T | null
  loading: boolean
  error: string
}

/**
 * Runs `fetcher` on mount and whenever `queryKey` changes, with the usual
 * loading/error/data bookkeeping and stale-response guarding. Every analytics
 * view needs exactly this shape, so it lives in one place.
 *
 * `queryKey` is the single source of truth for "the inputs changed" - build
 * it from whatever the fetcher closes over (filter values, or a fixed string
 * for a parameterless view). The effect deliberately keys off `queryKey`
 * alone, not the `fetcher` identity, so an inline arrow is fine.
 */
export function useAnalyticsQuery<T>(fetcher: () => Promise<T>, queryKey: string): QueryState<T> {
  const [state, setState] = useState<QueryState<T>>({ data: null, loading: true, error: '' })

  useEffect(() => {
    let cancelled = false
    setState((prev) => ({ ...prev, loading: true, error: '' }))

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: '' })
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const message = err instanceof ApiError ? err.message : 'Failed to load this view.'
        setState({ data: null, loading: false, error: message })
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- queryKey captures every real input; fetcher identity is intentionally ignored
  }, [queryKey])

  return state
}