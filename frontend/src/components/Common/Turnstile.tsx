import { useEffect, useRef, useState } from "react"

import { cn } from "@/lib/utils"

const TURNSTILE_SCRIPT_SRC =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad&render=explicit"

declare global {
  interface Window {
    turnstile?: {
      render: (
        element: HTMLElement,
        options: {
          sitekey: string
          callback: (token: string) => void
          "expired-callback"?: () => void
          "error-callback"?: () => void
          theme?: "light" | "dark" | "auto"
          "response-field"?: boolean
        },
      ) => string
      reset: (widgetId?: string) => void
      remove: (widgetId?: string) => void
    }
    onTurnstileLoad?: () => void
  }
}

let scriptLoadingPromise: Promise<void> | null = null

function loadTurnstileScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Turnstile requires a browser environment"))
  }
  if (window.turnstile) {
    return Promise.resolve()
  }
  if (scriptLoadingPromise) {
    return scriptLoadingPromise
  }
  scriptLoadingPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(
      `script[src^="https://challenges.cloudflare.com/turnstile"]`,
    )
    const onReady = () => {
      if (window.turnstile) {
        resolve()
      } else {
        reject(new Error("Turnstile script loaded but global was not set"))
      }
    }
    window.onTurnstileLoad = onReady
    if (existing) {
      if (window.turnstile) {
        resolve()
      }
      return
    }
    const script = document.createElement("script")
    script.src = TURNSTILE_SCRIPT_SRC
    script.async = true
    script.defer = true
    script.onerror = () => {
      scriptLoadingPromise = null
      reject(new Error("Failed to load Cloudflare Turnstile script"))
    }
    document.head.appendChild(script)
  })
  return scriptLoadingPromise
}

export interface TurnstileProps {
  siteKey: string
  onVerify: (token: string) => void
  onExpire?: () => void
  onError?: () => void
  className?: string
  theme?: "light" | "dark" | "auto"
}

/**
 * Cloudflare Turnstile widget wrapper.
 *
 * Loads the Turnstile script lazily on mount, renders the widget into a
 * container div, and surfaces the resulting token through ``onVerify``.
 * ``onExpire`` is called when a previously valid token has timed out
 * (Turnstile rotates the token automatically); callers should clear their
 * stored token and re-render the widget before allowing another submit.
 */
export function Turnstile({
  siteKey,
  onVerify,
  onExpire,
  onError,
  className,
  theme = "auto",
}: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const widgetIdRef = useRef<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!siteKey) {
      setError("Turnstile is not configured for this environment")
      onError?.()
      return
    }
    let cancelled = false

    loadTurnstileScript()
      .then(() => {
        if (cancelled) return
        if (!containerRef.current || !window.turnstile) return
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          callback: (token) => {
            setError(null)
            onVerify(token)
          },
          "expired-callback": () => {
            onExpire?.()
          },
          "error-callback": () => {
            setError("CAPTCHA could not be loaded. Please refresh the page.")
            onError?.()
          },
          theme,
        })
      })
      .catch((loadError) => {
        if (cancelled) return
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Failed to load CAPTCHA",
        )
        onError?.()
      })

    return () => {
      cancelled = true
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current)
        } catch {
        }
        widgetIdRef.current = null
      }
    }
  }, [siteKey, onVerify, onExpire, onError, theme])

  if (!siteKey) {
    return null
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div ref={containerRef} data-testid="turnstile-widget" />
      {error ? (
        <p className="text-destructive text-xs" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}
