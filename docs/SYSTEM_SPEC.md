# Eagle Eye — System Specification

> CDLB Media Club digital publication platform. This document describes the system as currently implemented and deployed.

---

## 1. Project Overview

Eagle Eye is the CDLB Media Club's centralized digital publication website. It allows club members to write, review, and publish school news articles, manage club members, handle media uploads, moderate comments and contact submissions, and administer users — all through a role-aware web interface backed by a secure REST API.

| Item | Value |
|---|---|
| **Organization** | CDLB Media Club |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS + shadcn/ui |
| **Backend** | Python (≥ 3.14) + FastAPI |
| **ORM** | SQLModel + SQLAlchemy |
| **Database** | PostgreSQL 18 |
| **Auth** | JWT (argon2id password hashing) |
| **Rate limiting** | Redis 7 (sliding-window Lua); fail-open to in-memory |
| **Package managers** | uv 0.9.26 (backend), Bun 1.3.12 (frontend) |
| **Dev environment** | Docker Compose |
| **API prefix** | `/api/v1` |

---

## 2. Architecture

### 2.1 Runtime Services

Five services run in all environments (defined in `compose.yml`):

| Service | Image / Notes |
|---|---|
| **proxy** | Traefik 3.6; TLS termination, routing |
| **socket-proxy** | Tecnativa docker-socket-proxy (SHA-pinned); restricts Docker socket access |
| **db** | PostgreSQL 18 |
| **redis** | Redis 7-alpine |
| **backend** | FastAPI application |

Three additional services run in development only (`compose.override.yml`):

| Service | Notes |
|---|---|
| **adminer** | Database browser (dev only) |
| **mailpit** | SMTP sandbox for outbound-email testing (dev only) |
| **frontend-dev** | Vite dev server with HMR (dev only) |

Production overrides (`compose.deploy.yml`) add `restart: always`, Let's Encrypt HTTPS, and a named Docker volume (`app-uploads-data`) mounted at `/app/backend/uploads` for persistent media storage.

### 2.2 Request Flow

```
Browser → Traefik (proxy) → FastAPI backend
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
               PostgreSQL 18     Redis 7         uploads/
               (application      (rate            (media
                  data)          limiting)        storage)
```

The React SPA is served as static files from `FRONTEND_DIR = Path(__file__).parent / "frontend"` inside the backend container. FastAPI handles a SPA catch-all fallback for non-API, non-static paths.

### 2.3 Frontend Architecture

| Concern | Library / Tool |
|---|---|
| Framework | React 18 |
| Language | TypeScript |
| Bundler | Vite |
| Styling | Tailwind CSS + shadcn/ui |
| Routing | TanStack Router |
| Server state | TanStack Query |
| API client | @hey-api/openapi-ts (generated from OpenAPI schema) |
| E2E testing | Playwright |

### 2.4 Backend Architecture

| Concern | Library / Tool |
|---|---|
| Framework | FastAPI |
| ORM | SQLModel + SQLAlchemy |
| DB driver | psycopg (v3); `DATABASE_URL` validator rewrites `postgres://` / `postgresql://` → `postgresql+psycopg://` |
| Migrations | Alembic |
| Password hashing | argon2-cffi |
| Email | SMTP (Mailpit in dev; real SMTP in prod) |
| Error tracking | Sentry SDK (enabled in non-development environments when `SENTRY_DSN` is set) |
| CAPTCHA | Cloudflare Turnstile (`backend/app/core/captcha.py`) |

---

## 3. Authentication & Authorization

### 3.1 Authentication Flow

1. Client sends credentials to `POST /api/v1/login/access-token` (OAuth2 password form).
2. `authenticate()` in `crud.py` verifies the password with argon2. When the user does not exist, `verify_password` is called against `DUMMY_HASH` to prevent timing-based user enumeration.
3. On success, a JWT is issued with claims `sub` (user ID), `exp`, `jti` (unique token ID), and `tv` (token version, copied from `User.token_version`).
4. Default expiry: `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 8` (8 days).
5. The token is validated on every protected request by `_enforce_token_not_revoked` in `deps.py`, which checks both the `tv` claim against `User.token_version` and the `jti` against the `token_revocations` table. Both failure paths return the same 401 to prevent enumeration.

