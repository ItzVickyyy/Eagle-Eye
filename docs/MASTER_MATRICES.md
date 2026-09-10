# Eagle Eye — Master Matrices

> Comprehensive cross-reference matrices covering features, files, dependencies, APIs, database, security, environment, and Docker.
> All data reflects commit `792c43c` (2026-09-08).

---

## 1. Feature Matrix

| Feature | Spec Section | Backend Route | Frontend Route | Model | Migration | Status |
|---|---|---|---|---|---|---|
| Authentication (JWT) | §5.6 | `login.py` | `/login` | `User` | 0001 | IMPLEMENTED |
| User signup | §5.6 | `users.py` | `/signup` | `User` | 0001 | IMPLEMENTED |
| User profile | §5.6 | `users.py` | `/dashboard/account` | `User` | 0001 | IMPLEMENTED |
| Password recovery | §5.6 | `password.py` | `/recover-password` | `User` | 0001 | IMPLEMENTED |
| Password reset | §5.6 | `password.py` | `/reset-password` | `User` | 0001 | IMPLEMENTED |
| Article CRUD | §5.2-5.4 | `articles.py` | `/dashboard/articles` | `Article` | 0002 | IMPLEMENTED |
| Article status workflow | §5.2-5.4 | `articles.py` | review queue UI | `Article` | 0002 | IMPLEMENTED |
| Category management | §5.3 | `categories.py` | `/dashboard/categories` | `Category` | 0002 | IMPLEMENTED |
| Tag management | §5.3 | `tags.py` | `/dashboard/categories` | `Tag` | 0002 | IMPLEMENTED |
| Media upload | §5.2 | `media.py` | editor upload | `Media` | 0004 | IMPLEMENTED |
| Comments (public) | §5.1 SHOULD | `comments.py` | article detail | `Comment` | 0006 | IMPLEMENTED (feature-flagged) |
| Contact form | §5.1 MUST | `contact.py` | `/contact` | `ContactMessage` | 0005 | IMPLEMENTED |
| Club members (About Us) | §5.4 | `club_members.py` | `/about-us` | `ClubMember` | 0003 | IMPLEMENTED |
| Site settings | §5.4 | `settings.py` | admin settings | `SiteSetting` | 0005 | IMPLEMENTED |
| Developer tools | §5.5 | `developer.py` | `/dashboard/developer` | `ApplicationAuditLog` | 0013 | IMPLEMENTED |
| Feature flags (runtime) | §5.5.1 | `developer.py` | developer dashboard | `FeatureFlag` | 0013 | IMPLEMENTED |
| Audit log | §5.5.2 | `developer.py` | developer logs | `ApplicationAuditLog` | 0013 | IMPLEMENTED |
| CAPTCHA (Turnstile) | §5.6 | `captcha.py` | frontend widget | — | — | IMPLEMENTED |
| CSP headers | §5.6 | `main.py` | — | — | — | IMPLEMENTED |
| Rate limiting (login) | §5.6 | `login.py` | — | — | — | IMPLEMENTED (Redis-backed) |
| Rate limiting (contact) | §5.6 | `contact.py` | — | — | — | IMPLEMENTED (Redis-backed) |
| Rate limiting (password) | §5.6 | `password.py` | — | — | — | IMPLEMENTED (Redis-backed) |
| Maintenance mode | §5.5.1 | `developer.py` | developer dashboard | `FeatureFlag` | 0013 | IMPLEMENTED |
| Developer logs (audit) | §5.5.2 | `developer.py` | developer dashboard | `ApplicationAuditLog` | 0013 | IMPLEMENTED |
| Analytics overview | §5.4 SHOULD | `analytics.py` | `/dashboard/analytics` | `Article.views_count` | — | IMPLEMENTED |
| Profile picture | §6 | — | — | — | — | DEFERRED (not implemented) |
| ReviewAssignment model | — | — | — | — | — | SPEC GAP (not implemented, spec intent unclear) |
| Redis-backed rate limiting | §5.6 | `rate_limit.py` | `REDIS_URL` (compose.yml) | — | — | IMPLEMENTED (fail-open to in-memory) |
| Dark mode | §5.1 OPTIONAL | — | — | — | — | NOT IMPLEMENTED |
| Newsletter subscription | §5.1 OPTIONAL | — | — | — | — | NOT IMPLEMENTED |
| Social sharing | §5.1 SHOULD | — | — | — | — | NOT IMPLEMENTED |
| Reading-time estimate | §5.1 SHOULD | — | — | — | — | NOT IMPLEMENTED |
| Related articles | §5.1 SHOULD | — | — | — | — | NOT IMPLEMENTED |
| Tag-based filtering | §5.1 SHOULD | — | — | — | — | NOT IMPLEMENTED |
| Pagination | §5.1 SHOULD | — | — | — | — | NOT IMPLEMENTED |

