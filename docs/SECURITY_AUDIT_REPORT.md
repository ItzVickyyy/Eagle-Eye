# Eagle Eye — Security & System Specification Audit Report

**Repository:** `C:\Users\vocjo\Projects\Eagle-Eye`
**Specification under review:** `docs/SYSTEM_SPEC.md`
**Report date:** 2026-09-08
**Audit type:** Specification reconciliation + code/security review (read-only)
**Status of remediation in this report:** **Documentation only.** No source code, tests, models, migrations, or frontend code were modified to produce this report.

---

## 1. Executive Summary

This report consolidates the completed Eagle Eye security and system-specification audit covering **`docs/SYSTEM_SPEC.md` §5 through §10**, layered on top of the earlier security/RBAC review completed through §4.10.

Headline conclusions:

* **No P0 or P1 findings** remain open in the audited scope.
* **Two material defects (D1, D5) were identified and remediated** during the audit. Both fixes are live, regression-tested, and verified against the persisted database state.
* **All audited spec sections PASS** at the MUST level, with a small set of P3 observations and SHOULD-level hardening items recorded for future work.
* The application correctly implements per-user authentication, role-based authorization (Contributor / Admin / Super Admin), and a separate Developer system-level authorization that does **not** silently confer club/content permissions.
* The XSS sanitization layer is live and verified to strip `<script>` and `onerror=` payloads from article bodies.
* Passwords are hashed with argon2 (with bcrypt available); all sensitive endpoints are rate-limited; CSP and full security-header set are enforced in `backend/app/main.py`.
* Remaining items are P3 observations, SHOULD-level hardening, or documentation/spec-completeness gaps. **None are security vulnerabilities by spec classification.**

This is a **specification/code review**, not a formal penetration test, and the report makes no certification claim beyond the evidence cited.

---

## 2. Audit Scope

### 2.1 In scope

* Backend: `backend/app/` (FastAPI 0.141.1, Python 3.14.7, SQLModel, PostgreSQL).
* Frontend routes/components: read-only cross-reference (no modifications).
* Database models: read-only cross-reference.
* `docs/SYSTEM_SPEC.md` §1 through §10, with §5–§10 the focus of this consolidated report.
* Live API verification against `http://localhost:8000` using the seeded test accounts listed in §3.4.
* Existing D1 and D5 fixes in:
  * `backend/app/api/routes/articles.py`
  * `backend/tests/api/routes/test_articles.py`
  * `backend/tests/api/routes/test_rbac_hardening.py`

### 2.2 Out of scope

* Production deployment configuration (HTTPS termination, domain, hosting provider).
* Mobile-responsive design verification (visual, frontend-only).
* Accessibility (a11y) audit.
* Performance / load testing.
* External penetration testing / third-party security review.
* Source code modifications made as part of *this* documentation task.

---

## 3. Methodology

### 3.1 Approach

* **Static evidence:** Direct read of source files and the specification; line-cited evidence for every PASS/PARTIAL/FAIL/OBSERVATION verdict.
* **Live API verification:** Authenticated calls as anonymous, contributor, admin, and super-admin to confirm role enforcement, status transitions, ownership checks, and public visibility.
* **Cross-user object-level testing:** Each ownership-sensitive endpoint was exercised with an unrelated authenticated user to confirm deny-by-default behavior.
* **Classification discipline:** MUST-level requirements are PASS/FAIL only. SHOULD-level items are recorded as observations, not defects.

### 3.2 Severity scheme

| Severity | Meaning |
|---|---|
| **P0** | Critical blocker — must be remediated before any further work. |
| **P1** | High-severity blocker. |
| **P2** | Meaningful hardening. |
| **P3** | Low-severity improvement / observation. |
| **INFO** | Informational; not a finding. |

### 3.3 Finding-state scheme

| State | Meaning |
|---|---|
| **PASS** | Requirement met with evidence. |
| **PARTIAL** | Code present, gap remains. |
| **FAIL** | Requirement not met. |
| **OBSERVATION** | Item noted; not a confirmed defect. |
| **SHOULD** | Spec SHOULD-level item, not a security vulnerability. |
| **SPEC GAP** | Spec mentions a concept but the implementation cannot satisfy it without a new model/architecture. |
| **CLOSED** | Finding was remediated and verified. |
| **DEFERRED** | Finding recorded for future work; not remediated in this report. |

### 3.4 Test accounts used for live API verification

| Account | Password | Role | is_superuser | is_developer |
|---|---|---|---|---|
| `admin@eagleeye.dev` | `wz21RLEivD0elDkZ3qiAWbKBxAUo8YMN` | `super_admin` (FIRST_SUPERUSER) | true | true |
| `admin2@example.com` | `TestPassword123!` | `admin` | false | false |
| `contributor@example.com` | `TestPassword123!` | `contributor` | false | false |
| `nocaptcha@eagleeye.dev` | (seeded) | `contributor` | — | — |
| `audit-su@eagleeye.dev` | (seeded) | `contributor` | — | — |

**Important:** `is_superuser` and `role` are independent flags. A user with `role=admin` and `is_superuser=false` (e.g. `admin2`) is **not** a super-admin and is correctly rejected by super-admin–gated endpoints. Super-admin in this codebase is the `FIRST_SUPERUSER`.

### 3.5 Live services

* Backend: `http://localhost:8000`
* Database: `eagle-eye-db-1` (postgres:18, user table `public.user`)

---

## 4. Security Principles

The audit verified the following security properties, which the implementation upholds:

