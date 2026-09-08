# Eagle Eye — Definition of Done

> Validation checklist for the documentation knowledge base and the codebase itself.
> Covers all 49 required coverage areas from the archaeology mission briefing.
> Each item is **CONFIRMED FACT** verified against commit `792c43c`.

---

## A. Documentation Deliverables

| # | Deliverable | Status | Location |
|---|---|---|---|
| A1 | Master index (`docs/README.md`) | COMPLETE | `docs/README.md` |
| A2 | Current-state document | COMPLETE | `docs/CURRENT_STATE.md` |
| A3 | Master matrices (feature/file/dependency/API/DB/security/env/Docker) | COMPLETE | `docs/MASTER_MATRICES.md` |
| A4 | Architecture diagrams (Mermaid) | COMPLETE | `docs/ARCHITECTURE_DIAGRAMS.md` |
| A5 | Definition-of-done checklist | COMPLETE | **This file** |
| A6 | Existing docs verified & cross-referenced | COMPLETE | All 9 `.md` files in `docs/` + root/backend/frontend/scripts READMEs |

---

## B. Codebase Coverage (49 Required Areas)

### B1. Architecture & Stack

| # | Area | Evidence | Status |
|---|---|---|---|
| 1 | Backend framework | FastAPI ≥0.141.1, Python ≥3.14, `pyproject.toml` | CONFIRMED |
| 2 | Frontend framework | React 18 + TypeScript + Vite, `package.json` | CONFIRMED |
| 3 | ORM/DB | SQLModel + SQLAlchemy, PostgreSQL 18, `pyproject.toml` | CONFIRMED |
| 4 | Auth system | JWT + argon2-cffi, `backend/app/core/security.py` | CONFIRMED |
| 5 | Frontend state/data | TanStack Query + TanStack Router, `package.json` | CONFIRMED |
| 6 | Testing | Pytest 38 files (`--fail-under=90`), Playwright 4-shard | CONFIRMED |
| 7 | Build tools | Vite (frontend), uv (backend), `compose.yml` | CONFIRMED |

### B2. Models & Data

| # | Area | Evidence | Status |
|---|---|---|---|
| 8 | Domain models (10) | User, Article, Category, Tag, Media, Comment, ClubMember, ContactMessage, SiteSetting, ApplicationAuditLog | CONFIRMED |
| 9 | Migrations (13) | `backend/app/alembic/versions/` (0001–0013) | CONFIRMED |
| 10 | Seeding logic | `backend/app/initial_data.py` (Super Admin creation) | CONFIRMED |
| 11 | Feature flags (4) | `dev_maintenance_mode`, `dev_public_comments_enabled`, `dev_contact_form_enabled`, `dev_allow_public_signup` | CONFIRMED |

### B3. API

| # | Area | Evidence | Status |
|---|---|---|---|
| 12 | Route modules (15) | `backend/app/api/routes/` — login, users, articles, categories, tags, media, comments, contact, password, developer, analytics, club_members, settings, utils, internal | CONFIRMED |
| 13 | Auth flow | `/login/access-token`, `/login/test-token`, `/users/signup` | CONFIRMED |
| 14 | Rate limiting | 7 endpoints rate-limited; Redis-backed sliding window by default, fail-open to in-memory | CONFIRMED |
| 15 | RBAC enforcement | `deps.py:115-134` (except L124 unreachable `return None`) | CONFIRMED |

### B4. Frontend

| # | Area | Evidence | Status |
|---|---|---|---|
| 16 | Generated client | `sdk.gen.ts`/`types.gen.ts`/`client.gen.ts` (@hey-api) | CONFIRMED |
| 17 | Legacy client coexistence | `frontend/src/client/client/` (7 files) + `core/` (8 files) — legacy dirs still imported by `sdk.gen.ts` | CONFIRMED |
| 18 | UI library | shadcn/ui + Tailwind CSS | CONFIRMED |
| 19 | Asset inventory | All visual assets marked UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE | CONFIRMED |

### B5. Infrastructure

| # | Area | Evidence | Status |
|---|---|---|---|
| 20 | Compose base (5 svc) | proxy, socket-proxy, db, redis, backend — `compose.yml` | CONFIRMED |
| 21 | Dev overrides | adminer, mailpit, playwright added; ports exposed; `compose.override.yml` | CONFIRMED |
| 22 | Deploy overrides | Traefik HTTPS ACME, `app-uploads-data`, `app-redis-data` volumes, `restart: always` — `compose.deploy.yml` | CONFIRMED |
| 23 | Reverse proxy | Traefik 3.6 (HTTP→HTTPS redirect, ACME TLS, Docker provider) | CONFIRMED |
| 24 | Socket security | Vendored `docker-socket-proxy` (Tecnativa SHA-pinned); mutating ops blocked | CONFIRMED |
| 25 | Container startup chain | `entrypoint.sh` → `prestart.sh` (auto) → `exec "$@"` (PID 1) | CONFIRMED |
| 26 | Dockerfile topology | Multi-stage: Bun build → Python uv; `backend/Dockerfile` | CONFIRMED |
| 27 | Mailpit dev email | `8025:8025` (UI) + `1025:1025` (SMTP) — `compose.override.yml` | CONFIRMED |
| 28 | Redis store | `redis:7-alpine` in base `compose.yml`; `REDIS_URL` wired to backend | CONFIRMED |

### B6. CI/CD

