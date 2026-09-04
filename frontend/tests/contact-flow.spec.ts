import { expect, test } from "@playwright/test"
import { getContactMessages, submitContactMessage } from "./utils/api"
import { setRole } from "./utils/roleAuth"
import { ensureE2EUsers } from "./utils/userFactory"

const ADMIN = "admin@example.com"

test.describe("Contact form flow", () => {
  let adminToken: string

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    adminToken = tokens[ADMIN]
  })

  test("guest submits a contact form and sees a success confirmation", async ({
    page,
  }) => {
    await page.goto("/contact-us")
    await page.getByLabel("Name").fill("Contact Tester")
    await page.getByLabel("Email").fill("tester@example.com")
    await page.getByLabel("Subject").fill("E2E Contact Test")
    await page.getByLabel("Message").fill("This is a test contact message.")
    await page.getByRole("button", { name: "Send Message" }).click()
    await expect(
      page.getByText(/sent successfully|has been sent/),
    ).toBeVisible()
  })

  test("admin sees a new message in the Contact Inbox", async ({ page }) => {
    const subject = `Inbox Test ${Date.now()}`
    await submitContactMessage({
      name: "Inbox Tester",
      email: "inbox@example.com",
      subject,
      message: "Please read this.",
    })
    await setRole(page, adminToken)
    await page.goto("/admin/contact")
    await expect(
      page.getByRole("heading", { name: "Contact Inbox" }),
    ).toBeVisible()
    await expect(page.getByText(subject)).toBeVisible()
  })

  test("opening a contact message auto-marks it as read", async ({ page }) => {
    const subject = `AutoRead ${Date.now()}`
    const body = "Should auto-mark as read on open."
    await submitContactMessage({
      name: "AutoRead Tester",
      email: "autoread@example.com",
      subject,
      message: body,
    })
    await setRole(page, adminToken)
    await page.goto("/admin/contact")
    const row = page.locator("tr").filter({ hasText: subject })
    await expect(row).toBeVisible()
    await row.getByTitle("View Message").click()
    const dialogBody = page.locator("[role='dialog']").getByText(body)
    await expect(dialogBody).toBeVisible()
    const messages = await getContactMessages(adminToken)
    const msg = messages.find((m: any) => m.subject === subject)
    expect(msg?.status).toBe("read")
  })
})