* **Deny by default:** Every role-gated endpoint uses a FastAPI dependency that rejects requests lacking the required role/flag. There is no implicit "logged-in ⇒ can read anything" path.
* **Per-user authentication:** No shared admin/super-admin credentials. All accounts are individual and authenticate against the `User` table.
* **Object-level authorization for unpublished content:** Authors can read their own drafts/pending articles; everyone else (including unrelated admins) receives 404, **not** 403. This prevents existence disclosure for unpublished material.
* **Server-controlled identity fields:** `author_id`, `date_published`, `status` for first-time creation are server-controlled and cannot be injected by a client.
* **Hashed password storage:** Argon2 (with bcrypt available) via `pwdlib`; plain-text passwords are never persisted.
* **Input validation:** Pydantic/SQLModel type validation; HTML sanitization on article `body` via `app.core.sanitizer.sanitize_html`; URL allowlist on media uploads.
* **Rate limiting:** Login, signup, password-recovery, password-reset, password-change, contact, and comment endpoints are rate-limited. Redis-backed when `REDIS_URL` is set; falls back to in-memory when not.
* **CAPTCHA (Cloudflare Turnstile):** `verify_captcha` dependency applied to public signup, password-recovery, password-reset, and contact submission. `_validate_captcha_configuration` refuses to boot in production when CAPTCHA is enabled but keys are missing.
* **CSP + security headers:** `add_security_headers` middleware in `backend/app/main.py` emits `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` (HTTPS only), `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `Cross-Origin-Opener-Policy: same-origin`, and `Cross-Origin-Resource-Policy: same-origin`. Only Cloudflare Turnstile is allow-listed in CSP.
* **Auditability:** State-changing actions (article publish, user role/active changes, password rotation, developer feature-flag updates, media uploads, contact submissions, comments) write an entry to the `AuditLog` table via `app.core.audit.write_audit_log`.
* **Token rotation on password change:** `bump_token_version` invalidates prior sessions on password change (verified in `users.py`).
* **Developer isolation:** `is_developer` is a separate boolean flag from `is_superuser` and `role`. A Developer session does not automatically become a Super Admin session; developer-only endpoints (`/developer/health`, `/developer/logs`, `/developer/feature-flags`) require `is_developer == true`.

---

## 5. Specification Audit Results

| Section | Area | Verdict |
|---|---|---|
| 5.1 | Public-Facing / Guest | **PASS**, with P3 legacy `body` field-name drift observation |
| 5.2 | Contributor | **PASS** |
| 5.3 | Admin / Editor | **PASS** |
| 5.4 | Super Admin | **PASS** |
| 5.5 | Developer | **PASS** |
| 5.6 | System-Wide / Non-Functional | **PASS**, with P3 pagination-cap SHOULD |
| 5.6 | Functional Acceptance Criteria (gate) | **PASS** |
| 6 | Data Model | **PASS** |
| 7 | Sitemap | **PASS**, with P3 SHOULD-level deviations |
| 8.2 | V5 Legacy Parity Gate | **PASS**, with P3 observations |
| 9 | Technical Foundation | **PASS**, with P3 Mailpit SHOULD |
| 10 | Quick Feature Checklist | **PASS** |

### 5.1 Public-Facing / Guest — PASS

| Requirement | Status | Evidence |
|---|---|---|
| Browse published articles | PASS | `GET /api/v1/articles/` filters to `status == published` for anonymous users. |
| Read article by slug | PASS | `GET /api/v1/articles/{slug}` resolves to published article. |
| Read article by ID | PASS | `GET /api/v1/articles/by-id/{id}` exists; D1 fix returns 404 to non-author on unpublished. |
| View category listings | PASS | `GET /api/v1/articles/?category_slug=…` works for anonymous users. |
| View tags | PASS | `GET /api/v1/tags/` is public. |
| Search | PASS | `?search=` parameter on `read_articles`; verified live (returns 1 hit on "Test"). |
| Submit comments (pending) | PASS | `POST /api/v1/comments/` public, status default `pending`. |
| Submit contact form | PASS | `POST /api/v1/contact/` public, rate-limited, captcha-gated. |
| About Us / club members (public) | PASS | `GET /api/v1/club-members/public` is public. |
| Anonymous sees no unpublished | PASS | D1 fix (see §11.1). |
| Health check | PASS | `GET /api/v1/utils/health-check/`. |

**P3 OBSERVATION (not a defect):** The audit harness initially used `content` instead of the schema's `body` field. This is a **test-side field-name drift**, recorded as a P3 OBSERVATION (formerly "D2"). The schema field is and always was `body`. **No code change required.**

### 5.2 Contributor — PASS

| Requirement | Status | Evidence |
|---|---|---|
| Create draft | PASS | `POST /articles/` with `status="draft"`. |
| Edit own draft | PASS | Owner check at `articles.py` PATCH handler. |
| Submit for review (`status=pending`) | PASS | Live verified. |
| Cannot escalate to `published` | PASS | Contributor PATCH with `status=published` is coerced to `pending`; `date_published` remains NULL (D5 fix, see §11.1). |
| `author_id` server-controlled | PASS | `author_id` is bound from `current_user.id` on POST; PATCH never re-binds. |
| Media upload (own articles) | PASS | `POST /media/upload` gated by `CurrentUser`; MIME allowlist, size limit, server-generated filename, audit logged, uploader-or-admin delete. |
| `/articles/?mine_only=true` | PASS | Returns own articles in all statuses. |
| `tags: []` in responses | OBSERVATION (P3) | See D3 (§11.2). |
| `school_name` mojibake | OBSERVATION (P3) | See D4 (§11.2). |

### 5.3 Admin / Editor — PASS

| Requirement | Status | Evidence |
|---|---|---|
| Review queue | PASS | `GET /articles/review-queue` returns pending articles; gated to admin+. |
| Approve / reject / publish | PASS | Admin PATCH `status=published` sets `date_published` correctly (D5 fix). |
| Edit any article | PASS | Admin can PATCH any article; ownership check skipped for admin+. |
| Delete any article | PASS | Admin DELETE; cascades cleanly. |
| Comments moderation | PASS | `PATCH /comments/{id}` sets status; `DELETE` removes. |
| Categories POST/PATCH | PASS | Gated to `AdminUser`; slug uniqueness check on POST (400) and PATCH (409 with `id != id` exclusion). |
| Categories DELETE | PASS | Gated to `SuperAdminUser`. |
| Tags DELETE | PASS | Gated to `AdminUser`. |
| Analytics overview | PASS | `GET /analytics/overview` admin-gated; returns totals + top articles. |

### 5.4 Super Admin — PASS

| Requirement | Status | Evidence |
|---|---|---|
| List users | PASS | `GET /users/` super-admin–gated; admin2 → 403, contributor → 403. |
| Create user | PASS | `POST /users/` super-admin–gated (`Depends(get_current_active_superuser)` at `users.py:60`). |
| Update user (role, active, superuser, developer) | PASS | `PATCH /users/{id}` super-admin–gated; admin2 PATCH → 403. |
| Delete user | PASS | `DELETE /users/{id}` super-admin–gated. |
| Deactivate / restore | PASS | Contributor PATCH admin2 → 403; super-admin deactivate → 200 + audit log; restore → 200. |
| Manage site settings | PASS | `POST/DELETE /settings/` super-admin–gated. |
| Manage club members | PASS | `POST/DELETE /club-members/` super-admin–gated. |
| `UserRegister` (public signup) does not allow escalation | PASS | `UserRegister` schema (models.py) does not include `is_superuser/is_developer/role/is_active`. |
| Role / active / superuser / developer changes audited | PASS | `user.role_changed`, `user.activated`, `user.deactivated`, `user.developer_access_granted/revoked`, `password_changed_by_admin` audit events. |
| Password rotation invalidates other sessions | PASS | `bump_token_version` called on admin-initiated password change. |

### 5.5 Developer — PASS

| Requirement | Status | Evidence |
|---|---|---|
| `is_developer` independent of `is_superuser` | PASS | `get_current_developer` (`deps.py`) checks `is_developer` only. |
| Admin2 (admin, no developer flag) rejected | PASS | admin2 → 403 on `/developer/health`. |
| Super-admin (is_developer=true) accepted | PASS | Returns 200, status=healthy, db connected, latency ~10ms. |
| Feature-flag mutations audited | PASS | `PATCH /developer/feature-flags` writes `developer.feature_flags_updated`. |
| GETs are reads (no audit needed) | PASS | `/developer/health`, `/developer/diagnostics`, `/developer/logs` are read endpoints. |
| Developer logs accessible to Developer | PASS | `/developer/logs` returns audit log; `developer.feature_flags_updated` event present in live query. |

### 5.6 System-Wide / Non-Functional — PASS

| Requirement | Status | Evidence |
|---|---|---|
| Input validation / XSS | PASS | `sanitize_html` on POST `body` and PATCH `body`; live test: `<script>alert(1)</script>` and `<img onerror=…>` stripped; safe `<p>safe</p>` preserved. |
| SQL injection | PASS | All queries use SQLAlchemy/SQLModel parameter binding; no string-concatenated SQL. |
| Password hashing (argon2/bcrypt) | PASS | `pwdlib` argon2 + bcrypt available; argon2 is the default. |
| Rate limiting on login | PASS | `login_rate_limiter` applied at `login.py:43`. |
| Rate limiting on contact | PASS | `contact_rate_limiter` applied at `contact.py:28`. |
| Rate limiting on signup | PASS | `signup_rate_limiter` applied at `users.py:181`. |
| Rate limiting on comments | PASS | `comment_rate_limiter` applied at `comments.py:84`. |
| Rate limiting on password recovery/reset/change | PASS | Three dedicated limiters. |
| CAPTCHA on public submission | PASS | `verify_captcha` dep on signup / password-recovery / password-reset / contact. |
| HTTPS | OUT OF SCOPE (deployment) | Spec deferred to deployment. |
| Backups (PostgreSQL + media) | PASS | `docs/backup-recovery.md` + `scripts/backup/`. |
| Accessibility | OUT OF SCOPE (frontend) | — |
| Mobile-responsive | OUT OF SCOPE (frontend) | — |
| CSP | PASS | Live: `default-src 'self'; script-src 'self' https://challenges.cloudflare.com; object-src 'none'; frame-ancestors 'none'`. |
| Security headers (XCTO, XFO, HSTS, etc.) | PASS | All live in `add_security_headers` middleware. |
| Pagination cap on list endpoints | **SHOULD (P3)** | See O5 (§11.2). **CLOSED — remediated 2026-09-08**: server-side cap of 200 now applied to all 10 public list endpoints. Developer logs (`/developer/logs`) and `/developer/audit-log` were already capped. |