### 3.2 Token Revocation

Implemented in `backend/app/core/token_store.py`:

| Function | Behavior |
|---|---|
| `revoke_token(jti)` | Idempotent insert into `token_revocations` table |
| `bump_token_version(user)` | Increments `User.token_version`; invalidates all existing sessions for that user |
| `is_token_revoked(jti)` | Checks `TokenRevocation` table |
| `prune_revocations()` | Deletes expired rows; called at startup |

`POST /api/v1/login/logout` revokes the current `jti` (single-session logout).  
`bump_token_version` is used for bulk invalidation (e.g., password change, role change).

### 3.3 RBAC

#### Club / content roles (`UserRole` enum)

| Role | `UserRole` value | Permissions |
|---|---|---|
| **Super Admin** | `super_admin` | Full club and content administration; user/role management, club members, categories, tags, site settings, analytics, media |
| **Admin** | `admin` | Article management and editorial workflow; upload media; approve/reject/publish; manage categories and tags |
| **Contributor** | `contributor` | Create and edit own drafts; submit for review; cannot publish directly |
| **Guest / Reader** | *(unauthenticated)* | Browse published content, search, contact form, comments (when enabled) |

#### System-level access

| Field | Type | Meaning |
|---|---|---|
| `is_superuser` | `bool` | Full superuser access (separate from `UserRole`) |
| `is_developer` | `bool` | Access to developer/system tools; independent from club roles |

`is_developer` is a system-level boolean, not a position in the club RBAC hierarchy. A developer session does not automatically inherit club/content permissions.

#### FastAPI dependency aliases (from `deps.py`)

| Alias | Requirement |
|---|---|
| `CurrentUser` | Any authenticated active user |
| `AdminUser` | `role in (admin, super_admin)` or `is_superuser` |
| `SuperAdminUser` | `role == super_admin` or `is_superuser` |
| `DeveloperUser` | `is_developer == True` |

All authorization is enforced by the backend. Frontend route guards are a UX complement, not a security boundary.

### 3.4 CAPTCHA

Cloudflare Turnstile is applied to public-submission endpoints. Controlled by `CAPTCHA_ENABLED` (deploy-time setting):

- `False` (dev/test default): verification skipped.
- `True`: `backend/app/core/captcha.py` verifies the token via Cloudflare's `siteverify` endpoint; fails closed (403) on missing/invalid/transport-error tokens.

Endpoints protected: `POST /api/v1/users/signup`, `POST /api/v1/password-recovery/{email}`, `POST /api/v1/reset-password`, `POST /api/v1/contact/`.

When `CAPTCHA_ENABLED=true`, the settings validator `_validate_captcha_configuration` requires `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`, and the frontend `VITE_TURNSTILE_SITE_KEY` to be set; it refuses to start the production process if any are missing. Under `FASTAPI_ENV=development` the same condition surfaces as a warning only.

---

## 4. Security

### 4.1 HTTP Security Headers

Set in `backend/app/main.py` on every response:

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' https://challenges.cloudflare.com; frame-src 'self' https://challenges.cloudflare.com; connect-src 'self' https://challenges.cloudflare.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Cross-Origin-Resource-Policy` | `same-origin` |
| `X-Content-Type-Options` | `nosniff` |

### 4.2 CORS

`allow_origins=[settings.FRONTEND_HOST]`. Only the configured frontend origin is allowed.

### 4.3 Rate Limiting

Implemented in `backend/app/core/rate_limit.py`. Uses a Redis sliding-window Lua script (`_SLIDING_WINDOW_SCRIPT`). Fails open to an in-memory fallback when Redis is unavailable.

`_resolve_client_ip` respects `trusted_proxies`; `X-Forwarded-For` is only trusted when the direct peer is a configured trusted proxy.

