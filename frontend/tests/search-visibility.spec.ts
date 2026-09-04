import { expect, test } from "@playwright/test"
import { apiCreateArticle, getCategories } from "./utils/api"
import { ensureE2EUsers } from "./utils/userFactory"

const ADMIN = "admin@example.com"

test.describe("Search visibility", () => {
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    adminToken = tokens[ADMIN]
  })

  test("a published article is findable via the public search", async ({
    page,
  }) => {
    const headline = `Searchable Published ${Date.now()}`
    const categories = await getCategories()
    await apiCreateArticle({
      token: adminToken,
      headline,
      categoryId: categories[0].id,
      status: "published",
    })
    await page.goto(`/search?q=${encodeURIComponent(headline)}`)
    await expect(page.getByRole("link", { name: headline })).toBeVisible()
  })

  test("a draft article is not visible in public search results", async ({
    page,
  }) => {
    const headline = `Hidden Draft ${Date.now()}`
    const categories = await getCategories()
    await apiCreateArticle({
      token: adminToken,
      headline,
      categoryId: categories[0].id,
      status: "draft",
    })
    await page.goto(`/search?q=${encodeURIComponent(headline)}`)
    const _results = page.locator("article, [data-testid]")
    const match = page.getByText(headline)
    await expect(match).toHaveCount(0)
  })

  test("a pending-review article is not visible in public search results", async ({
    page,
  }) => {
    const headline = `Hidden Pending ${Date.now()}`
    const categories = await getCategories()
    await apiCreateArticle({
      token: adminToken,
      headline,
      categoryId: categories[0].id,
      status: "pending",
    })
    await page.goto(`/search?q=${encodeURIComponent(headline)}`)
    await expect(page.getByText(headline)).toHaveCount(0)
  })

  test("searching for gibberish shows an empty state", async ({ page }) => {
    await page.goto("/search?q=xyzzy12345nonexistent")
    await expect(page.getByText(/No results for/)).toBeVisible()
  })
})