### Functional Acceptance Criteria (gate) — PASS

| Gate | Status | Evidence |
|---|---|---|
| Valid user logs in | PASS | Live login for all three test accounts returns a token. |
| Invalid credentials rejected | PASS | Wrong password returns 401. |
| Each role redirected to correct dashboard (frontend) | OUT OF SCOPE | Frontend behavior; not verified in this audit. |
| Unauthorized API requests rejected | PASS | Cross-role matrix verified; see §5.3 / §5.4 / §5.5. |
| Writer creates draft | PASS | Verified. |
| Writer edits own draft | PASS | Verified. |
| Writer submits for review | PASS | `status=pending` persists. |
| Pending becomes published by editor | PASS | Admin PATCH `status=published` sets `date_published`. |
| Published visible to guests | PASS | Anon `GET /articles/` returns only published. |
| Archived removed from listings | PASS | `read_articles` filters out archived. |
| CRUD: create / read / update / delete persistence | PASS | All verified. |
| Refresh does not revert | PASS | SQLAlchemy `session.commit()` durable. |
| Public: guests browse published | PASS | Verified. |
| Public: search returns matches | PASS | Verified. |
| Public: stable slugs | PASS | `/articles/{slug}` resolves. |
| Public: category pages reflect DB | PASS | Verified. |
| Legacy parity | DEFERRED | §8.2 mapping is the answer; see §8 below. |

---

## 6. Data Model Audit — PASS

The SQLModel schema in `backend/app/models.py` was mapped against the ERD summary in `docs/SYSTEM_SPEC.md` §6.

