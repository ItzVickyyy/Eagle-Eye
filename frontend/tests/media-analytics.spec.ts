import { expect, test } from "@playwright/test"
import { setRole } from "./utils/roleAuth"
import { apiBaseURL, ensureE2EUsers } from "./utils/userFactory"

const ADMIN = "admin@example.com"
const CONTRIBUTOR = "contributor@example.com"

test.describe("Analytics and media", () => {
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    adminToken = tokens[ADMIN]
  })

  test("staff admin opens the analytics page and sees publication metrics", async ({
    page,
  }) => {
    await setRole(page, adminToken)
    await page.goto("/admin/analytics")
    await expect(page.getByRole("heading", { name: "Analytics" })).toBeVisible()
    await expect(page.getByText("Total Views")).toBeVisible()
  })

  test("a contributor is redirected away from the analytics page", async ({
    page,
  }) => {
    const tokens = await ensureE2EUsers()
    await setRole(page, tokens[CONTRIBUTOR])
    await page.goto("/admin/analytics")
    await page.waitForURL("**/admin")
    await expect(page.getByText("Welcome back")).toBeVisible()
  })

  test("admin can upload a file through the media endpoint", async () => {
    const fileContent = Buffer.from(
      "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
      "base64",
    )
    const blob = new Blob([fileContent], { type: "image/gif" })
    const formData = new FormData()
    formData.append("file", blob, "pixel.gif")

    const res = await fetch(`${apiBaseURL()}/api/v1/media/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${adminToken}` },
      body: formData,
    })
    expect(res.ok).toBeTruthy()
    const data = await res.json()
    const url = data?.data?.file_url || data?.file_url
    expect(url).toBeTruthy()
  })
})