---

## 2. File-to-Feature Matrix (Key Files)

| File | Feature(s) | Lines (approx) |
|---|---|---|
| `backend/app/main.py` | App factory, CSP, lifespan | ~300 |
| `backend/app/api/routes/login.py` | JWT auth, rate limiting | ~120 |
| `backend/app/api/routes/users.py` | Signup, profile, user management | ~200 |
| `backend/app/api/routes/articles.py` | Article CRUD, review queue | ~300 |
| `backend/app/api/routes/categories.py` | Category CRUD | ~100 |
| `backend/app/api/routes/tags.py` | Tag CRUD | ~80 |
| `backend/app/api/routes/media.py` | Media upload, list, delete | ~150 |
| `backend/app/api/routes/comments.py` | Comment create, moderate, delete | ~200 |
| `backend/app/api/routes/contact.py` | Contact form submission, admin inbox | ~150 |
| `backend/app/api/routes/password.py` | Password recovery, reset | ~120 |
| `backend/app/api/routes/developer.py` | Feature flags, logs, diagnostics | ~300 |
| `backend/app/api/routes/analytics.py` | Analytics overview | ~80 |
| `backend/app/api/routes/club_members.py` | Club member CRUD | ~150 |
| `backend/app/api/routes/settings.py` | Site settings | ~100 |
| `backend/app/api/deps.py` | Auth deps, RBAC checks | ~170 |
| `backend/app/core/config.py` | Settings, env validation | ~250 |
| `backend/app/core/security.py` | JWT, hashing, revocation | ~150 |
| `backend/app/core/captcha.py` | Turnstile verification | ~80 |
| `backend/app/utils.py` | Email sending utilities | ~100 |
| `backend/scripts/entrypoint.sh` | Container entrypoint | ~30 |
| `backend/scripts/prestart.sh` | Alembic + initial data | ~15 |
| `frontend/src/client/sdk.gen.ts` | Generated API SDK | ~1000 |
| `frontend/src/client/client.gen.ts` | Generated API client | ~50 |
| `frontend/src/client/types.gen.ts` | Generated types | ~500 |
| `compose.yml` | Base compose config | ~37 |
| `compose.override.yml` | Dev overrides | ~119 |
| `compose.deploy.yml` | Production deploy | ~80+ |
| `backend/Dockerfile` | Multi-stage build | ~60+ |
| `docker-socket-proxy/haproxy.cfg.template` | Proxy security rules | ~53+ |
| `opencode.json` | opencode tool config | ~small |

---

## 3. Dependency Matrix

### Python (pyproject.toml / uv.lock)

| Dependency | Version (locked) | Purpose | Direct? |
|---|---|---|---|
| fastapi | 0.12.22 | Web framework | Yes |
| uvicorn | 0.38.0 | ASGI server | Yes |
| sqlmodel | 0.0.24 | ORM/models | Yes |
| sqlalchemy | 2.0.41 | Database layer | Yes (via sqlmodel) |
| alembic | 1.16.5 | Migrations | Yes |
| pydantic | 2.12.5 | Validation | Yes |
| pydantic-settings | 2.10.1 | Settings | Yes |
| python-jose | 3.5.0 | JWT | Yes |
| argon2-cffi | 23.1.0 | Password hashing | Yes |
| passlib | 1.7.4 | Password utilities | Yes |
| boto3 | 1.43.89 | S3 storage | Yes |
| redis | 6.2.0 | Redis client | Yes |
| httpx | 0.28.1 | HTTP client | Yes |
| emails | 0.6 | Email templates | Yes |
| mypy | 1.19.1 | Type checking | Yes (dev) |
| ruff | 0.14.1 | Linting | Yes (dev) |
| pytest | 8.4.2 | Testing | Yes (dev) |
| pytest-cov | 6.3.0 | Coverage | Yes (dev) |

