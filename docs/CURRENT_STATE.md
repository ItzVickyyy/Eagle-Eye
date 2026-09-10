# Eagle Eye — Current State Document

> **Last updated:** 2026-09-08
> **Commit:** `792c43c1aa07c121a38c905171e8be915e06320d`
> **Branch:** `main` (3 ahead of origin, NOT pushed)

---

## 1. Project Identity

| Item | Value |
|---|---|
| Name | Eagle Eye |
| Organization | CDLB Media Club |
| Original project | Grade 12 Practical Research (2023) |
| Nature | Personal rebuild (NOT a capstone) |
| Repository | `ItzVickyyy/Eagle-Eye` |
| Working directory | `C:\Users\vocjo\Projects\Eagle-Eye` |

---

## 2. Technology Stack (Implemented)

### Frontend
- **Framework:** React 18 + TypeScript + Vite
- **Styling:** Tailwind CSS + shadcn/ui
- **Routing:** TanStack Router
- **State:** TanStack Query
- **Testing:** Playwright (e2e, 4-shard matrix)
- **Client generation:** @hey-api/openapi-ts
- **Package manager:** Bun 1.3.12

### Backend
- **Framework:** FastAPI (Python ≥3.14)
- **ORM:** SQLModel + SQLAlchemy
- **Database:** PostgreSQL 18
- **Auth:** JWT + argon2 password hashing
- **Rate limiting:** Redis-backed sliding window by default (`REDIS_URL` wired in compose.yml); fail-open to per-worker in-memory if Redis unavailable
- **Email:** Mailpit (dev) / SMTP (prod)
- **Storage:** Local (`uploads/`) or S3-compatible (boto3)
- **Testing:** Pytest (38 test files, `--fail-under=90`)
- **Package manager:** uv 0.9.26

### Infrastructure
- **Dev environment:** Docker Compose (5 base services + 3 dev-only)
- **Reverse proxy:** Traefik 3.6 (compose.override.yml dev, compose.deploy.yml prod)
- **Container security:** Vendored docker-socket-proxy (Tecnativa, SHA-pinned)
- **Rate limiter store:** Redis 7-alpine (compose.yml, REDIS_URL wired)
- **CI/CD:** GitHub Actions (13 workflows)

---

## 3. Docker Compose Services

### Base services (compose.yml)

| Service | Image | Exposed Ports | Network | Notes |
|---|---|---|---|---|
| `proxy` | traefik:3.6 | — (internal only) | `default` + `proxy` | Routes HTTP traffic |
| `socket-proxy` | tecnativa/docker-socket-proxy (SHA-pinned) | — | `proxy` only | Read-only Docker API proxy; all mutating ops blocked |
| `db` | postgres:18 | 5432 (dev override) | `default` | healthcheck: pg_isready |
| `redis` | redis:7-alpine | 6379 (dev override) | `default` | Rate-limit store; healthcheck: redis-cli ping |
| `backend` | Custom (backend/Dockerfile) | 8000 (internal; 8000 dev override) | `default` + `proxy` | Depends on db (healthy) + redis (healthy) |

### Dev-only services (compose.override.yml)

| Service | Image | Exposed Ports |
|---|---|---|
| `proxy` | traefik:3.6 | 80:80, 8090:8080 |
| `db` | — | 5432:5432 |
| `redis` | — | 6379:6379 |
| `adminer` | adminer (latest) | 8080:8080 + Traefik label (`adminer.localhost`) |
| `mailpit` | axllent/mailpit | 8025:8025 (UI), 1025:1025 (SMTP) |
| `playwright` | Custom (Dockerfile.playwright) | 9323:9323 |

### Deploy-only services (compose.deploy.yml)

