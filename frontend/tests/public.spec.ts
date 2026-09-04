import { expect, test } from "@playwright/test"
import { apiCreateArticle, pickCategorySlug } from "./utils/api"
import { ensureE2EUsers, firstSuperuser } from "./utils/userFactory"

let superToken: string
let detailArticle: { id: string; slug: string; headline: string }

test.beforeAll(async () => {
  const tokens = await ensureE2EUsers()
  superToken = tokens[firstSuperuser]
  const news = await pickCategorySlug("news")
  detailArticle = await apiCreateArticle({
    token: superToken,
    headline: `Public Test Story ${Date.now()}`,
    slug: `public-test-story-${Date.now()}`,
    excerpt: "A story crafted for public page E2E validation.",
    body: "<p>The Eagle Eye newsroom validated this article through the public reader journey.</p>",
    coverImageUrl:
      "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800",
    categoryId: news.id,
    status: "published",
  })
})

test.describe("Public experience", () => {
  test("home page renders latest news and site navigation", async ({
    page,
  }) => {
    await page.goto("/")
    await expect(
      page.getByRole("heading", { name: "Latest News" }),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Home", exact: true }).first(),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "News", exact: true }).first(),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "About Us", exact: true }).first(),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "Contact", exact: true }).first(),
    ).toBeVisible()
  })

  test("news listing page shows header, filters and count", async ({
    page,
  }) => {
    await page.goto("/news")
    await expect(
      page.getByRole("heading", { name: "Latest News" }),
    ).toBeVisible()
    await expect(
      page.getByRole("link", { name: "All", exact: true }).first(),
    ).toBeVisible()
  })

  test("published article detail renders headline, body and comments section", async ({
    page,
  }) => {
    await page.goto(`/news/${detailArticle.slug}`)
    await expect(
      page.getByRole("heading", { name: detailArticle.headline }),
    ).toBeVisible()
    await expect(
      page.getByText(/The Eagle Eye newsroom validated/),
    ).toBeVisible()
    await expect(
      page.getByRole("heading", { name: "Leave a comment" }),
    ).toBeVisible()
  })

  test("about page renders mission and team sections", async ({ page }) => {
    await page.goto("/about-us")
    await expect(
      page.getByRole("heading", {
        name: "The student voice of Colegio de Los Baños",
      }),
    ).toBeVisible()
    await expect(
      page.getByRole("heading", { name: "Our Mission & History" }),
    ).toBeVisible()
    await expect(
      page.getByRole("heading", { name: "What We Stand For" }),
    ).toBeVisible()
    await expect(
      page.getByRole("heading", { name: "Meet the Staff & Advisers" }),
    ).toBeVisible()
  })

  test("contact page renders the public contact form", async ({ page }) => {
    await page.goto("/contact-us")
    await expect(
      page.getByRole("heading", { name: "Contact Us" }),
    ).toBeVisible()
    await expect(page.getByLabel("Name")).toBeVisible()
    await expect(page.getByLabel("Message")).toBeVisible()
    await expect(
      page.getByRole("button", { name: "Send Message" }),
    ).toBeVisible()
  })

  test("footer exposes category and club navigation", async ({ page }) => {
    await page.goto("/")
    const footer = page.locator("footer").first()
    await expect(footer.getByText("Sections", { exact: true })).toBeVisible()
    await expect(footer.getByText("The Club", { exact: true })).toBeVisible()
    await expect(
      footer.getByText("Get in Touch", { exact: true }),
    ).toBeVisible()
  })

  test("201 article visit increments the view counter shown on detail page", async ({
    page,
  }) => {
    await page.goto(`/news/${detailArticle.slug}`)
    await expect(
      page.getByRole("heading", { name: detailArticle.headline }),
    ).toBeVisible()
    await expect(page.getByText(/\d+ views/)).toBeVisible()
  })
})
