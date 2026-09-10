# Eagle Eye — Security Measures

Single canonical security document. Covers the environment-file safeguards and the full specification/security audit results.

**Last verified:** 2026-09-08 (HEAD `792c43c`)

---

## 1. Security Posture Summary

| Item | Status |
|------|--------|
| P0 findings open | **0** |
| P1 findings open | **0** |
| P2 findings open | **0** |
| P3 observations (all closed or deferred) | 10 |
| Spec sections audited (§5–§10) | All **PASS** at the MUST level |

The application upholds deny-by-default authorization, per-user authentication, hashed passwords, rate limiting, CAPTCHA, CSP + security headers, XSS sanitization, and audit logging for state-changing actions.

---

## 2. Environment-File Safeguards

### 2.1 Background

A prior review raised a concern that `.env` files containing production secrets may have been committed in the repository's history. A comprehensive read-only audit of all reachable Git history was performed:

- `git ls-tree -r` across every reachable root and tree found zero tracked `.env` files.
- `git log --all --diff-filter=D -- "*.env"` returned no deletions.
- `git log -p -S "SECRET_KEY=" -- "*.env"` and equivalent pickaxe searches for `POSTGRES_PASSWORD` found no matches in any `.env` file.

**Conclusion:** `.env` and `frontend/.env` were never committed to Git. No secrets were exposed through the repository's history. No rotation is required.

### 2.2 Preventive Measures (Implementation 12A)

Although no exposure occurred, the following safeguards were added:

- `.gitignore` rules so real `.env` / `.env.*` files are ignored, while `.env.example` templates remain trackable.
- `.env.example` and `frontend/.env.example` templates (no real secrets — `change-me` placeholders only).
- A dependency-free pre-commit guard (`scripts/guard-secrets.sh` wired into `.pre-commit-config.yaml`) that blocks any future commit that would track a real `.env` file. It runs locally and in the existing `pre-commit.yml` CI.

### 2.3 Current State

| Item | Status |
|------|--------|
| `.env` / `.env.*` in `.gitignore` | Present |
| `.env.example` and `frontend/.env.example` in repo | Present (placeholders only) |
| Pre-commit guard (`guard-secrets.sh`) | Active |
| `.env` files tracked in Git history | **None — never committed** |

### 2.4 Operator Guidance

- Keep production secrets in environment variables or GitHub Actions secrets, never in source-controlled files.
- Rotate secrets periodically per organizational policy.
- Run `scripts/guard-secrets.sh` locally or rely on the `pre-commit.yml` CI check to prevent accidental commits of real `.env` files.

---

## 3. Security Principles Verified

The audit verified the following security properties, all upheld by the implementation:

- **Deny by default:** Every role-gated endpoint uses a FastAPI dependency that rejects requests lacking the required role/flag.
- **Per-user authentication:** No shared admin/super-admin credentials. All accounts are individual and authenticate against the `User` table.
- **Object-level authorization for unpublished content:** Authors can read their own drafts/pending articles; everyone else (including unrelated admins) receives 404, not 403.
- **Server-controlled identity fields:** `author_id`, `date_published`, `status` for first-time creation are server-controlled and cannot be injected by a client.
- **Hashed password storage:** Argon2 (with bcrypt available) via `pwdlib`; plain-text passwords are never persisted.
- **Input validation:** Pydantic/SQLModel type validation; HTML sanitization on article `body`; URL allowlist on media uploads.
- **Rate limiting:** Login, signup, password-recovery, password-reset, password-change, contact, and comment endpoints are rate-limited. Redis-backed when `REDIS_URL` is set; falls back to in-memory when not.
- **CAPTCHA (Cloudflare Turnstile):** Applied to public signup, password-recovery, password-reset, and contact submission. `_validate_captcha_configuration` refuses to boot in production when CAPTCHA is enabled but keys are missing.
- **CSP + security headers:** `add_security_headers` middleware emits `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` (HTTPS only), `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `Cross-Origin-Opener-Policy: same-origin`, and `Cross-Origin-Resource-Policy: same-origin`. Only Cloudflare Turnstile is allow-listed in CSP.
- **Auditability:** State-changing actions write an entry to the `AuditLog` table via `app.core.audit.write_audit_log`.
- **Token rotation on password change:** `bump_token_version` invalidates prior sessions on password change.
- **Developer isolation:** `is_developer` is a separate boolean flag from `is_superuser` and `role`. A Developer session does not automatically become a Super Admin session.

---

## 4. Specification Audit Results

### 4.1 Summary

| Section | Area | Verdict |
|---|---|---|
| 5.1 | Public-Facing / Guest | PASS |
| 5.2 | Contributor | PASS |
| 5.3 | Admin / Editor | PASS |
| 5.4 | Super Admin | PASS |
| 5.5 | Developer | PASS |
| 5.6 | System-Wide / Non-Functional | PASS |
| 6 | Data Model | PASS |
| 7 | Sitemap | PASS (with P3 SHOULD-level deviations) |
| 8.2 | V5 Legacy Parity Gate | PASS (with P3 observations) |
| 9 | Technical Foundation | PASS |
| 10 | Quick Feature Checklist | PASS |

### 4.2 Data Model Coverage

All 12 spec tables have matching backend models: `User`, `Article`, `Category`, `Tag`, `ArticleTag`, `Media`, `Comment`, `ClubMember`, `ContactMessage`, `SiteSetting`, `AuditLog`, `TokenRevocation`.

### 4.3 Functional Acceptance Criteria

All functional gates pass: login, invalid-credential rejection, role-gated access, article CRUD lifecycle, comment moderation, public browsing, search, and pagination.

---

## 5. Security Findings

### 5.1 Closed Findings

| ID | Description | Severity | Status |
|---|---|---|---|
| D1 | Object-level authorization defect on unpublished articles — unrelated admins could read another user's unpublished article | P1 | **CLOSED** — `_can_view_unpublished_article` helper returns 404 to non-authors; regression-tested in `test_rbac_hardening.py` |
| D2 | Not a defect — audit harness used `content` instead of schema's `body` field | — | **CLOSED** — no code change required |
| D5 | Contributor publication data-integrity defect — contributor PATCH with `status=published` caused `date_published` to be assigned while article was still pending | P1 | **CLOSED** — contributor `status` coerced to `pending`; `date_published` only set on admin publish; regression-tested in `test_articles.py` |
| O3 | Audit events missing on destructive hard-deletes (6 endpoints) | P3 SHOULD | **CLOSED** — `write_audit_log` added to all 6 endpoints; tested in `test_o3_audit_on_delete.py` |
| O4 | `POST /tags/` requires only `CurrentUser` (not Admin) | P3 OBSERVATION | **CLOSED** — intentional; contributors need tag creation for article-create flow |
| O5 | No server-side pagination/list-limit caps on 10 public endpoints | P3 SHOULD | **CLOSED** — `safe_limit = max(1, min(int(limit), 200))` applied to all 10; tested in `test_o5_pagination_caps.py` |
| O6 | Frontend uses `/admin/...` not `/dashboard/...` | P3 OBSERVATION | **CLOSED** — internal naming preference; no functional impact |
| O7 | No dynamic `/[category]/[slug]` route | P3 OBSERVATION | **CLOSED** — URL structure choice; unique slugs make per-category routing unnecessary |
| O8 | No dedicated `/articles/[id]/edit` route | P3 OBSERVATION | **CLOSED** — query-string variant reuses same component; bookmarkable |
| O9 | Mailpit not provisioned in `compose.yml` | P3 SHOULD | **CLOSED** — already in `compose.override.yml:90-94`; live-verified (`http://localhost:8025` returns 200, container healthy) |
| O10 | Categories seed coverage (only News + Sports seeded) | P3 OBSERVATION | **CLOSED** — stale observation; all 4 spec categories (`News`, `Academics`, `Sports`, `Events`) are seeded in `db.py:45-50` |
| D3 | `tags: []` in article responses | P3 OBSERVATION | **CLOSED** — seed-data gap; `db.py` seed now attaches tags to first 4 articles; live-DB migration applied |
| D4 | `school_name` UTF-8 mojibake | P3 OBSERVATION | **CLOSED** — not a defect; correct UTF-8 stored in DB; "mojibake" was a PowerShell console-codec display artifact |

