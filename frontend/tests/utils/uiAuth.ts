import { expect, type Page } from "@playwright/test"

/**
 * Makes the supplied page context a logged-out guest by clearing the auth
 * token on every navigation. The `chromium` project injects a superuser
 * storage state, so auth-sensitive tests must call this before navigating.
 */
export async function clearAuth(page: Page) {
  await page.addInitScript(() => window.localStorage.removeItem("access_token"))
}

/**
 * Logs in a user through the real login UI and waits for the post-login
 * redirect. Mirrors the current app flow (useAuth navigates to /admin).
 */
export async function loginAs(page: Page, email: string, password: string) {
  await page.goto("/login")
  await page.getByTestId("email-input").fill(email)
  await page.getByTestId("password-input").fill(password)
  await page.getByRole("button", { name: "Log In" }).click()
  await page.waitForURL("**/admin")
  await expect(
    page.getByRole("heading", { name: /Welcome back/ }),
  ).toBeVisible()
}

export async function logoutViaMenu(page: Page) {
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log Out" }).click()
}

export async function expectRedirectedToLogin(page: Page) {
  await page.waitForURL("**/login")
  await expect(page.getByRole("heading", { name: "Staff Login" })).toBeVisible()
}
