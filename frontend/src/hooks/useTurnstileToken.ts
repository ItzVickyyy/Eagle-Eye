import { useCallback, useEffect, useState } from "react"

interface UseTurnstileOptions {
  resetSignal?: number
  onExpire?: () => void
}

/**
 * Manage the current Turnstile token for a form.
 *
 * Tracks the verified token in local component state and exposes
 * ``reset`` so the surrounding form can clear the token (e.g. after a
 * server error, when the user edits their input, or when the token
 * expires). When ``resetSignal`` changes, the token is invalidated
 * automatically; this is the recommended pattern for forms that need
 * to re-prompt after a failed submission.
 */
export function useTurnstileToken(options: UseTurnstileOptions = {}) {
  const { resetSignal, onExpire } = options
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    if (resetSignal === undefined) return
    setToken(null)
  }, [resetSignal])

  const onVerify = useCallback((next: string) => {
    setToken(next)
  }, [])

  const handleExpire = useCallback(() => {
    setToken(null)
    onExpire?.()
  }, [onExpire])

  const reset = useCallback(() => {
    setToken(null)
  }, [])

  return { token, onVerify, onExpire: handleExpire, reset }
}
