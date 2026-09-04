import { expect, test } from "@playwright/test"
import {
  apiCreateArticle,
  getArticleCommentsPublic,
  getCategories,
  postComment,
} from "./utils/api"
import { setRole } from "./utils/roleAuth"
import { ensureE2EUsers } from "./utils/userFactory"

const ADMIN = "admin@example.com"

test.describe("Comments", () => {
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    adminToken = tokens[ADMIN]
  })

  test("a public comment on a published article is visible on the article page", async () => {
    const categories = await getCategories()
    const article = await apiCreateArticle({
      token: adminToken,
      headline: `Comments Test Article ${Date.now()}`,
      categoryId: categories[0].id,
      status: "published",
    })
    await postComment({
      articleId: article.id,
      guestName: "Commenter Alice",
      guestEmail: "alice@example.com",
      body: "This is a public test comment.",
    })
    const comments = await getArticleCommentsPublic(article.id)
    const match = comments.find(
      (c: any) => c.body === "This is a public test comment.",
    )
    expect(match).toBeTruthy()
    expect(match?.guest_name).toBe("Commenter Alice")
  })

  test("staff admin can view and moderate comments in the admin comments page", async ({
    page,
  }) => {
    const categories = await getCategories()
    const body = `Moderate me ${Date.now()}`
    const article = await apiCreateArticle({
      token: adminToken,
      headline: `Comment Mod Article ${Date.now()}`,
      categoryId: categories[0].id,
      status: "published",
    })
    await postComment({
      articleId: article.id,
      guestName: "Moderator Test",
      guestEmail: "moder@example.com",
      body,
    })
    await setRole(page, adminToken)
    await page.goto("/admin/comments")
    await expect(
      page.getByRole("heading", { name: "Comment Moderation" }),
    ).toBeVisible()
    await expect(page.getByText(body).first()).toBeVisible()
  })
})