Active rate limiters:

| Limiter | Applied to |
|---|---|
| `login_rate_limiter` | `POST /api/v1/login/access-token` |
| `password_recovery_rate_limiter` | `POST /api/v1/password-recovery/{email}` |
| `password_reset_rate_limiter` | `POST /api/v1/reset-password` |
| `signup_rate_limiter` | `POST /api/v1/users/signup` |
| `comment_rate_limiter` | `POST /api/v1/comments/` |
| `contact_rate_limiter` | `POST /api/v1/contact/` |
| `password_change_rate_limiter` | `PATCH /api/v1/users/me/password` |

### 4.4 Input Sanitization

Rich-text article body content is sanitized server-side (XSS prevention). Database access goes through SQLModel/SQLAlchemy ORM (SQL injection prevention).

---

## 5. Feature Flags & Maintenance Mode

Feature flags are stored in the `site_setting` table and read at request time. Managed through the Developer dashboard (`PATCH /api/v1/developer/feature-flags`). The authoritative source is always the database row; flags cannot be overridden via query parameters.

| Flag key | Default | Effect when disabled |
|---|---|---|
| `dev_maintenance_mode` | `false` | `MaintenanceModeMiddleware` blocks public traffic with 503 |
| `dev_public_comments_enabled` | `true` | `POST /api/v1/comments/` returns 403 |
| `dev_contact_form_enabled` | `true` | `POST /api/v1/contact/` returns 403 |
| `dev_allow_public_signup` | `true` | `POST /api/v1/users/signup` returns 403 |

`MaintenanceModeMiddleware` (from `app.core.flags`) always allows the following paths even when maintenance mode is active:

- `/api/v1/login/`, `/api/v1/password-recovery/`, `/api/v1/reset-password/`
- `/api/v1/developer/`, `/api/v1/utils/`, `/api/v1/settings/`
- `/api/v1/openapi.json`, `/docs`, `/redoc`
- `/uploads/`, `/assets/`, `/favicon.ico`, `/`

---

## 6. Data Models

### 6.1 Enumerations

| Enum | Values |
|---|---|
| `UserRole` | `super_admin`, `admin`, `contributor` |
| `ArticleStatus` | `draft`, `pending`, `published`, `archived` |
| `CommentStatus` | `pending`, `approved`, `spam` |
| `ContactMessageStatus` | `new`, `read` |

### 6.2 Core Tables

#### `user`

| Field | Type / Notes |
|---|---|
| `id` | UUID, PK |
| `email` | str, unique index |
| `hashed_password` | str |
| `full_name` | str, optional |
| `is_active` | bool (default `true`) |
| `is_superuser` | bool (default `false`) |
| `is_developer` | bool (default `false`) |
| `role` | `UserRole` enum, optional |
| `department` | str, optional |
| `position_title` | str, optional |
| `token_version` | int (bulk session invalidation) |

#### `article`

| Field | Type / Notes |
|---|---|
| `id` | UUID, PK |
| `title` | str |
| `slug` | str, unique |
| `body` | str (rich text) |
| `status` | `ArticleStatus` enum |
| `author_id` | UUID, FK → user |
| `category_id` | int, FK → category (optional) |
| `cover_image_id` | int, FK → media (optional) |
| `views_count` | int (default 0) |
| `published_at` | datetime, optional |
| GIN index on `body` for full-text search |

#### `category`

| Field | Type / Notes |
|---|---|
| `id` | int, PK |
| `name` | str, unique |
| `slug` | str, unique |
| `description` | str, optional |

#### `tag`

| Field | Type / Notes |
|---|---|
| `id` | int, PK |
| `name` | str, unique |

#### `article_tag` (join table)

| Field | Type |
|---|---|
| `article_id` | UUID, FK → article |
| `tag_id` | int, FK → tag |

#### `media`

| Field | Type / Notes |
|---|---|
| `id` | int, PK |
| `filename` | str |
| `file_url` | str |
| `mime_type` | str |
| `uploaded_by_id` | UUID, FK → user |
| `article_id` | UUID, FK → article (optional) |