### Frontend (package.json / bun.lock)

| Dependency | Purpose | Direct? |
|---|---|---|
| react / react-dom | UI framework | Yes |
| @tanstack/react-query | State/data fetching | Yes |
| @tanstack/react-router | Routing | Yes |
| tailwindcss | Styling | Yes |
| @hey-api/openapi-ts | Client generation | Yes (dev) |
| @playwright/test | E2E testing | Yes (dev) |
| vite | Build tool | Yes (dev) |
| typescript | Type system | Yes (dev) |

---

## 4. API Endpoint Matrix

| Method | Path | Auth Required | RBAC | Rate Limited | Feature Flag | Notes |
|---|---|---|---|---|---|---|
| POST | `/api/v1/login/access-token` | No | — | Yes (20/60s, Redis-backed) | — | Returns JWT |
| POST | `/api/v1/login/test-token` | No | — | — | — | Debug only |
| POST | `/api/v1/users/signup` | No | — | Yes (20/60s, Redis-backed) | `dev_allow_public_signup` | CAPTCHA gated |
| GET | `/api/v1/users/me` | Yes | Any role | — | — | Current user |
| PATCH | `/api/v1/users/me` | Yes | Any role | — | — | Update profile |
| GET | `/api/v1/users/` | Yes | super_admin | — | — | List users |
| POST | `/api/v1/users/` | Yes | super_admin | — | — | Create user |
| PATCH | `/api/v1/users/{id}` | Yes | super_admin | — | — | Update user |
| DELETE | `/api/v1/users/{id}` | Yes | super_admin | — | — | Deactivate user |
| GET | `/api/v1/articles/` | No | — | — | — | Published list |
| GET | `/api/v1/articles/{id}` | No | — | — | — | Article detail |
| GET | `/api/v1/articles/by-slug/{slug}` | No | — | — | — | Slug lookup |
| POST | `/api/v1/articles/` | Yes | admin+ | — | — | Create article |
| PATCH | `/api/v1/articles/{id}` | Yes | author/admin | — | — | Update article |
| DELETE | `/api/v1/articles/{id}` | Yes | author/admin | — | — | Delete article |
| GET | `/api/v1/articles/review-queue/` | Yes | admin+ | — | — | Pending articles |
| PATCH | `/api/v1/articles/{id}/status` | Yes | admin+ | — | — | Approve/reject |
| GET | `/api/v1/categories/` | No | — | — | — | List categories |
| POST | `/api/v1/categories/` | Yes | admin+ | — | — | Create category |
| PATCH | `/api/v1/categories/{id}` | Yes | admin+ | — | — | Update category |
| DELETE | `/api/v1/categories/{id}` | Yes | super_admin | — | — | Delete category |
| GET | `/api/v1/tags/` | No | — | — | — | List tags |
| POST | `/api/v1/tags/` | Yes | admin+ | — | — | Create tag |
| POST | `/api/v1/media/` | Yes | contributor+ | — | — | Upload media |
| GET | `/api/v1/media/` | Yes | contributor+ | — | — | List media |
| DELETE | `/api/v1/media/{id}` | Yes | owner/admin | — | — | Delete media |
| POST | `/api/v1/comments/` | No | — | Yes (30/60s, Redis-backed) | `dev_public_comments_enabled` | Public comment |
| GET | `/api/v1/comments/article/{id}` | No | — | — | — | Article comments |
| GET | `/api/v1/comments/all` | Yes | admin+ | — | — | All comments |
| PATCH | `/api/v1/comments/{id}` | Yes | admin+ | — | — | Moderate comment |
| DELETE | `/api/v1/comments/{id}` | Yes | admin+ | — | — | Delete comment |
| POST | `/api/v1/contact/` | No | — | Yes (15/60s, Redis-backed) | `dev_contact_form_enabled` | CAPTCHA gated |
| GET | `/api/v1/contact/` | Yes | admin+ | — | — | Admin inbox |
| POST | `/api/v1/password-recovery/{email}` | No | — | Yes (10/60s, Redis-backed) | — | CAPTCHA gated |
| POST | `/api/v1/reset-password/` | No | — | Yes (10/60s, Redis-backed) | — | Reset token |
| GET | `/api/v1/developer/feature-flags` | Yes | developer | — | — | Read flags |
| PATCH | `/api/v1/developer/feature-flags` | Yes | developer | — | — | Update flags |
| GET | `/api/v1/developer/logs` | Yes | developer | — | — | Audit logs |
| GET | `/api/v1/analytics/overview` | Yes | admin+ | — | — | Stats overview |
| GET | `/api/v1/club-members/` | No | — | — | — | Active members |
| GET | `/api/v1/club-members/all` | Yes | admin+ | — | — | All members |
| POST | `/api/v1/club-members/` | Yes | super_admin | — | — | Create member |
| PATCH | `/api/v1/club-members/{id}` | Yes | super_admin | — | — | Update member |
| DELETE | `/api/v1/club-members/{id}` | Yes | super_admin | — | — | Delete member |
| GET | `/api/v1/settings/` | No | — | — | — | Public settings |
| GET | `/api/v1/settings/all` | Yes | super_admin | — | — | All settings |
| PUT | `/api/v1/settings/` | Yes | super_admin | — | — | Update settings |
| GET | `/api/v1/utils/health-check/` | No | — | — | — | Health check |

