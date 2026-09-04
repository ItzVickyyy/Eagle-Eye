import { expect, test } from "@playwright/test"
import { setRole } from "./utils/roleAuth"
import { ensureE2EUsers } from "./utils/userFactory"

const DEVELOPER = "developer@example.com"
const ADMIN = "admin@example.com"
const ADMIN_DEV = "admindeveloper@example.com"

test.describe("Developer isolation", () => {
  let developerToken: string
  let adminToken: string
  let adminDevToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    developerToken = tokens[DEVELOPER]
    adminToken = tokens[ADMIN]
    adminDevToken = tokens[ADMIN_DEV]
  })

  test("a contributor-developer sees the System Dashboard link", async ({
    page,
  }) => {
    await setRole(page, developerToken)
    await page.goto("/admin")
    await expect(
      page.getByRole("link", { name: "System Dashboard" }),
    ).toBeVisible()
    await expect(page.getByRole("link", { name: "Review Queue" })).toHaveCount(
      0,
    )
    await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0)
  })

  test("a contributor-developer opens the developer page and sees system metrics", async ({
    page,
  }) => {
    await setRole(page, developerToken)
    await page.goto("/admin/developer")
    await expect(
      page.getByRole("heading", { name: "Developer System Dashboard" }),
    ).toBeVisible()
    await expect(page.getByText("System Status")).toBeVisible()
  })

  test("a non-developer admin is redirected away from the developer page", async ({
    page,
  }) => {
    await setRole(page, adminToken)
    await page.goto("/admin/developer")
    await page.waitForURL("**/admin")
    await expect(page.getByText("Welcome back")).toBeVisible()
  })

  test("an admin-developer sees both admin and developer navigation", async ({
    page,
  }) => {
    await setRole(page, adminDevToken)
    await page.goto("/admin")
    await expect(page.getByRole("link", { name: "Review Queue" })).toBeVisible()
    await expect(
      page.getByRole("link", { name: "System Dashboard" }),
    ).toBeVisible()
  })
})
