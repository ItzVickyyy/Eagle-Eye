# Eagle Eye — CDLB Media Club News Website

Eagle Eye is a personal rebuild of the CDLB Media Club news site, originally
built as a Grade 12 Practical Research project in 2023 (PHP, MySQL, HTML/CSS/JS).
This version is a ground-up rewrite on a modern, production-grade stack.

---

## Background

The CDLB Media Club is a student journalism and media organization. In 2023,
a news website was built from scratch as a Grade 12 Practical Research output —
raw PHP, MySQL, and vanilla HTML/CSS/JS, delivered under school-project constraints.

Eagle Eye is that website, rebuilt properly. Same purpose, same organization,
different everything else: a real API, a real auth system, a real frontend
framework, containerized infrastructure, and a security posture that would
survive outside a school server.

---

## What It Does

Eagle Eye is a content management and publishing platform for a student media club:

- **Readers** browse published articles by category or tag, read full articles,
  view the club member roster, and submit contact messages.
- **Contributors** draft, edit, and submit articles for editorial review.
- **Admins** review and publish articles, moderate comments, manage categories,
  tags, media, and club member profiles, and handle contact messages.
- **Super Admins** manage user accounts and system-wide site settings.

The editorial workflow is `draft → pending → published → archived`, with
moderation required at every promotion step.

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python ≥ 3.14, FastAPI, SQLModel + SQLAlchemy, uv |
| Database | PostgreSQL 18, Alembic migrations |
| Auth | JWT (HS256), argon2 password hashing, Cloudflare Turnstile CAPTCHA, token revocation |
| Rate limiting | Redis 7-alpine sliding-window Lua script; in-memory fail-open fallback |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Router, TanStack Query |
| API client | `@hey-api/openapi-ts` auto-generated SDK |
| Infrastructure | Docker Compose, Traefik 3.6, SHA-pinned Tecnativa socket proxy |
| Testing | Pytest (≥ 90% coverage gate), Playwright E2E (4-shard matrix) |
| CI | 13 GitHub Actions workflows |

---

## Getting Started

See [`development.md`](./development.md) for the full local dev workflow. Quick version:

```bash
docker compose watch
```

Then visit:

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- Adminer (DB UI): http://localhost:8080
- Mailpit (dev email inbox): http://localhost:8025
- Traefik dashboard: http://localhost:8090

Default local dev login (configured in `.env`):

- Email: `admin@eagleeye.dev`
- Password: `EagleEyeDev123!`

---

## Documentation

| Document | Purpose |
|----------|---------|
| [`docs/SYSTEM_SPECIFICATION.md`](./docs/SYSTEM_SPECIFICATION.md) | Authoritative technical specification — architecture, API surface, security, RBAC, data model |
| [`docs/MILESTONES.md`](./docs/MILESTONES.md) | Historical record of completed work with verified commit hashes |
| [`docs/ROADMAP.md`](./docs/ROADMAP.md) | Remaining and planned work |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Mermaid diagrams of system architecture |
| [`docs/SECURITY_MEASURES.md`](./docs/SECURITY_MEASURES.md) | Security posture, audit findings, and environment-file safeguards |
| [`docs/BACKUP_RECOVERY.md`](./docs/BACKUP_RECOVERY.md) | Backup and recovery runbook |

---

## License

The original Full Stack FastAPI Template base is MIT licensed.
Eagle Eye is a personal, non-commercial project for the CDLB Media Club.
