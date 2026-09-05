import { expect, test } from "@playwright/test"
import { setRole } from "./utils/roleAuth"
import { apiBaseURL, ensureE2EUsers } from "./utils/userFactory"

const ADMIN = "admin@example.com"

test.describe("Article editor — video insertion", () => {
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    adminToken = tokens[ADMIN]
  })

  test("Insert Video button opens the dialog with Upload and URL sections", async ({
    page,
  }) => {
    await setRole(page, adminToken)
    await page.goto("/admin/articles/new")

    const toolbar = page.getByRole("toolbar", {
      name: "Editor formatting options",
    })
    await expect(toolbar).toBeVisible()

    const videoButton = toolbar.getByRole("button", { name: "Insert video" })
    await expect(videoButton).toBeVisible()
    await videoButton.click()

    const dialog = page.getByRole("dialog", { name: "Insert Video" })
    await expect(dialog).toBeVisible()
    await expect(
      dialog.getByText("Upload a video from your device", { exact: false }),
    ).toBeVisible()
    await expect(dialog.getByText("MP4 or WEBM up to 100MB")).toBeVisible()
    await expect(dialog.getByLabel("Video Web URL")).toBeVisible()
    await expect(
      dialog.getByRole("button", { name: "Insert URL" }),
    ).toBeVisible()
    await expect(dialog.getByRole("button", { name: "Cancel" })).toBeVisible()
  })

  test("Inserting a video by URL renders a <video> element in the editor", async ({
    page,
  }) => {
    await setRole(page, adminToken)
    await page.goto("/admin/articles/new")

    const toolbar = page.getByRole("toolbar", {
      name: "Editor formatting options",
    })
    await toolbar.getByRole("button", { name: "Insert video" }).click()

    const dialog = page.getByRole("dialog", { name: "Insert Video" })
    const urlInput = dialog.getByLabel("Video Web URL")
    const testUrl = "https://example.com/clip.mp4"
    await urlInput.fill(testUrl)
    await dialog.getByRole("button", { name: "Insert URL" }).click()

    const editor = page.locator(".tiptap")
    await expect(editor.locator("video")).toHaveCount(1)
    await expect(editor.locator("video")).toHaveAttribute("src", testUrl)
    await expect(editor.locator("video")).toHaveAttribute("controls", "true")
  })

  test("Inserting a video rejects an unsafe URL scheme", async ({ page }) => {
    await setRole(page, adminToken)
    await page.goto("/admin/articles/new")

    const toolbar = page.getByRole("toolbar", {
      name: "Editor formatting options",
    })
    await toolbar.getByRole("button", { name: "Insert video" }).click()

    const dialog = page.getByRole("dialog", { name: "Insert Video" })
    const urlInput = dialog.getByLabel("Video Web URL")
    await urlInput.fill("javascript:alert(1)")

    await dialog.getByRole("button", { name: "Insert URL" }).click()

    const editor = page.locator(".tiptap")
    await expect(editor.locator("video")).toHaveCount(0)
  })

  test("backend rejects an oversized video upload with HTTP 413", async () => {
    const big = new Uint8Array(101 * 1024 * 1024)
    const blob = new Blob([big], { type: "video/mp4" })
    const formData = new FormData()
    formData.append("file", blob, "oversized.mp4")

    const res = await fetch(`${apiBaseURL()}/api/v1/media/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${adminToken}` },
      body: formData,
    })
    expect(res.status).toBe(413)
    const body = await res.json().catch(() => ({}))
    const detail = JSON.stringify(body).toLowerCase()
    expect(detail).toContain("video")
    expect(detail).toContain("100mb")
  })

  test("backend accepts a small video upload", async () => {
    const tiny = new Uint8Array(1024)
    const blob = new Blob([tiny], { type: "video/mp4" })
    const formData = new FormData()
    formData.append("file", blob, "tiny.mp4")

    const res = await fetch(`${apiBaseURL()}/api/v1/media/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${adminToken}` },
      body: formData,
    })
    expect(res.ok).toBeTruthy()
    const body = await res.json()
    const url = body?.data?.file_url || body?.file_url
    expect(url).toBeTruthy()
  })

  test("backend still accepts an image at 14MB under the 15MB image limit", async () => {
    const fourteenMb = 14 * 1024 * 1024
    const img = new Uint8Array(fourteenMb)
    const blob = new Blob([img], { type: "image/png" })
    const formData = new FormData()
    formData.append("file", blob, "big.png")

    const res = await fetch(`${apiBaseURL()}/api/v1/media/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${adminToken}` },
      body: formData,
    })
    expect(res.ok).toBeTruthy()
  })

  test("backend rejects an oversized image at 16MB with HTTP 413", async () => {
    const tooBig = 16 * 1024 * 1024
    const img = new Uint8Array(tooBig)
    const blob = new Blob([img], { type: "image/png" })
    const formData = new FormData()
    formData.append("file", blob, "toobig.png")

    const res = await fetch(`${apiBaseURL()}/api/v1/media/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${adminToken}` },
      body: formData,
    })
    expect(res.status).toBe(413)
    const body = await res.json().catch(() => ({}))
    const detail = JSON.stringify(body).toLowerCase()
    expect(detail).toContain("image")
  })
})