---

## 5. Database Migration Matrix

| Migration | Commit | Tables Affected | Key Changes |
|---|---|---|---|
| 0001 | — | `user` | Initial user table with roles, auth fields |
| 0002 | — | `article`, `category`, `tag`, `article_tag` | Article system with categories and tags |
| 0003 | — | `club_member` | Club members CMS |
| 0004 | — | `media` | Media upload tracking |
| 0005 | — | `contact_message`, `site_setting` | Contact form + site settings |
| 0006 | — | `comment` | Comment system with moderation |
| 0007 | — | — | Schema adjustments |
| 0008 | — | — | Schema adjustments |
| 0009 | — | — | Schema adjustments |
| 0010 | — | — | Schema adjustments |
| 0011 | — | — | Schema adjustments |
| 0012 | — | — | Schema adjustments |
| 0013 | — | `feature_flag`, `application_audit_log` | Developer tools: feature flags + audit log |

---

## 6. Security Matrix

| Requirement | Section | Implementation | Status |
|---|---|---|---|
| Authentication | §5.6 | JWT + argon2 hashing | PASS |
| RBAC enforcement | §4.1 | Backend `deps.py` dependency injection | PASS |
| Developer role isolation | §4.2 | `is_developer` flag, separate checks | PASS |
| Input validation | §5.6 | Pydantic models | PASS |
| CSP headers | §5.6 | `main.py` middleware | PASS |
| CAPTCHA (Turnstile) | §5.6 | `captcha.py` + env validation | PASS |
| Rate limiting (login) | §5.6 | Redis-backed sliding window by default (fail-open to in-memory) | PASS |
| Rate limiting (contact) | §5.6 | Redis-backed sliding window by default (fail-open to in-memory) | PASS |
| Rate limiting (password) | §5.6 | In-memory | PASS |
| Secrets out of source control | §9 | `.env` gitignored, `.env.example` templates, `guard-secrets.sh` | PASS (D1 remediated) |
| HTTPS (production) | §5.6 | Traefik ACME TLS | PASS (deploy config) |
| Container security | — | Vendored socket-proxy, SHA-pinned image | PASS |
| Audit logging | §5.5.2 | `ApplicationAuditLog` model + endpoint | PASS |
| Feature flag gating | §5.5.1 | 4 runtime flags | PASS |
| Password hashing | §5.6 | argon2-cffi | PASS |
| Token revocation | — | `security.py` revocation check | PASS |

---

## 7. Environment Variable Matrix

