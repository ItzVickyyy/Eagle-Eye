import { expect, test } from "@playwright/test"
import {
  DeveloperService,
  type FeatureFlags,
  type FeatureFlagsUpdate,
} from "../src/client"
import { client as apiClient } from "../src/client/client.gen"
import { setRole } from "./utils/roleAuth"
import { apiBaseURL, ensureE2EUsers } from "./utils/userFactory"

const DEVELOPER = "developer@example.com"
const FLAG_KEY = "allow_public_signup" as const
const FLAG_SITE_KEY = "dev_allow_public_signup"
const TOGGLE_LABEL = "Public Self-Registration"

interface RuntimeSignupResult {
  status: number
  detail: string | null
}

async function fetchFeatureFlags(token: string): Promise<FeatureFlags> {
  apiClient.setConfig({
    baseURL: apiBaseURL(),
    headers: { Authorization: `Bearer ${token}` },
  })
  const res = await DeveloperService.getFeatureFlags()
  if (!res.data) {
    throw new Error("DeveloperService.getFeatureFlags returned no data")
  }
  return res.data
}

async function patchFeatureFlags(
  token: string,
  body: FeatureFlagsUpdate,
): Promise<FeatureFlags> {
  apiClient.setConfig({
    baseURL: apiBaseURL(),
    headers: { Authorization: `Bearer ${token}` },
  })
  const res = await DeveloperService.updateFeatureFlags({ body })
  if (!res.data) {
    throw new Error("DeveloperService.updateFeatureFlags returned no data")
  }
  return res.data
}

async function probePublicSignup(): Promise<RuntimeSignupResult> {
  const email = `e2e-runtime-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2, 8)}@example.com`
  const res = await fetch(`${apiBaseURL()}/api/v1/users/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password: "E2e!RuntimePass1",
      full_name: "E2E Runtime Probe",
    }),
  })
  let detail: string | null = null
  try {
    const json = (await res.json()) as { detail?: string }
    detail = json.detail ?? null
  } catch {
    detail = null
  }
  return { status: res.status, detail }
}

test.describe.configure({ mode: "serial" })

test.describe("Developer feature flags (Phase 2 E2E)", () => {
  let developerToken: string
  let originalValue: boolean

  test.beforeAll(async () => {
    const tokens = await ensureE2EUsers()
    developerToken = tokens[DEVELOPER]
    if (!developerToken) {
      throw new Error(`No token available for ${DEVELOPER}`)
    }
    const initial = await fetchFeatureFlags(developerToken)
    originalValue = initial[FLAG_KEY]
  })

  test.afterAll(async () => {
    try {
      const current = await fetchFeatureFlags(developerToken)
      if (current[FLAG_KEY] === originalValue) return
      const restored = await patchFeatureFlags(developerToken, {
        [FLAG_KEY]: originalValue,
      } as FeatureFlagsUpdate)
      if (restored[FLAG_KEY] !== originalValue) {
        throw new Error(
          `Restore mismatch: expected ${FLAG_KEY}=${originalValue}, got ${restored[FLAG_KEY]}`,
        )
      }
    } catch (error) {
      throw new Error(
        `Mandatory flag restoration failed for ${FLAG_SITE_KEY}=${originalValue}: ${(error as Error).message}`,
      )
    }
  })

  test("round-trip: invert, persist across reload, restore", async ({
    page,
  }) => {
    await setRole(page, developerToken)
    await page.goto("/admin/developer")

    await expect(
      page.getByRole("heading", { name: "Developer System Dashboard" }),
    ).toBeVisible()

    await page.getByRole("tab", { name: /Feature Flags/ }).click()

    const flagRow = page
      .locator("div", { hasText: TOGGLE_LABEL })
      .filter({ has: page.getByRole("checkbox") })
      .last()
    const toggle = flagRow.getByRole("checkbox")
    await expect(toggle).toBeVisible()

    const initialUiState = await toggle.getAttribute("data-state")
    const expectedInitial = originalValue ? "checked" : "unchecked"
    expect(initialUiState).toBe(expectedInitial)

    const inverted = !originalValue

    await toggle.click()
    await expect(toggle).toHaveAttribute(
      "data-state",
      inverted ? "checked" : "unchecked",
    )

    const persistedAfterClick = await fetchFeatureFlags(developerToken)
    expect(persistedAfterClick[FLAG_KEY]).toBe(inverted)

    await page.reload()
    await expect(
      page.getByRole("heading", { name: "Developer System Dashboard" }),
    ).toBeVisible()
    await page.getByRole("tab", { name: /Feature Flags/ }).click()
    const flagRowAfterReload = page
      .locator("div", { hasText: TOGGLE_LABEL })
      .filter({ has: page.getByRole("checkbox") })
      .last()
    const toggleAfterReload = flagRowAfterReload.getByRole("checkbox")
    await expect(toggleAfterReload).toBeVisible()
    await expect(toggleAfterReload).toHaveAttribute(
      "data-state",
      inverted ? "checked" : "unchecked",
    )
  })

  test("runtime enforcement: /signup reflects the current flag value", async () => {
    const current = await fetchFeatureFlags(developerToken)
    const currentValue = current[FLAG_KEY]

    const result = await probePublicSignup()
    if (currentValue) {
      expect(result.status).toBe(200)
      expect(result.detail).toBeNull()
    } else {
      expect(result.status).toBe(403)
      expect(result.detail).toBe("Public sign-up is temporarily disabled")
    }
  })
})
