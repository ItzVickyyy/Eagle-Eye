import { expect, test } from "@playwright/test"
import { type ArticleRecord, apiCreateArticle } from "./utils/api"
import { setRole } from "./utils/roleAuth"
import { ensureE2EUsers } from "./utils/userFactory"

const CONTRIBUTOR = "contributor@example.com"

test.describe("Contributor workflow", () => {
  let contributorToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    contributorToken = tokens[CONTRIBUTOR]
  })

  test("contributor is redirected out of the admin shell", async ({
    page,
  }) => {
    await setRole(page, contributorToken)
    await page.goto("/admin")
    await page.waitForURL("**/")
    await expect(
      page.getByRole("heading", { name: "Users" }),
    ).toHaveCount(0)
    await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0)
    await expect(
      page.getByRole("link", { name: "Review Queue" }),
    ).toHaveCount(0)
    await expect(
      page.getByRole("link", { name: "System Dashboard" }),
    ).toHaveCount(0)
  })

  test("a contributor can author an article but is forced into review, not published", async () => {
    const headline = `Contributor Submits ${Date.now()}`
    const created: ArticleRecord = await apiCreateArticle({
      token: contributorToken,
      headline,
      status: "published",
    })
    expect(created.status).toBe("pending")
  })

  test("contributor-created draft appears in the staff admin article list", async ({
    page,
  }) => {
    const headline = `Contributor Draft ${Date.now()}`
    await apiCreateArticle({
      token: contributorToken,
      headline,
      status: "draft",
    })
    const tokens = await ensureE2EUsers()
    await setRole(page, tokens["admin@example.com"])
    await page.goto("/admin/articles")
    await page.getByPlaceholder("Search articles...").fill(headline)
    await expect(
      page.getByRole("cell", { name: headline }).first(),
    ).toBeVisible()
  })
})