| # | Area | Evidence | Status |
|---|---|---|---|
| 29 | Workflows (13 active) | test-backend, test-docker-compose, playwright (4-shard), pre-commit, deploy, deploy-docker-compose, detect-conflicts, guard-dependencies, smokeshow, zizmor (+ 3 inactive) | CONFIRMED |
| 30 | Template-inherited inactive | issue-manager, add-to-project, bump-pre-commit-hooks (all `if: github.repository_owner == 'fastapi'`) | CONFIRMED |
| 31 | Coverage threshold | `--fail-under=90` + smokeshow 90 | CONFIRMED |
| 32 | deploy.yml target | FastAPI Cloud (`uv run fastapi deploy`) | CONFIRMED |
| 33 | deploy-docker-compose target | Self-hosted runner (rsync + SSH + Docker) | CONFIRMED |

### B7. Security

| # | Area | Evidence | Status |
|---|---|---|---|
| 34 | CSP headers | `main.py` middleware | CONFIRMED |
| 35 | CAPTCHA (Turnstile) | `captcha.py` + env validation | CONFIRMED |
| 36 | Password hashing | argon2-cffi (via passlib) | CONFIRMED |
| 37 | Token revocation | `security.py` revocation check | CONFIRMED |
| 38 | Secrets management | `.env` gitignored, `.env.example` templates, `guard-secrets.sh` | CONFIRMED |
| 39 | Audit logging | `ApplicationAuditLog` model + endpoint | CONFIRMED |

### B8. Documentation Quality

| # | Area | Evidence | Status |
|---|---|---|---|
| 40 | Source-of-truth hierarchy | 15-level hierarchy in `docs/README.md` | CONFIRMED |
| 41 | Fact labels | 6 labels (CONFIRMED/STRONG INFERENCE/UNKNOWN/HISTORICAL/SPEC INTENT/IMPL REALITY) | CONFIRMED |
| 42 | Stale baseline cross-ref | 2 audit docs cross-referenced against HEAD | CONFIRMED |
| 43 | Link integrity | All 11 index links verified in `docs/README.md`: 4 in `docs/` + 7 external (root/backend/frontend/scripts READMEs + deployment docs) | CONFIRMED |

### B9. Gaps Documented (Not Fixed)

| # | Area | Evidence | Status |
|---|---|---|---|
| 44 | `boto3` presence (not absence) | `pyproject.toml:21`, `uv.lock:286` — S6 briefing claim corrected | CONFIRMED CORRECTED |
| 45 | Legacy client coexistence | 17 files in `frontend/src/client/` — legacy `client/client/` + `core/` still imported | CONFIRMED DOCUMENTED |
| 46 | `return None` unreachable | `deps.py:124` — dead code inside try/except that always returns | CONFIRMED DOCUMENTED |
| 47 | `test-local.sh` legacy `docker-compose` | Lines 6/13/14/15/16 use deprecated binary | CONFIRMED DOCUMENTED |
| 48 | `opencode.json` tracked + committed API key | Git-tracked with API key; undocumented in `.md` files | CONFIRMED DOCUMENTED |
| 49 | ReviewAssignment spec gap | SYSTEM_SPEC mentions but no model implemented | CONFIRMED DOCUMENTED |

---

## C. S4 Retraction (Rate Limiter)

| Previous Claim | Current Reality |
|---|---|
| "In-memory rate limiter only — no Redis-backed distributed rate limiter" | **RETRACTED.** `backend/app/core/rate_limit.py` implements `RedisRateLimiter` (sliding window via Lua script); `REDIS_URL=redis://redis:6379/0` is wired in `compose.yml`. Backend falls back to `InMemoryRateLimiter` only when Redis is unreachable or `REDIS_URL` is unset. |

---

## D. O9 Resolution (Mailpit)

| Previous Claim | Current Reality |
|---|---|
| "Mailpit not provisioned in `compose.yml`" | **CLOSED.** Mailpit is in `compose.override.yml:90-94` (`8025:8025` + `1025:1025`). `compose.override.yml` IS part of the dev stack (loaded automatically by `docker compose up`). |

---

## E. Validation Commands

These commands can be re-run to verify claims:

```bash
# Verify Redis is in compose and REDIS_URL is wired
grep -n "REDIS_URL" compose.yml backend/app/core/rate_limit.py backend/app/core/config.py

# Verify service count
grep -n "^  [a-z]" compose.yml

# Verify rate-limit constants
grep -n "times=\|seconds=" backend/app/core/rate_limit.py

# Verify link targets
ls docs/README.md docs/CURRENT_STATE.md docs/MASTER_MATRICES.md docs/ARCHITECTURE_DIAGRAMS.md docs/DEFINITION_OF_DONE.md

# Verify doc cross-references
grep -o '\.\./[a-zA-Z_-]*\.md' docs/README.md | sort -u
```

---

## F. Status Summary

| Category | Items | Confirmed | Actioned |
|---|---|---|---|
| Documentation deliverables | 6 | 6/6 | All complete |
| Codebase coverage areas | 49 | 49/49 | All documented or verified |
| Previous open findings retracted | 1 | 1/1 | S4 retracted |
| Previous open findings closed | 1 | 1/1 | O9 closed |

**OVERALL STATUS: COMPLETE.** All documentation deliverables written, all 49 coverage areas addressed, all prior findings verified or corrected, all doc links validated.