| Additions | Details |
|---|---|
| `redis` | Gets `restart: always` + `app-redis-data` named volume |
| `proxy` | TLS via ACME (Let's Encrypt); ports 80+443; `traefik-certificates` volume |
| `backend` | Gets `restart: always` + `app-uploads-data` volume + HTTPS routing |
| `db` | Gets `restart: always` |

---

## 4. Domain Models (Implemented)

| Model | Table | Key Relationships |
|---|---|---|
| `User` | `user` | Auth, RBAC (super_admin/admin/contributor), `is_developer` flag |
| `Article` | `article` | FK→User (author), FK→Category, status workflow (draft→pending→published→archived) |
| `Category` | `category` | Has articles; seeded with News/Academics/Sports/Events |
| `Tag` | `tag` | Many-to-many with articles via `article_tag` |
| `Media` | `media` | FK→Article (nullable), file_url, uploaded_by |
| `Comment` | `comment` | FK→Article, moderation status (pending/approved/spam) |
| `ClubMember` | `club_member` | About Us CMS — name, position, department, photo |
| `ContactMessage` | `contact_message` | Public contact form submissions, new/read status |
| `SiteSetting` | `site_setting` | Key-value store for logo, social links, site name |
| `ApplicationAuditLog` | `application_audit_log` | Developer action audit trail |

---

## 5. API Endpoints (15 route modules)

| Module | Prefix | Key Endpoints |
|---|---|---|
| `login.py` | `/api/v1/login` | `/access-token`, `/test-token` |
| `users.py` | `/api/v1/users` | `/signup`, `/me`, `/{user_id}` |
| `articles.py` | `/api/v1/articles` | CRUD, review queue, slug lookup |
| `categories.py` | `/api/v1/categories` | CRUD |
| `tags.py` | `/api/v1/tags` | CRUD |
| `media.py` | `/api/v1/media` | Upload, list, delete |
| `comments.py` | `/api/v1/comments` | Create (feature-flagged), moderate, delete |
| `contact.py` | `/api/v1/contact` | Public submission, admin inbox |
| `password.py` | `/api/v1/password` | `/password-recovery/{email}`, `/reset-password/` |
| `developer.py` | `/api/v1/developer` | Feature flags, logs, diagnostics |
| `analytics.py` | `/api/v1/analytics` | Overview stats |
| `club_members.py` | `/api/v1/club-members` | CRUD |
| `settings.py` | `/api/v1/settings` | Site settings CRUD |
| `utils.py` | `/api/v1/utils` | Email test, health check |
| `internal.py` | `/api/v1/internal` | Dev-only utilities |

---

## 6. RBAC Roles

| Role | Description | Permissions |
|---|---|---|
| `super_admin` | Club adviser(s) | Full administration |
| `admin` | Club officers / editorial | Article management, review, publish |
| `contributor` | Club members / writers | Create/edit own drafts, submit for review |
| `guest` (unauthenticated) | Public visitors | Browse, search, read published content |
| `developer` (system-level) | Technical maintainer(s) | System tools, logs, feature flags (separate from club RBAC) |

---

## 7. Feature Flags (Runtime)

| Flag | Default | Effect |
|---|---|---|
| `dev_maintenance_mode` | `false` | Intercepts public traffic; allows admin/auth paths |
| `dev_public_comments_enabled` | `true` | Gates `POST /api/v1/comments/` |
| `dev_contact_form_enabled` | `true` | Gates `POST /api/v1/contact/` |
| `dev_allow_public_signup` | `true` | Gates `POST /api/v1/users/signup` |

---

## 8. CI Workflows (13 active)

### Active
| Workflow | Trigger | Purpose |
|---|---|---|
| `test-backend` | push/PR to main | Pytest with `--fail-under=90` + smokeshow |
| `test-docker-compose` | push/PR to main | Docker Compose integration test |
| `playwright` | push/PR to main | 4-shard Playwright e2e |
| `pre-commit` | push/PR to main | Linting/formatting |
| `deploy` | push to main | FastAPI Cloud deployment |
| `deploy-docker-compose` | push to main | Self-hosted Docker deployment |
| `detect-conflicts` | PR to main | Merge conflict detection |
| `guard-dependencies` | pull_request_target | Author gate for dependency changes |
| `smokeshow` | push/PR to main | Coverage HTML publishing |
| `zizmor` | push/PR to main | GitHub Actions security scanning |

---

## 9. Environment Variables (Key)

| Variable | Default | Source |
|---|---|---|
| `FASTAPI_ENV` | `development` | compose.yml |
| `FIRST_SUPERUSER` | `admin@eagleeye.dev` | compose.yml |
| `SECRET_KEY` | (generated) | `.env` (gitignored) |
| `FIRST_SUPERUSER_PASSWORD` | (generated) | `.env` (gitignored) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | `.env` (gitignored) |
| `CAPTCHA_ENABLED` | `False` (dev default) | `.env` |
| `VITE_API_URL` | (empty — uses same origin) | frontend/.env |
| `VITE_TURNSTILE_SITE_KEY` | (empty) | frontend/.env |

---

## 10. Known Gaps

| ID | Description | Classification |
|---|---|---|
| ~~S4~~ | ~~In-memory rate limiter only~~ — RETRACTED: Redis-backed sliding window IS implemented (`backend/app/core/rate_limit.py`) and wired by default (`REDIS_URL=redis://redis:6379/0` in compose.yml). Fail-open to in-memory only if Redis unavailable. | RETRACTED |
| ~~ReviewAssignment~~ | ~~Specified in SYSTEM_SPEC but not implemented as a model~~ — IMPLEMENTED (Implementation 19): ReviewAssignment model, API, migration, frontend UI, tests. | RESOLVED |

---

## 11. Key Source Files

| File | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI application factory, CSP headers, lifespan |
| `backend/app/api/deps.py` | Authentication/authorization dependencies |
| `backend/app/api/routes/review_assignments.py` | Review assignment CRUD endpoints |
| `backend/app/core/config.py` | Settings with pydantic-settings, startup validation |
| `backend/app/core/security.py` | JWT, password hashing, token revocation |
| `backend/app/core/captcha.py` | Cloudflare Turnstile verification |
| `backend/app/initial_data.py` | First-run Super Admin creation |
| `backend/scripts/entrypoint.sh` | Container entrypoint — auto-runs prestart |
| `backend/scripts/prestart.sh` | Alembic migrations + initial data |
| `backend/Dockerfile` | Multi-stage: Bun build → Python uv |
| `compose.yml` | Base compose (5 services, socket-proxy) |
| `compose.override.yml` | Dev overrides (exposed ports, debug) |
| `compose.deploy.yml` | Production deploy (Traefik HTTPS, ACME) |
| `frontend/src/client/sdk.gen.ts` | Generated API client (auto-generated) |
| `frontend/src/client/client/` | Legacy @hey-api client dir (still referenced) |
| `opencode.json` | opencode config (**tracked + committed, contains API key**) |

---

## 12. Git State

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `792c43c1aa07c121a38c905171e8be915e06320d` |
| Status | 3 ahead of origin, **NOT pushed** |
| Audit baseline 1 | `d32fa60` (stale vs HEAD) |
| Audit baseline 2 | `d967664` (stale vs HEAD) |

---

## 13. Email Pipeline

```
packages/react-email (workspace: "emails")
    ↓ bun run export
backend/app/email-templates/ ({{ project_name }}, {{ username }} placeholders)
    ↓ backend sends via SMTP
Mailpit (dev: localhost:8025) / SMTP server (prod)
```

---

## 14. Container Startup Chain

```
docker compose up backend
  → Dockerfile CMD: bash scripts/entrypoint.sh uv run fastapi run ...
    → entrypoint.sh: UNLESS SKIP_PRESTART=1, runs prestart.sh
      → prestart.sh: alembic upgrade head + python app/initial_data.py
    → exec "$@"  (PID 1: uv run fastapi run ...)
```