| Variable | Required | Default | Where Set | Used By |
|---|---|---|---|---|
| `SECRET_KEY` | Yes (prod) | — | `.env` | `config.py` |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` | `.env` / compose | `config.py` |
| `FIRST_SUPERUSER` | Yes | `admin@eagleeye.dev` | compose.yml | `initial_data.py` |
| `FIRST_SUPERUSER_PASSWORD` | Yes | — | `.env` | `initial_data.py` |
| `FASTAPI_ENV` | No | `development` | compose.yml | `config.py` |
| `CAPTCHA_ENABLED` | No | `False` | `.env` | `captcha.py` |
| `TURNSTILE_SITE_KEY` | If CAPTCHA | — | `.env` | `captcha.py` |
| `TURNSTILE_SECRET_KEY` | If CAPTCHA | — | `.env` | `captcha.py` |
| `VITE_API_URL` | No | (empty) | `frontend/.env` | Vite build |
| `VITE_TURNSTILE_SITE_KEY` | If CAPTCHA | — | `frontend/.env` | Turnstile widget |
| `SMTP_HOST` | For email | `mailpit` | compose.override.yml | `utils.py` |
| `SMTP_PORT` | For email | `1025` | compose.override.yml | `utils.py` |
| `SMTP_TLS` | For email | `false` | compose.override.yml | `utils.py` |
| `SENTRY_DSN` | No | — | `.env` | Error tracking |
| `FRONTEND_HOST` | Deploy | — | compose.deploy.yml | CORS |
| `DOMAIN` | Deploy | — | compose.deploy.yml | Traefik |
| `PROJECT_NAME` | Deploy | — | compose.deploy.yml | Traefik |
| `SKIP_PRESTART` | CI | — | workflow env | `entrypoint.sh` |
| `MEDIA_STORAGE_BACKEND` | No | `local` | `.env` | `utils.py` |

---

## 8. Docker Compose Matrix

| Service | Image | Networks | Volumes | Exposed Ports | Config File |
|---|---|---|---|---|---|
| `backend` | Custom (backend/Dockerfile) | `default`, `proxy` | uploads (deploy), htmlcov (dev) | internal / 8000 (dev) | compose.yml + overrides + deploy |
| `db` | postgres:18 | `default` | `app-postgres-data` | 5432 (dev) | compose.yml + overrides |
| `proxy` | traefik:3.6 | `default`, `proxy` | `traefik-certificates` (deploy) | 80/8090 (dev), 80/443 (deploy) | compose.yml + overrides + deploy |
| `socket-proxy` | tecnativa/docker-socket-proxy (SHA-pinned) | `proxy` | vendored haproxy.cfg.template | — (no ports exposed) | compose.yml |
| `redis` | redis:7-alpine | `default` | `app-redis-data` (deploy) | 6379 (dev) | compose.yml |
| `mailpit` | axllent/mailpit | `default` | — | 8025/1025 | compose.override.yml |
| `adminer` | adminer (latest) | `default` | — | 8080 (Traefik) | compose.override.yml |
| `playwright` | Custom (Dockerfile.playwright) | `default` | blob-report, test-results | 9323 | compose.override.yml |

---

## 9. CI Workflow Matrix

| Workflow | File | Trigger | Key Actions | Runner |
|---|---|---|---|---|
| test-backend | `test-backend.yml` | push/PR main | pytest + coverage + smokeshow | ubuntu-latest |
| test-docker-compose | `test-docker-compose.yml` | push/PR main | Docker Compose integration | ubuntu-latest |
| playwright | `playwright.yml` | push/PR main | 4-shard e2e tests | ubuntu-latest |
| pre-commit | `pre-commit.yml` | push/PR main | Linting/formatting | ubuntu-latest |
| deploy | `deploy.yml` | push main | `uv run fastapi deploy` | ubuntu-latest |
| deploy-docker-compose | `deploy-docker-compose.yml` | push main | rsync + SSH + Docker | self-hosted |
| detect-conflicts | `detect-conflicts.yml` | PR main | Merge conflict detection | ubuntu-latest |
| guard-dependencies | `guard-dependencies.yml` | pull_request_target | Author gate | ubuntu-latest |
| smokeshow | `smokeshow.yml` | push/PR main | Coverage HTML publish | ubuntu-latest |
| zizmor | `zizmor.yml` | push/PR main | GH Actions security scan | ubuntu-latest |

---

## 10. Asset Inventory

> **Note:** All visual assets marked **UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE** because the auditing agent cannot render or inspect binary image/font files.

| Asset Type | Location | Status |
|---|---|---|
| Frontend logos | `frontend/public/` | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
| Favicon | `frontend/public/` | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
| Background patterns | `frontend/public/` | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
| Fonts | `frontend/` or CDN | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
| Legacy logo reference | `Media-Club-2023/Images/logo.webp` | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
| Legacy favicon reference | `Media-Club-2023/Images/logoico.ico` | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
| Legacy background reference | `Media-Club-2023/styles/Background.webp` | UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE |
