import { expect, test } from "@playwright/test"

test.describe("Article editor route", () => {
  test("/admin/articles renders the article list (index route)", async ({
    page,
  }) => {
    await page.goto("/admin/articles")

    await expect(
      page.getByRole("heading", { name: "Articles", level: 1 }),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: /New Article/ }),
    ).toBeVisible()
    await expect(
      page.getByRole("tab", { name: /Drafts/ }),
    ).toBeVisible()
  })

  test("/admin/articles/new renders the editor (not the list)", async ({
    page,
  }) => {
    await page.goto("/admin/articles/new")

    await expect(
      page.getByRole("heading", { name: "Write Article", level: 1 }),
    ).toBeVisible()

    await expect(page.locator("#headline")).toBeVisible()
    await expect(page.locator("#excerpt")).toBeVisible()
    await expect(page.locator("#tags")).toBeVisible()

    await expect(
      page.getByRole("button", { name: "Save Draft" }),
    ).toBeVisible()
    await expect(
      page.getByRole("button", { name: "Submit for Review" }),
    ).toBeVisible()

    await expect(
      page.getByRole("toolbar", { name: "Editor formatting options" }),
    ).toBeVisible()

    await expect(
      page.getByRole("heading", { name: "Articles", level: 1 }),
    ).not.toBeVisible()
  })

  test("navigating from list to editor preserves the route", async ({
    page,
  }) => {
    await page.goto("/admin/articles")

    await page.getByRole("link", { name: /New Article/ }).click()
    await page.waitForURL("**/admin/articles/new")

    await expect(
      page.getByRole("heading", { name: "Write Article", level: 1 }),
    ).toBeVisible()
  })

  test("navigating from editor back to list works", async ({ page }) => {
    await page.goto("/admin/articles/new")

    await page.locator('a[href="/admin/articles"]').first().click()
    await page.waitForURL("**/admin/articles")

    await expect(
      page.getByRole("heading", { name: "Articles", level: 1 }),
    ).toBeVisible()
  })
})

test.describe("Article editor route — auth", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("unauthenticated user is redirected away from /admin/articles/new", async ({
    page,
  }) => {
    await page.goto("/admin/articles/new")
    await page.waitForURL("**/login")
    await expect(
      page.getByRole("heading", { name: "Staff Login" }),
    ).toBeVisible()
  })
})