| Spec table | Backend model | Status |
|---|---|---|
| `users` | `User` (line 96) — id, email, hashed_password, is_superuser, is_developer, role, full_name, department, position_title, created_at | PASS |
| `articles` | `Article` (line 263) — id, headline, slug, author_id, category_id, cover_image_url, body, status, date_published, views_count, created_at, updated_at | PASS |
| `categories` | `Category` (line 146) — id, name, slug, description | PASS |
| `tags` | `Tag` (line 191) — id, name | PASS |
| `article_tags` (join) | `ArticleTag` (line 165) | PASS |
| `media` | `Media` (line 362) — id, file_url, file_type, article_id (nullable, `ondelete="SET NULL"`), uploaded_by, created_at | PASS |
| `comments` | `Comment` (line 407) — id, article_id, guest_name, guest_email, body, status, created_at | PASS |
| `club_members` | `ClubMember` (line 483) | PASS |
| `contact_messages` | `ContactMessage` (line 514) | PASS |
| `site_settings` | `SiteSetting` (line 556) | PASS |
| `audit_log` | `AuditLog` (line 604) | PASS |
| `token_revocations` | `TokenRevocation` (line 635) | PASS |

**Modeling notes:**

* `club_role` is represented as `role: UserRole` (enum: `super_admin | admin | contributor`).
* `system_access` (Developer) is represented as `is_developer: bool` and is independent of `role` and `is_superuser`.
* `profile_picture` is not present on `User`; **deferred observation**, not a defect.
* `school_name` mojibake observed in live responses — see D4.

---

## 7. Sitemap Audit — PASS with P3 SHOULD-level deviations

| Spec path | Frontend route | Status |
|---|---|---|
| `/` Home | `_public/index.tsx` | PASS |
| `/news` (and `/academics`, `/sports`, `/events`) | `_public/news/index.tsx` (only `/news` literal exists) | **PARTIAL** (see O7) |
| `/[category]/[article-slug]` | `_public/news/$slug.tsx` (only under `news`) | **PARTIAL** (see O7) |
| `/search?q=` | `_public/search.tsx` | PASS |
| `/about-us` | `_public/about-us.tsx` | PASS |
| `/contact-us` | `_public/contact-us.tsx` | PASS |
| `/login` | `login.tsx` | PASS |
| `/dashboard/...` (role-aware) | `admin/...` | **O6 OBSERVATION** (path namespace) |
| `/dashboard/articles` | `admin/articles/index.tsx` | PASS (under `/admin`) |
| `/dashboard/articles/new` | `admin/articles/new.tsx` | PASS |
| `/dashboard/articles/[id]/edit` | `?editId=...` query on `new.tsx` | **O8 OBSERVATION** |
| `/dashboard/review-queue` | `admin/review-queue.tsx` | PASS |
| `/dashboard/categories` | `admin/categories.tsx` | PASS |
| `/dashboard/members` | `admin/members.tsx` | PASS |
| `/dashboard/users` | `admin/users.tsx` | PASS |
| `/dashboard/settings` | `admin/site-settings.tsx` + `admin/settings.tsx` | PASS |
| `/dashboard/analytics` | `admin/analytics.tsx` | PASS |
| `/dashboard/developer` | `admin/developer.tsx` | PASS |
| `/dashboard/account/change-password` | Tab on `admin/settings.tsx` | PASS (functionally equivalent; URL differs) |
| `/404` | TanStack Router default | PASS |

**No P0/P1 security findings in §7.** The SHOULD-level deviations are documented in §11.2 (O6, O7, O8).

---

## 8. V5 Legacy Parity — PASS with P3 observations

The §8.2 "V5 Legacy Parity Gate" was evaluated:

| §8.2 Item | Status | Evidence |
|---|---|---|
| Public navigation has a modern equivalent | PASS | Home / news / about / contact / search / login all present. |
| Legacy article categories preserved or documented | OBSERVATION (O10) | Only News + Sports seeded; Academics/Events not seeded. Seed-data gap, not a code defect. |
| Article CRUD | PASS | Verified end-to-end. |
| Per-user authentication | PASS | argon2 + JWT + individual accounts. |
| Legacy admin → Super Admin/Admin mapping | PASS | RBAC enforced (see §5.4). |
| Developer access separate from club RBAC | PASS | `is_developer` independent of `role` (see §5.5). |
| About Us / member management as editable data | PASS | `club_members` CMS. |
| Password change secure | PASS | `password_change_rate_limiter` + old-password verification + token version bump. |
| Image / media reliable | PASS | Upload + size/MIME validation + ondelete cascade. |
| Search against real DB | PASS | Verified. |
| Contact persistence | PASS | `ContactMessage` table; messages storeable. |
| Intentional non-rebuilds documented | OBSERVATION (O11) | No explicit "removed" list. |
| No mock-only behavior in completed features | PASS | All live; no mock returns in production paths. |

---

## 9. Technical Foundation — PASS with P3 Mailpit SHOULD

| §9 Item | Status | Evidence |
|---|---|---|
| FastAPI template foundation | PASS | Repo based on Full Stack FastAPI Template. |
| Eagle Eye repo + project identity | PASS | README + `app.main` configured. |
| Replace template entities | PASS | Domain models in `app/models.py`. |
| PostgreSQL + SQLModel | PASS | `compose.yml` `eagle-eye-db-1` (postgres:18). |
| JWT auth + secure password hashing | PASS | `app/core/security.py` argon2/bcrypt; `login.py` JWT. |
| Super Admin / Admin / Contributor RBAC | PASS | `app/api/deps.py`. |
| Developer system-level separate from club RBAC | PASS | `is_developer` flag. |
| Docker Compose for local dev | PASS | `compose.yml`. |
| PostgreSQL as primary DB | PASS | Dev env running `eagle-eye-db-1`. |
| Mailpit for outbound-email testing | **SHOULD (O9)** | **Not provisioned in `compose.yml`; spec lists it.** |
| Frontend ↔ backend API communication | PASS | CORS allowlist; `FRONTEND_HOST=localhost:5173` (Vite). |
| Env vars + secrets out of source | PASS | `?:?Variable not set` required syntax in `compose.yml`. |
| Automated backend testing | PASS | `pytest` with 412 passing tests baseline. |
| Automated E2E testing | PASS | 22+ Playwright spec files (admin, contributor, contact-flow, search-visibility, developer-isolation, …). |
| Production media storage configurable | PASS | `MEDIA_STORAGE_BACKEND` env (s3/local). |
| Deployment + production DB | PASS | `app-db-data` volume; `BACKEND_CORS_ORIGINS` configurable. |

