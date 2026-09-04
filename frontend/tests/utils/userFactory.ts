import fs from "node:fs"
import path from "node:path"

import { firstSuperuser, firstSuperuserPassword } from "../config"

export { firstSuperuser }

export const E2E_PASSWORD = "E2e!RolePass1"

const STATE_FILE = path.join(process.cwd(), "playwright", ".e2e-users.json")
const LOCK_FILE = `${STATE_FILE}.lock`

export interface E2ERoleUser {
  email: string
  password: string
  fullName: string
  role: "contributor" | "admin" | "super_admin"
  isDeveloper: boolean
}

/**
 * Deterministic role-specific test accounts. Reserved emails allow the
 * helper to be run any number of times without clobbering unrelated data.
 */
export const E2E_USERS: E2ERoleUser[] = [
  {
    email: "contributor@example.com",
    password: E2E_PASSWORD,
    fullName: "E2E Contributor",
    role: "contributor",
    isDeveloper: false,
  },
  {
    email: "admin@example.com",
    password: E2E_PASSWORD,
    fullName: "E2E Admin",
    role: "admin",
    isDeveloper: false,
  },
  {
    email: "developer@example.com",
    password: E2E_PASSWORD,
    fullName: "E2E Developer",
    role: "contributor",
    isDeveloper: true,
  },
  {
    email: "admindeveloper@example.com",
    password: E2E_PASSWORD,
    fullName: "E2E Admin Developer",
    role: "admin",
    isDeveloper: true,
  },
  {
    email: "superadminnoidev@example.com",
    password: E2E_PASSWORD,
    fullName: "E2E Super Admin",
    role: "super_admin",
    isDeveloper: false,
  },
]

export function apiBaseURL(): string {
  return process.env.VITE_API_URL ?? "http://127.0.0.1:8000"
}

export async function apiRequest(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<any> {
  const headers: Record<string, string> = {
    ...((init.headers as Record<string, string>) ?? {}),
  }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${apiBaseURL()}${path}`, { ...init, headers })
  const isJson = (res.headers.get("content-type") ?? "").includes("json")
  const body = isJson ? await res.json() : await res.text()
  if (!res.ok) {
    const detail =
      body?.detail ?? (typeof body === "string" ? body : "request failed")
    throw new Error(
      `API ${init.method ?? "GET"} ${path} -> ${res.status}: ${JSON.stringify(detail)}`,
    )
  }
  return body
}

export async function apiLogin(
  email: string,
  password: string,
): Promise<string> {
  const body = new URLSearchParams()
  body.set("username", email)
  body.set("password", password)
  const data = await apiRequest("/api/v1/login/access-token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  })
  if (!data?.access_token) {
    throw new Error(`Login for ${email} returned no access token`)
  }
  return data.access_token
}

export async function apiCreateUser(
  superToken: string,
  user: E2ERoleUser,
): Promise<string> {
  const data = await apiRequest(
    "/api/v1/users/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: user.email,
        password: user.password,
        full_name: user.fullName,
        role: user.role,
        is_developer: user.isDeveloper,
        is_active: true,
      }),
    },
    superToken,
  )
  return data.id as string
}

export async function apiFindUserId(
  superToken: string,
  email: string,
): Promise<string | null> {
  const data = await apiRequest("/api/v1/users/", {}, superToken)
  const rows: Array<{ id: string; email: string }> = data?.data ?? []
  const match = rows.find((u) => u.email === email)
  return match?.id ?? null
}

export async function apiUpdateUser(
  superToken: string,
  userId: string,
  patch: Record<string, unknown>,
): Promise<void> {
  await apiRequest(
    `/api/v1/users/${userId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    },
    superToken,
  )
}

/**
 * Ensures every E2E role account exists with the intended role/developer
 * config, returning a map of email -> access token so specs can act as any
 * role without going through the UI.
 *
 * Login is rate-limited by the app (in-memory 20/min per client IP), so this
 * helper performs the expensive login/setup work ONCE per backend process and
 * caches the resulting tokens to `playwright/.e2e-users.json`. Parallel
 * workers then reuse the cache instead of hammering the login endpoint (the
 * security boundary is never bypassed). A lock file serializes the initial
 * setup across concurrent workers.
 */
export async function ensureE2EUsers(): Promise<Record<string, string>> {
  const cached = readTokenCache()
  if (cached && (await validateTokens(cached))) {
    return cached
  }

  for (let attempt = 0; attempt < 120; attempt++) {
    if (await tryAcquireLock()) {
      try {
        const again = readTokenCache()
        if (again && (await validateTokens(again))) {
          return again
        }
        const tokens = await performFullSetup()
        writeTokenCache(tokens)
        return tokens
      } finally {
        releaseLock()
      }
    }
    await sleep(500)
    const fresh = readTokenCache()
    if (fresh && (await validateTokens(fresh))) {
      return fresh
    }
  }

  const fallback = readTokenCache()
  if (fallback) return fallback
  throw new Error("Could not acquire E2E user setup lock within timeout")
}

async function performFullSetup(): Promise<Record<string, string>> {
  const superToken = await apiLogin(firstSuperuser, firstSuperuserPassword)
  const tokens: Record<string, string> = { [firstSuperuser]: superToken }
  for (const user of E2E_USERS) {
    const existingId = await apiFindUserId(superToken, user.email)
    if (existingId) {
      await apiUpdateUser(superToken, existingId, {
        role: user.role,
        is_developer: user.isDeveloper,
        is_active: true,
      })
    } else {
      try {
        await apiCreateUser(superToken, user)
      } catch {
        // Parallel creation race -> another worker created it first; login below.
      }
    }
    tokens[user.email] = await apiLogin(user.email, user.password)
  }
  return tokens
}

async function getMe(token: string): Promise<boolean> {
  try {
    await apiRequest("/api/v1/users/me", {}, token)
    return true
  } catch {
    return false
  }
}

async function validateTokens(
  tokens: Record<string, string>,
): Promise<boolean> {
  const emails = [...E2E_USERS.map((u) => u.email), firstSuperuser]
  for (const email of emails) {
    const token = tokens[email]
    if (!token) return false
    if (!(await getMe(token))) return false
  }
  return true
}

function readTokenCache(): Record<string, string> | null {
  try {
    const raw = fs.readFileSync(STATE_FILE, "utf8")
    const parsed = JSON.parse(raw)
    return parsed?.tokens && typeof parsed.tokens === "object"
      ? (parsed.tokens as Record<string, string>)
      : null
  } catch {
    return null
  }
}

function writeTokenCache(tokens: Record<string, string>): void {
  try {
    fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true })
    fs.writeFileSync(
      STATE_FILE,
      JSON.stringify({ tokens, recordedAt: Date.now() }, null, 2),
    )
  } catch {
    // best-effort cache write; a later full setup is tolerable
  }
}

function tryAcquireLock(): boolean {
  try {
    const fd = fs.openSync(LOCK_FILE, "wx")
    fs.closeSync(fd)
    return true
  } catch {
    return false
  }
}

function releaseLock(): void {
  try {
    fs.unlinkSync(LOCK_FILE)
  } catch {
    // already released
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
