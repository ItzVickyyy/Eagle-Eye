import { expect, test } from "@playwright/test"
import { setRole } from "./utils/roleAuth"
import { ensureE2EUsers } from "./utils/userFactory"

const SUPERADMIN = "superadminnoidev@example.com"
const ADMIN = "admin@example.com"

test.describe("Super admin and RBAC", () => {
  let superAdminToken: string
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    superAdminToken = tokens[SUPERADMIN]
    adminToken = tokens[ADMIN]
  })

  test("super admin sees the Administration navigation group", async ({
    page,
  }) => {
    await setRole(page, superAdminToken)
    await page.goto("/admin")
    await expect(page.getByRole("link", { name: "Users" })).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Members", exact: true }),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Site Settings", exact: true }),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "System Dashboard" }),
    ).toHaveCount(0)
  })

  test("a non-super admin cannot open the Users management page", async ({
    page,
  }) => {
    await setRole(page, adminToken)
    await page.goto("/admin/users")
    await page.waitForURL("**/admin")
    await expect(page.getByText("Welcome back")).toBeVisible()
  })

  test("super admin creates a staff user from the Users page", async ({
    page,
  }) => {
    const email = `e2e-rbac-${Date.now()}@example.com`
    const password = "E2e!RbacPass1"
    await setRole(page, superAdminToken)
    await page.goto("/admin/users")
    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible()
    await page.getByRole("button", { name: "Add User" }).click()
    await page.getByPlaceholder("Email").fill(email)
    await page.getByPlaceholder("Full name").fill("RBAC E2E User")
    await page.getByPlaceholder("Password").first().fill(password)
    await page.getByPlaceholder("Password").last().fill(password)
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("User created successfully")).toBeVisible()
    await expect(page.getByRole("cell", { name: email })).toBeVisible()
  })
})
