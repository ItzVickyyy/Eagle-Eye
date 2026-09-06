import { expect, test } from "@playwright/test"
import { apiCreateArticle } from "./utils/api"
import { setRole } from "./utils/roleAuth"
import { ensureE2EUsers } from "./utils/userFactory"

const ADMIN = "admin@example.com"
const CONTRIBUTOR = "contributor@example.com"

test.describe("Admin management", () => {
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    adminToken = tokens[ADMIN]
  })

  test("admin sees editorial, moderation, and management navigation", async ({
    page,
  }) => {
    await setRole(page, adminToken)
    await page.goto("/admin")
    await expect(page.getByRole("link", { name: "Review Queue" })).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Categories & Tags" }),
    ).toBeVisible()
    await expect(page.getByRole("link", { name: "Analytics" })).toBeVisible()
    await expect(page.getByRole("link", { name: "Comments" })).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Contact Inbox" }),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "System Dashboard" }),
    ).toHaveCount(0)
    await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0)
  })

  test("admin creates a news category", async ({ page }) => {
    const name = `Cat ${Date.now()}`
    await setRole(page, adminToken)
    await page.goto("/admin/categories")
    await page.getByRole("button", { name: "Add Category" }).first().click()
    await page.getByPlaceholder("e.g. Sports").fill(name)
    await page.getByRole("button", { name: "Create Category" }).click()
    await expect(page.getByText("Category created successfully")).toBeVisible()
    await expect(page.getByRole("cell", { name, exact: true })).toBeVisible()
  })

  test("admin approves and publishes a pending article from the review queue", async ({
    page,
  }) => {
    const headline = `Awaiting Review ${Date.now()}`
    await apiCreateArticle({ token: adminToken, headline, status: "pending" })
    await setRole(page, adminToken)
    await page.goto("/admin/review-queue")
    const card = page
      .locator("div.grid-cols-1 > div")
      .filter({ hasText: headline })
    await expect(card).toBeVisible()
    await card.getByRole("button", { name: "Approve & Publish" }).click()
    await expect(
      page.getByText("Article approved and published!"),
    ).toBeVisible()
  })

  test("contributor is kept out of staff-only admin pages", async ({
    page,
  }) => {
    const tokens = await ensureE2EUsers()
    await setRole(page, tokens[CONTRIBUTOR])
    await page.goto("/admin/review-queue")
    await page.waitForURL("**/")
    await expect(
      page.getByRole("heading", { name: "Welcome back" }),
    ).toHaveCount(0)
  })
})