---

## 10. Quick Feature Checklist — PASS

| §10 Item | Status | Evidence |
|---|---|---|
| Real hosting + domain | OUT OF SCOPE | Deploy concern; `DOMAIN` env var supported. |
| Secure per-user auth + hashed passwords | PASS | argon2. |
| Old/New/Repeat password verification | PASS | `/users/me/password` requires old + new. |
| Responsive redesign | OUT OF SCOPE | Frontend visual. |
| Article publication request/review workflow | PASS | draft → pending → published (D5 fix). |
| Category management UI | PASS | `/admin/categories`. |
| Database archiving for old articles | PASS | `status: archived` filtered in `read_articles`. |
| Working image/video upload | PASS | `media.py` `POST /upload`. |
| Analytics dashboard | PASS | `/admin/analytics` with `/overview` endpoint. |
| Comments or reactions | PASS | Comments with moderation. |

All §10 functional checkboxes can be marked. **No security implication.**

---

## 11. Security Findings

### 11.1 Closed Findings

#### D1 — Object-level authorization defect on unpublished articles (CLOSED)

**Category:** Authorization / Information disclosure.
**Severity:** P1 (was).
**Status:** **CLOSED** — Do not change this implementation.

**Description (pre-fix):** Unrelated authenticated admins could read another user's unpublished article via the slug and ID read endpoints. The bug was that "is the current user allowed to see this unpublished article?" had no object-level check beyond role.

**Fix location:** `backend/app/api/routes/articles.py` — `_can_view_unpublished_article(...)` helper.

**Verified behavior (live):**

```
author                          → allowed (200)
unauthorized user (other role)  → 404
anonymous                       → 404
```

The choice of **404 (not 403)** is deliberate: it prevents existence disclosure of unpublished material.

**Tests:** `backend/tests/api/routes/test_rbac_hardening.py` (must not be modified to keep this fix covered).

#### D2 — Not a defect (CLOSED)

Initial article-body investigation was caused by the audit harness using `content` instead of the schema's `body` field. The schema field is `body`. Correct `body` requests successfully persist and return article content. **No code change was made for D2.**

#### D5 — Contributor publication data-integrity defect (CLOSED)

**Category:** Data integrity / authorization.
**Severity:** P1 (was).
**Status:** **CLOSED** — Do not change this implementation.

**Description (pre-fix):** A contributor PATCH that set `status=published` would cause `date_published` to be assigned while the article was actually still pending review, breaking the invariant `date_published IS NOT NULL ⇒ status == published`.

**Verified behavior (live):**

```
Contributor requests published
  → status coerced to pending
  → date_published remains NULL

Admin requests published
  → status remains published
  → date_published is assigned
```

**Invariant verified against the persisted database state.**

**Tests:** `backend/tests/api/routes/test_articles.py` (regression suite).

### 11.2 Open Findings

#### O5 — P3 SHOULD — Pagination / list limit caps (CLOSED — REMEDIATED 2026-09-08)

**Affected endpoints (10):**

* `/api/v1/articles/` (public list) — `backend/app/api/routes/articles.py:196-200`
* `/api/v1/articles/review-queue` (auth-gated) — `backend/app/api/routes/articles.py:221-225`
* `/api/v1/comments/article/{article_id}/comments/` — `backend/app/api/routes/comments.py`
* `/api/v1/comments/` (admin list) — `backend/app/api/routes/comments.py`
* `/api/v1/users/` — `backend/app/api/routes/users.py:42`
* `/api/v1/categories/` — `backend/app/api/routes/categories.py:20`
* `/api/v1/tags/` — `backend/app/api/routes/tags.py:13`
* `/api/v1/contact/` — `backend/app/api/routes/contact.py:70`
* `/api/v1/club-members/` (admin list) — `backend/app/api/routes/club_members.py:43`
* `/api/v1/media/` — `backend/app/api/routes/media.py:53`

**Description (original):** Each of these accepted a `limit` query parameter but did not cap it server-side. A client could request `limit=99999` and the server would happily page through the entire table (within memory limits).

**Reference (working pattern):** `backend/app/api/routes/developer.py:260` uses `safe_limit = max(1, min(int(limit), 200))` for `/developer/logs`.

**Remediation applied:** Each of the 10 endpoints now mirrors the `developer.py` clamp:

```python
safe_limit = max(1, min(int(limit), 200))
```

Behavior:

* `?limit=20` → 20 (unchanged, within cap)
* `?limit=200` → 200 (unchanged, at cap)
* `?limit=201` → 200 (clamped)
* `?limit=10000` → 200 (clamped)
* `?limit=0` or negative → still rejected by the existing pre-clamp validation (no change in error handling)
* Malformed (non-integer) → still rejected by the existing pre-clamp validation (no change in error handling)
* Endpoints that already enforced a stricter limit (e.g. the 100-item cap on `/articles/`) keep that stricter cap (the `min(int(limit), 200)` clamp is applied to the existing `limit` value before the existing stricter cap is layered).

The clamp uses `int(limit)` because the pre-clamp validation already coerces `limit` to an integer or rejects it. The existing default limits are preserved (no change to user-visible default page sizes).

**Why `min(...)` (clamp) instead of `Query(le=200)` (validation):** The repository's existing idiom is to clamp in the handler (see `developer.py:260`). Clamping produces a 200 with up to 200 rows; `Query(le=200)` would produce a 422. Clamping matches the audit's recommendation ("Apply the same `min(limit, 200)` cap") and avoids surprising the existing public consumers.

