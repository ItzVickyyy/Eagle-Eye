import type { Browser, BrowserContext, Page } from "@playwright/test"

export const FRONTEND_ORIGIN =
  process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173"

/**
 * Impersonates the given `access_token` on the managed `page` fixture by
 * injecting it into localStorage before every navigation. The `chromium`
 * project boots with a superuser storage state, so calling this with a role
 * token overrides it (mirrors src/hooks/useAuth.ts). Safe for parallel tests
 * because each test gets its own `page`.
 */
export async function setRole(page: Page, token: string) {
  await page.addInitScript(
    ({ accessToken }) => {
      window.localStorage.setItem("access_token", accessToken)
    },
    { accessToken: token },
  )
}

/**
 * Creates a fresh browser context that is authenticated as the given
 * `access_token`. The token is injected into localStorage before the app
 * boots, mirroring exactly what the app's login flow stores
 * (see src/hooks/useAuth.ts). Closing the returned `page` also closes the
 * dedicated context so it never leaks auth into other parallel tests.
 */
export async function openAuthedPage(
  browser: Browser,
  token: string,
): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext()
  await context.addInitScript(
    ({ accessToken }) => {
      window.localStorage.setItem("access_token", accessToken)
    },
    { accessToken: token },
  )
  const page = await context.newPage()
  return { context, page }
}

/**
 * Creates a fresh browser context with NO authentication (a logged-out guest).
 * Closing the returned `page` also closes the dedicated context.
 */
export async function openGuestPage(
  browser: Browser,
): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext()
  const page = await context.newPage()
  return { context, page }
}