#### `comment`

| Field | Type / Notes |
|---|---|
| `id` | int, PK |
| `article_id` | UUID, FK → article |
| `guest_name` | str |
| `guest_email` | str, optional |
| `body` | str |
| `status` | `CommentStatus` enum (default `pending`) |

#### `contact_message`

| Field | Type / Notes |
|---|---|
| `id` | int, PK |
| `name` | str |
| `email` | str |
| `message` | str |
| `status` | `ContactMessageStatus` enum (default `new`) |

#### `club_member`

| Field | Type / Notes |
|---|---|
| `id` | int, PK |
| `first_name` | str |
| `last_name` | str |
| `position` | str, optional |
| `position_title` | str, optional |
| `department` | str, optional |
| `photo_url` | str, optional |
| `is_officer` | bool (default `false`) |
| `is_active` | bool (default `true`) |
| `sort_order` | int (default 0) |

#### `site_setting`

| Field | Type / Notes |
|---|---|
| `key` | str, PK |
| `value` | str, optional |

Used for CMS settings and all feature flags (`dev_*` keys).

#### `token_revocation`

| Field | Type / Notes |
|---|---|
| `jti` | str, PK |
| `expires_at` | datetime |

#### `audit_log`

| Field | Type / Notes |
|---|---|
| `id` | UUID, PK |
| `event` | str |
| `component` | str |
| `severity` | str (default `INFO`) |
| `actor_email` | str, optional |
| `target_type` | str, optional |
| `target_id` | str, optional |
| `success` | bool |
| `message` | str, optional |
| `created_at` | datetime |

---

## 7. API Reference

All routes are prefixed with `/api/v1`. The OpenAPI schema is served at `/api/v1/openapi.json`.

### 7.1 Authentication (`/login`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/login/access-token` | Public (rate-limited) | Exchange credentials for JWT |
| `POST` | `/login/logout` | `CurrentUser` | Revoke current session token (jti) |
| `POST` | `/password-recovery/{email}` | Public (rate-limited, CAPTCHA) | Send password-reset email |
| `POST` | `/reset-password` | Public (rate-limited, CAPTCHA) | Reset password via token |
| `GET` | `/login/test-token` | `CurrentUser` | Verify and return current user |

### 7.2 Users (`/users`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/users/` | `is_superuser` | List all users |
| `POST` | `/users/` | `is_superuser` | Create user (admin flow) |
| `POST` | `/users/signup` | Public (rate-limited, CAPTCHA, flag-gated) | Public self-registration |
| `GET` | `/users/me` | `CurrentUser` | Get own profile |
| `PATCH` | `/users/me` | `CurrentUser` | Update own profile |
| `DELETE` | `/users/me` | `CurrentUser` | Delete own account |
| `PATCH` | `/users/me/password` | `CurrentUser` (rate-limited) | Change own password |
| `GET` | `/users/{user_id}` | `CurrentUser` | Get user by ID |
| `PATCH` | `/users/{user_id}` | `is_superuser` | Update user (admin) |
| `DELETE` | `/users/{user_id}` | `is_superuser` | Delete user (admin) |

### 7.3 Articles (`/articles`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/articles/` | Public | List published articles (paginated, filterable by category/tag/status) |
| `POST` | `/articles/` | `CurrentUser` | Create article (starts as `draft`) |
| `GET` | `/articles/{id_or_slug}` | Public / `CurrentUser` | Get article detail; increments `views_count` for published |
| `PATCH` | `/articles/{id}` | Author / `AdminUser` | Update article |
| `DELETE` | `/articles/{id}` | Author / `AdminUser` | Delete article |

Article status lifecycle: `draft` → `pending` → `published` → `archived`. Contributors cannot set status to `published` directly; that requires Admin or Super Admin.  
Full-text search via PostgreSQL GIN index on `body`.