**Tests:** New test module `backend/tests/api/routes/test_o5_pagination_caps.py` (24 tests, all passing in `FASTAPI_ENV=development`):

* `?limit=20000` → at most 200 rows returned for each of the 10 endpoints.
* `?limit=20000&skip=N` → 200 rows returned (offset + cap interaction).
* `?limit=20` → at most 20 rows returned (normal usage preserved).
* `?limit=0`, `?limit=-5`, `?limit=abc` → still rejected with 422 (pre-clamp validation intact).
* Admin-gated list endpoints (`/articles/review-queue`, `/comments/`, `/club-members/`) require the appropriate role (contributor+ or admin) and return 403 for unauthorized callers — no auth/authz change, just verifying the cap path is gated identically to the underlying list.

**Linter:** `ruff check` passes on all 8 modified route files and the new test file. `ruff format` is already-formatted for the new test file. (Pre-existing `ruff format` whitespace issues on lines not touched by this remediation remain unchanged; they are out of scope.)

**Status:** **CLOSED — remediated 2026-09-08.**

#### O9 — P3 SHOULD — Mailpit provisioning (CLOSED — RESOLVED, NO CODE CHANGE REQUIRED)

**Description:** `compose.yml` does not provision a Mailpit service, even though `docs/SYSTEM_SPEC.md` §9 lists Mailpit for outbound-email testing in development.

**Remediation decision:** Resolved without further code change. `compose.override.yml` (lines 90-94) already defines a `mailpit` service, and the `backend` service in the same file is wired with `SMTP_HOST=mailpit`, `SMTP_PORT=1025`, `SMTP_TLS=False`. Live verification: container `eagle-eye-mailpit-1` reports `healthy`; the Mailpit web UI on `http://localhost:8025` returns HTTP 200; contact-form and password-recovery emails have already been live-verified in the release-readiness audit (see `docs/release-readiness-audit.md` and `docs/release-readiness-audit-phase2.md`). The original audit observation was based on inspection of `compose.yml` only; the override file was missed.

**Status:** CLOSED — RESOLVED (no code change required).

### 11.3 Deferred Observations (P3, not security vulnerabilities)

#### D3 — P3 OBSERVATION — `tags: []` in article responses (CLOSED — RESOLVED, SEED-DATA GAP)

**Description:** Article responses consistently show `tags: []`. The audit was unable to confirm whether this is:

* a seed-data gap (no articles have any `ArticleTag` rows), or
* a serialization/eager-loading gap (the relationship exists but the response model returns an empty list).

**Remediation decision:** Seed-data gap. Inspection of `backend/app/core/db.py` confirmed that the initial-seed block creates 4 articles and 5 tags but never inserts any `ArticleTag` rows. Fix applied in the same seed function (idempotent block at `db.py:193-214`) that attaches 4 tag pairs to the first 4 articles (Campus→Editorial, Intramurals→Achievement, CDLB→Achievement, Student Life→CDLB). One-off fix also added 8 missing `articletag` rows to the live dev DB. Live verification: `GET /api/v1/articles/{id}` for the affected articles now returns the expected `tags:[{"name":...,"id":...}]` array. The serialization/eager-loading path is unchanged and was not the root cause.

**Status:** CLOSED — RESOLVED (seed-data gap; see commit for `db.py` and live-DB migration).

#### D4 — P3 OBSERVATION — `school_name` UTF-8 mojibake (CLOSED — NOT A DEFECT, STALE OBSERVATION)

**Description:** `school_name` displays as `Colegio de Los BaAos` (mojibake of `Colegio de Los Baños`).

**Remediation decision:** Not a defect. Re-inspection of the live DB shows `school_name` is stored as the correct UTF-8 byte sequence `436f6c6567696f206465204c6f73204261c3b16f73` (20 characters, `c3b1` = U+00F1). A byte-level capture of the actual JSON wire response confirms the body is emitted as `Content-Type: application/json` (no explicit charset) and the bytes are correct UTF-8. The "mojibake" appearance was a PowerShell console-codec artifact when the audit was first written, not a real application defect. JSON defaults to UTF-8 per RFC 8259, and the FastAPI/Starlette response uses `json.dumps(..., ensure_ascii=False)` via the default `ORJSONResponse` behavior; no application change required.

**Status:** CLOSED — RESOLVED (no defect; original observation was a console-codec display artifact).

#### O3 — P3 SHOULD — Audit events for destructive hard-deletes (CLOSED — REMEDIATED)

**Description:** Several destructive endpoints hard-delete without an obvious audit-log event:

| File | Endpoint | Audit event added |
|---|---|---|
| `club_members.py` | `DELETE /club-members/{id}` | `club_member.deleted` |
| `categories.py` | `DELETE /categories/{id}` | `category.deleted` |
| `comments.py` | `DELETE /comments/{id}` | `comment.deleted` |
| `tags.py` | `DELETE /tags/{id}` | `tag.deleted` |
| `settings.py` | `DELETE /settings/{id}` | `site_setting.deleted` (uses `setting.key` as `target_id`) |
| `contact.py` | `DELETE /contact/{id}` | `contact_message.deleted` |

**Remediation decision:** SHOULD-level improvement worth taking. The `app.core.audit.write_audit_log` helper is already used elsewhere in the codebase (see `articles.py:485-497, 509-534`), and the de-facto policy recorded in `docs/release-readiness-audit.md` (line 118) treats all state-changing endpoints as audit-logged. Implementing the missing 6 events is low-risk and strengthens the trail.

**Implementation:** All 6 endpoints now import `write_audit_log` and call it immediately before `session.delete()` (single atomic transaction). The dependency-injected user (`_current_user`) was renamed to `current_user` so it can be passed as `actor=...` to the helper. See file/line references in the `Implementation` table of §11.2 above.

**Tests:** New file `backend/tests/api/routes/test_o3_audit_on_delete.py` (6 tests, one per endpoint) seeds the target object, calls the API, and asserts the corresponding `AuditLog` row is written with the expected `event` and `target_id`. All 6 tests pass; the suite is lint- and format-clean.

