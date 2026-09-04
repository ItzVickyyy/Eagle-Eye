import { expect, test } from "@playwright/test"
import { firstSuperuserPassword } from "./config"
import {
  clearAuth,
  expectRedirectedToLogin,
  loginAs,
  logoutViaMenu,
} from "./utils/uiAuth"
import { ensureE2EUsers, firstSuperuser } from "./utils/userFactory"

test.beforeAll(async () => {
  await ensureE2EUsers()
})

test.describe("Auth flow", () => {
  test("logs in with valid superuser credentials and lands on the dashboard", async ({
    page,
  }) => {
    await clearAuth(page)
    await loginAs(page, firstSuperuser, firstSuperuserPassword)
  })

  test("rejects an incorrect password and stays on the login page", async ({
    page,
  }) => {
    await clearAuth(page)
    await page.goto("/login")
    await page.getByTestId("email-input").fill(firstSuperuser)
    await page.getByTestId("password-input").fill("definitely-wrong-pass-123")
    await page.getByRole("button", { name: "Log In" }).click()
    await expect(page).toHaveURL(/\/login/)
    await expect(page.getByText("Incorrect email or password")).toBeVisible()
  })

  test("logged-out guest is redirected away from a protected route", async ({
    page,
  }) => {
    await clearAuth(page)
    await page.goto("/admin")
    await expectRedirectedToLogin(page)
  })

  test("logged-out guest cannot reach a nested admin page", async ({
    page,
  }) => {
    await clearAuth(page)
    await page.goto("/admin/users")
    await expectRedirectedToLogin(page)
  })

  test("logging out returns the user to the public login page", async ({
    page,
  }) => {
    await clearAuth(page)
    await loginAs(page, firstSuperuser, firstSuperuserPassword)
    await logoutViaMenu(page)
    await expectRedirectedToLogin(page)
  })

  test("reset password page without a token bounces to login", async ({
    page,
  }) => {
    await clearAuth(page)
    await page.goto("/reset-password")
    await expectRedirectedToLogin(page) // missing ?token=
  })

  test("password recovery submits and reports a link was sent", async ({
    page,
  }) => {
    await clearAuth(page)
    await page.goto("/recover-password")
    await expect(
      page.getByRole("heading", { name: "Password Recovery" }),
    ).toBeVisible()
    await page.getByTestId("email-input").fill("reader@example.com")
    await page.getByRole("button", { name: "Continue" }).click()
    await expect(
      page.getByText("Password recovery email sent successfully"),
    ).toBeVisible()
  })
})