### 7.4 Categories (`/categories`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/categories/` | Public | List all categories |
| `GET` | `/categories/{id_or_slug}` | Public | Get category by ID or slug |
| `POST` | `/categories/` | `AdminUser` | Create category |
| `PATCH` | `/categories/{id}` | `AdminUser` | Update category |
| `DELETE` | `/categories/{id}` | `AdminUser` | Delete category |

### 7.5 Tags (`/tags`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/tags/` | Public | List all tags (alphabetical) |
| `POST` | `/tags/` | `CurrentUser` | Create tag (idempotent by name, case-insensitive) |
| `DELETE` | `/tags/{id}` | `AdminUser` | Delete tag |

### 7.6 Comments (`/comments`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/comments/article/{article_id}` | Public | List approved comments for an article |
| `GET` | `/comments/` | `AdminUser` | List all comments (moderation view) |
| `POST` | `/comments/` | Public (rate-limited, flag-gated) | Submit comment (starts as `pending`) |
| `PATCH` | `/comments/{id}` | `AdminUser` | Update comment status (approve/spam/etc.) |
| `DELETE` | `/comments/{id}` | `AdminUser` | Delete comment |

Comments require moderation; new submissions are `pending` and not publicly visible until approved.

### 7.7 Media (`/media`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/media/` | `CurrentUser` | List uploaded media |
| `POST` | `/media/upload` | `AdminUser` | Upload media file |
| `DELETE` | `/media/{id}` | `AdminUser` | Delete media |

Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `video/mp4`, `video/webm`.

Storage: local filesystem (`uploads/`, configured as `UPLOAD_DIR = Path(__file__).parent.parent / settings.MEDIA_STORAGE_LOCAL_DIR`) or S3-compatible (boto3), controlled by `MEDIA_STORAGE_BACKEND`. In production, the `app-uploads-data` Docker volume is mounted at `/app/backend/uploads`.

### 7.8 Analytics (`/analytics`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/analytics/overview` | `AdminUser` | Aggregated stats: total/published/pending/draft articles, `total_views`, `total_users`, `total_comments`, `top_articles` |

### 7.9 Contact (`/contact`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/contact/` | Public (CAPTCHA, rate-limited, flag-gated) | Submit contact message |
| `GET` | `/contact/` | `AdminUser` | List contact messages |
| `PATCH` | `/contact/{id}` | `AdminUser` | Update message status |

Optional SMTP notification email sent to admins on new submission.

### 7.10 Club Members (`/club-members`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/club-members/` | Public | List active members (officers first, then by sort order and last name) |
| `GET` | `/club-members/all` | `AdminUser` | List all members including inactive (paginated, max 200) |
| `POST` | `/club-members/` | `SuperAdminUser` | Create club member |
| `PATCH` | `/club-members/{id}` | `SuperAdminUser` | Update club member |
| `DELETE` | `/club-members/{id}` | `SuperAdminUser` | Delete club member |

### 7.11 Site Settings (`/settings`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/settings/` | Public | List all site settings |
| `GET` | `/settings/{key}` | Public | Get setting by key |
| `POST` | `/settings/` | `SuperAdminUser` | Set or update a setting (upsert by key) |
| `DELETE` | `/settings/{key}` | `SuperAdminUser` | Delete a setting |

### 7.12 Developer (`/developer`)

Requires `is_developer == True`. All endpoints under this prefix are accessible during maintenance mode.

| Method | Path | Description |
|---|---|---|
| `GET` | `/developer/health` | System health: DB connectivity, latency, environment, Python/FastAPI version, platform |
| `GET` | `/developer/diagnostics` | Entity counts for all major tables, DB engine name, server time |
| `GET` | `/developer/feature-flags` | Read current feature flag values |
| `PATCH` | `/developer/feature-flags` | Update feature flags; emits `developer.feature_flags_updated` audit event |
| `GET` | `/developer/logs` | Paginated audit log (filterable by event, component, target_type, severity, success; max 200 per page; newest-first; `has_more` indicator) |