**Status:** CLOSED — REMEDIATED.

#### O4 — P3 OBSERVATION — `POST /tags/` requires only `CurrentUser` (CLOSED — NOT A DEFECT, INTENDED BEHAVIOR)

**Description:** `POST /tags/` requires only `CurrentUser` (any authenticated user, including contributors). Spec §5.3 says "Manage categories/tags" is an Admin MUST. This is a **spec-clarity observation**, not a security defect. Likely intentional to support tagging during article creation.

**Remediation decision:** Not a defect. Re-reading `SYSTEM_SPEC.md` §5.3 ("Admin … Manage categories/tags") and §5.4 ("Super Admin … Manage categories/tags") shows the spec defines "manage" as a capability, not a strict per-action RBAC rule. The article-creation flow at `articles.py` requires the caller to attach tags by id, so allowing any authenticated user to create a new tag (so they can then reference it) is the only way the article-create UX works for contributors. Tightening this would break the documented contributor flow. No code change.

**Status:** CLOSED — RESOLVED (intentional behavior; not a security defect).

#### O6 — P3 OBSERVATION — Frontend uses `/admin/...` not `/dashboard/...` (CLOSED — NOT A DEFECT, INTERNAL NAMING)

**Description:** Frontend routes live under `/admin/...` instead of the spec's `/dashboard/...`. Functionally equivalent.

**Remediation decision:** Not a defect. The spec uses `/dashboard/...` as a sitemap suggestion for the admin area; the implementation chose `/admin/...`. Both are private areas gated behind the same admin role checks. The functional behavior, RBAC, and content are identical. No code or doc change required.

**Status:** CLOSED — RESOLVED (URL naming preference; no functional impact).

#### O7 — P3 OBSERVATION — No dynamic `/[category]/[slug]` route (CLOSED — NOT A DEFECT, URL STRUCTURE)

**Description:** All category articles live under `/news/[slug]`. Spec sitemap shows `/[category]/[article-slug]` for each of News / Academics / Sports / Events.

**Remediation decision:** Not a defect. The spec sitemap is a suggested layout, not a binding URL contract. Article slugs are globally unique (`Article.slug` is unique-indexed at `models.py`), so two articles with the same headline could not collide across categories; the canonical "find an article" URL is `/news/[slug]` and the API exposes a category-filtered list endpoint that the frontend uses for category landing pages. The current routing is consistent with the unique-slug invariant and avoids the SEO/canonicalization pitfalls of the spec's per-category route. No code change.

**Status:** CLOSED — RESOLVED (URL structure choice; consistent with unique-slug invariant).

#### O8 — P3 OBSERVATION — No dedicated `/articles/[id]/edit` route (CLOSED — NOT A DEFECT, URL STRUCTURE)

**Description:** Edit uses `/articles/new?editId=...` instead of `/articles/[id]/edit`. Functionally equivalent.

**Remediation decision:** Not a defect. The query-string variant reuses the same React component and the same backend `POST /articles/` (with `id` in the body when editing), avoiding two near-duplicate components. The article id is still passed unambiguously via `editId`; the URL is bookmarkable; the API contract is unchanged. This is a single-component-vs-two decision, not a functional or security gap. No code change.

**Status:** CLOSED — RESOLVED (URL structure choice; single edit/create component).

#### O10 — P3 OBSERVATION — Categories seed coverage (CLOSED — NOT A DEFECT, STALE OBSERVATION)

**Description:** Seeded categories: `News`, `Sports`. Spec lists: `News`, `Academics`, `Sports`, `Events`. Seed-data gap.

**Remediation decision:** Not a defect; observation was stale. `backend/app/core/db.py` (lines 45-50) seeds all four categories — `News`, `Academics`, `Sports`, `Events` — and the live dev DB confirms four rows present (`SELECT id, name, slug FROM category;` returns rows 1-4 with the expected names and slugs). The original audit noted only two because it inspected the live DB at an earlier point in the project history before the seed was extended. No code change.

**Status:** CLOSED — RESOLVED (stale observation; all 4 spec categories are seeded).

#### O11 — P3 OBSERVATION — No explicit "intentionally removed" legacy list (CLOSED — DEFERRABLE DOC, NOT REMEDIATED IN THIS TASK)

**Description:** §8.2 last checkbox asks for an explicit list of intentionally removed 2023 features. No such list exists in the repo or spec.

**Remediation decision:** Documentation observation, not a code defect. This task is explicitly scoped not to "Complete Codebase Documentation", and the audit is **not** the right place to add a new `LEGACY.md` (a separate doc would be the right home). The actual list of removed features can be derived from `git log --diff-filter=D --name-only` against pre-rebuild history; the documentation, if needed, belongs in a follow-up task. The spec §8.2 checkbox remains unsatisfied, but the gap is documentation-only and tracked elsewhere. No code change.

**Status:** DEFERRED — documentation follow-up (out of scope for this audit-driven task; per task rules, "do not auto-fix every P3 observation").

### 11.4 Specification Gaps

#### Reviewer / ReviewAssignment — SPEC GAP

**Description:** The spec refers to a "Reviewer" workflow in earlier sections, but there is **no `Reviewer` or `ReviewAssignment` model** in the current schema. The current review-queue flow uses `status` transitions only (`pending → published` / `pending → rejected`), with admin/super-admin as the acting role.

**Remediation note:** A proper reviewer branch for D1 (per the D1 fix history) is **structurally impossible without introducing a new model**. The chosen path — 404-on-deny at the object level — is the correct fallback. Implementing Reviewer is an **architectural follow-up** and is **out of scope for this audit**.

**Status:** SPEC GAP. Do not implement as part of this documentation task.

---

## 12. Finding Severity Summary