### 5.2 Deferred (Out of Scope)

| ID | Description | Reason |
|---|---|---|
| O11 | No explicit "intentionally removed" legacy list for §8.2 | Documentation follow-up, not a security defect. Actual list derivable from `git log --diff-filter=D --name-only`. |
| Reviewer / ReviewAssignment | Spec refers to a Reviewer workflow but no `Reviewer` or `ReviewAssignment` model exists | Architectural follow-up requiring a new model and migration. The current 404-on-deny approach is the correct fallback. |

### 5.3 Severity Summary

| State | Count | IDs |
|---|---|---|
| P0 (critical) | 0 | — |
| P1 (high) | 0 | — |
| P2 (meaningful hardening) | 0 | — |
| Closed (P1) | 2 | D1, D5 |
| Closed (P3 SHOULD) | 3 | O3, O5, O9 |
| Closed (not-a-defect) | 4 | D2, D3, D4, O10 |
| Closed (intentional / not-a-defect) | 4 | O4, O6, O7, O8 |
| Deferred (documentation follow-up) | 1 | O11 |
| Spec gaps | 1 | Reviewer / ReviewAssignment |

---

## 6. Current Security Posture

The application currently maintains:

- Per-user authentication with argon2 password hashing
- Role-based authorization (Contributor / Admin / Super Admin) enforced at the dependency level
- Developer access isolated from club RBAC (`is_developer` independent of `role` and `is_superuser`)
- CSP, security headers, rate limiting, CAPTCHA, and XSS sanitization all live
- Audit logging for all state-changing actions (including destructive hard-deletes)
- Token rotation invalidating prior sessions on password change
- Object-level authorization for unpublished content (404, not 403)
- Server-side pagination caps (max 200) on all list endpoints
- Environment-file safeguards (`.gitignore`, `.env.example` templates, pre-commit guard)

This document does not claim "100% secure", "fully penetration tested", or "production security certified". The findings reflect the evidence available at the time of review and the test accounts / live services used during verification.

---

## 7. Recommended Hardening Order

None of these are required before continuing further work. Recorded for future hardening.

1. ~~O5: server-side pagination/list-limit caps~~ — **CLOSED** (2026-09-08)
2. ~~O9: Mailpit provisioning~~ — **CLOSED** (already in `compose.override.yml`)
3. ~~D4: encoding / data-quality~~ — **CLOSED** (not a defect)
4. ~~D3: `tags: []` root-cause~~ — **CLOSED** (seed-data gap)
5. ~~O3: audit events for destructive hard-deletes~~ — **CLOSED**
6. O11: documentation follow-up — intentional legacy-removal list
7. Reviewer / ReviewAssignment — architectural follow-up (requires new model)

---

*End of document.*