### 7.13 Utils (`/utils`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/utils/test-email/` | `is_superuser` | Send a test email |
| `GET` | `/utils/health-check/` | Public | Returns `true` (liveness probe) |

### 7.14 Private (`/private`) — Development Only

Mounted only when `settings.FASTAPI_ENV == "development"`. No authentication required.

| Method | Path | Description |
|---|---|---|
| `POST` | `/private/users/` | Create a user without authentication (test seeding) |

---

## 8. Frontend Routes

Routes are defined with TanStack Router under `frontend/src/routes/`.

### 8.1 Public Routes (layout: `_public`)

| Path | Page |
|---|---|
| `/` | Home (latest articles, category previews) |
| `/about-us` | About Us (dynamic club member list) |
| `/contact-us` | Contact form |
| `/search` | Full-text search results |
| `/news/` | Article listing |
| `/news/$slug` | Article detail |

### 8.2 Auth Routes

| Path | Page |
|---|---|
| `/login` | Login |
| `/signup` | Public registration |
| `/recover-password` | Password recovery |
| `/reset-password` | Password reset (token from email) |

### 8.3 Admin Routes (layout: `admin`, requires authentication)

| Path | Page |
|---|---|
| `/admin/` | Dashboard overview |
| `/admin/articles` | Article list |
| `/admin/articles/new` | Create article |
| `/admin/articles/$id/edit` | Edit article |
| `/admin/categories` | Category management |
| `/admin/comments` | Comment moderation |
| `/admin/contact` | Contact message inbox |
| `/admin/developer` | Developer tools (requires `is_developer`) |
| `/admin/members` | Club member management |
| `/admin/review-queue` | Pending article review |
| `/admin/settings` | Account/profile settings |
| `/admin/site-settings` | Site settings (Super Admin) |
| `/admin/users` | User management (Super Admin) |
| `/admin/analytics` | Analytics overview |

---

## 9. Email

Settings: `SMTP_TLS`, `SMTP_SSL`, `SMTP_PORT`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAILS_FROM_EMAIL`, `EMAILS_FROM_NAME`.

In development, Mailpit runs as a local SMTP sandbox. In production, a real SMTP server is configured via environment variables.

Outbound email is used for: password recovery, password reset confirmation, contact form admin notification, and test emails (`/utils/test-email/`).

---

## 10. CI/CD

13 GitHub Actions workflows are active in `.github/workflows/`. These cover backend linting, type checking, and testing; frontend linting and type checking; Playwright E2E tests; Docker image builds; and deployment automation.

---

## 11. Audit Logging

`write_audit_log()` in `backend/app/core/audit.py` writes to the `audit_log` table. Fields: `event`, `component`, `severity`, `actor_email`, `target_type`, `target_id`, `success`, `message`.

Audited operations include: user deletion, password changes, role changes, tag deletion, club member deletion, site setting deletion, feature flag updates, contact message updates, and maintenance-mode-blocked requests (`system.maintenance_block`).

Developer audit logs are exposed via `GET /api/v1/developer/logs`.

---

## 12. Key Environment Variables

| Variable | Purpose |
|---|---|
| `FASTAPI_ENV` | `development` vs `production`; controls dev-only routes, Sentry, CAPTCHA warnings |
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime (default: `34560`, i.e. 8 days) |
| `FRONTEND_HOST` | Allowed CORS origin |
| `MEDIA_STORAGE_BACKEND` | `local` or `s3` |
| `MEDIA_STORAGE_LOCAL_DIR` | Subdirectory under backend root for local uploads |
| `SMTP_*`, `EMAILS_FROM_*` | Email configuration |
| `CAPTCHA_ENABLED` | Enables Cloudflare Turnstile verification |
| `TURNSTILE_SITE_KEY` | Cloudflare Turnstile site key |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile secret key |
| `SENTRY_DSN` | Sentry error tracking DSN |
| `REDIS_URL` | Redis connection string for rate limiting |
| `TRUSTED_PROXIES` | Comma-separated trusted proxy IPs for `X-Forwarded-For` |