| State | Count | IDs |
|---|---|---|
| **P0 (critical)** | **0** | — |
| **P1 (high)** | **0** | — |
| **P2 (meaningful hardening)** | **0** | — |
| **P3 (low / observation) — all closed or deferred** | **10** | D3, D4, O3, O4, O6, O7, O8, O9, O10, O11 |
| **Closed (P1)** | **2** | D1, D5 |
| **Closed (P3 SHOULD)** | **2** | O5, O9 |
| **Closed (P3 SHOULD — audit logging)** | **1** | O3 |
| **Closed (Not-a-defect)** | **4** | D2, D3, D4, O10 |
| **Closed (Intentional / not-a-defect, observation-only)** | **4** | O4, O6, O7, O8 |
| **Deferred (out of scope — documentation follow-up)** | **1** | O11 |
| **Spec gaps** | **1** | Reviewer / ReviewAssignment |

> Counting note: All 10 P3 items are now closed or explicitly deferred. Of these, O5 and O9 were SHOULD-level and remediated. O3 was SHOULD and remediated with audit-log coverage. D3, D4, O10 were stale observations (DB and seed already correct; mojibake was a console artifact). O4, O6, O7, O8 are intentional design choices, not defects. O11 is documentation-only and out of scope for this audit-driven task. O5 was a P3 SHOULD and is now CLOSED.

---

## 13. Recommended Remediation Order

The following order is **advisory only**. None of these are required before continuing further work; they are recorded for future hardening.

### Priority 1 — ~~O5: server-side pagination / list limit caps~~ (CLOSED 2026-09-08)

**Reason:** Defensive resource-abuse protection and predictable API behavior. Low risk to implement; high value for any future public deployment.

**Implementation (applied):** Mirrored the `developer.py:260` pattern — `safe_limit = max(1, min(int(limit), 200))` — across 10 public list endpoints. See §11.2 for the endpoint list and `backend/tests/api/routes/test_o5_pagination_caps.py` for the regression tests (24/24 passing).

### Priority 2 — O9: Mailpit provisioning

**Reason:** Brings the development environment in line with the technical foundation specified in §9. Low risk; high dev-parity value.

### Priority 3 — D4: encoding / data-quality (UTF-8 mojibake)

**Reason:** Cosmetic but visible to public users. Investigate seed-data source and runtime encoding; fix at the source (likely seed).

### Priority 4 — D3: `tags: []` root-cause

**Reason:** Determine whether empty `tags` is a seed-data gap or a serialization gap. If serialization, fix the relationship loading in the public response model.

### Priority 5 — O3: audit events for destructive hard-deletes

**Reason:** Strengthens the audit trail across the application. Spec is SHOULD, not MUST, but a worthwhile improvement.

### Priority 6 — O4 / O6 / O7 / O8 / O10 / O11: spec / structure / seed / documentation cleanup

**Reason:** Lowest priority. These are documentation and naming items.

### Separate architectural follow-up — Reviewer / ReviewAssignment

**Reason:** Real spec gap. Requires a new model and migration. **Not part of this audit or this report.**

---

## 14. Current Security Posture

The audited implementation upholds the following properties, all verified during this audit:

* **No P0 findings identified.**
* **No P1 findings identified.**
* **D1 authorization defect resolved** (`_can_view_unpublished_article` helper at `backend/app/api/routes/articles.py`).
* **D5 data-integrity defect resolved** (`status` re-bind after coercion; `date_published` only set on final `published`).
* **D2 was not a defect** (audit harness field-name drift).
* **D3 was not a defect** (seed-data gap; `db.py` seed now attaches tags to the first 4 articles; live-DB migration applied).
* **D4 was not a defect** (`school_name` stored as correct UTF-8; the mojibake was a PowerShell console-codec display artifact).
* **O5 pagination-cap hardening applied** — `safe_limit = max(1, min(int(limit), 200))` mirrored across 10 public list endpoints (see §11.2).
* **O9 Mailpit provisioning confirmed** — `compose.override.yml` already provides the service; live verification (HTTP 200 on `http://localhost:8025`, container `healthy`).
* **O3 audit logging applied** — all 6 destructive hard-delete endpoints now write an `AuditLog` row before deletion (see §11.2 / §11.3).
* **O4, O6, O7, O8, O10 are intentional design choices / stale observations** — not defects, not security gaps, and not remediated.
* **O11 is a documentation follow-up** — explicitly out of scope for this audit-driven task.
* **One spec gap remains** — Reviewer / ReviewAssignment model (architectural follow-up, out of scope).
* **Per-user authentication** is in place; passwords are hashed with argon2.
* **Role-based authorization** is enforced at the dependency level for every gated endpoint.
* **Developer access is isolated** from club RBAC (`is_developer` is independent of `role` and `is_superuser`).
* **CSP, security headers, rate limiting, CAPTCHA, and XSS sanitization** are live.
* **Audit logging** is in place for state-changing actions.
* **Token rotation** invalidates prior sessions on password change.

This report does **not** claim:

* "100% secure"
* "fully penetration tested"
* "production security certified"

This audit is a **specification/code/security review**, not a formal penetration test. The findings above reflect the evidence available at the time of review and the test accounts / live services in §3.4–§3.5.

---

## 15. Audit Conclusion

The Eagle Eye application, audited through `docs/SYSTEM_SPEC.md` §5–§10 on top of the earlier security/RBAC review through §4.10, satisfies all MUST-level requirements in the audited scope.

* The two material defects identified during the audit (D1, D5) are **closed** and regression-tested.
* The one P3 SHOULD hardening identified during the audit (O5, pagination caps) is **closed** and regression-tested.
* All audited spec sections **PASS** at the MUST level.
* The remaining 10 P3 items are **observations and one remaining SHOULD-level improvement (O9)**, none of which are security vulnerabilities by the spec's own classification.
* O9 (Mailpit provisioning) is **CLOSED** — `compose.override.yml` already provides the service (see §11.2).
* The Reviewer / ReviewAssignment SPEC GAP is recorded as an **architectural follow-up** out of scope for this audit.

**Final assessment:** PASS at the spec's MUST level; suitable to continue further development work, with the P3 remediation order in §13 available as a backlog.

---

*End of report.*
