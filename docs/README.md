# Eagle Eye — Documentation Index

> **Personal rebuild of the CDLB Media Club news website.**
> Originally a Grade 12 Practical Research project (Dumagco, Reboton, Salen — "Development of News Website for the Schools Publication of Colegio de Los Baños"). This is a personal rebuild, **not** a capstone.

---

## Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| [`SYSTEM_SPECIFICATION.md`](SYSTEM_SPECIFICATION.md) | Authoritative technical specification — architecture, API surface, security, RBAC, data model | All |
| [`SECURITY_MEASURES.md`](SECURITY_MEASURES.md) | Security posture, audit findings, environment-file safeguards | Security reviewers / DevOps |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Mermaid diagrams of system architecture, data flow, deployment topology | Architects / contributors |
| [`BACKUP_RECOVERY.md`](BACKUP_RECOVERY.md) | Backup & recovery runbook — `pg_dump` database backups, `uploads/` file backups, restore procedures | Operations |
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | Current application state — verified features, environments, service URLs | Developers / contributors |
| [`REQUIREMENTS_MATRIX.md`](REQUIREMENTS_MATRIX.md) | Feature-to-file, dependency, API, DB, security, environment, and Docker matrices | Developers / QA |
| [`MILESTONES.md`](MILESTONES.md) | Historical record of completed work with verified commit hashes | All |
| [`ROADMAP.md`](ROADMAP.md) | Remaining and planned work, prioritized by implementation sequence | Developers |
| [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) | Release-readiness checklist — all artifacts required before production deployment | Developers / reviewers |

---

## Related Documentation (outside `docs/`)

| Document | Purpose | Audience |
|----------|---------|----------|
| [Root `README.md`](../README.md) | Project overview, stack, quick start, domain models | Developers, contributors |
| [`development.md`](../development.md) | Local development setup — Docker Compose, FastAPI, Vite, Mailpit | Developers |
| [`deployment.md`](../deployment.md) | FastAPI Cloud deployment guide | Deployers |
| [`deployment-docker-compose.md`](../deployment-docker-compose.md) | Self-hosted Docker Compose deployment (Traefik HTTPS) | Deployers / sysadmins |
| [`backend/README.md`](../backend/README.md) | Backend overview — local dev, VS Code debugger, testing, API | Backend developers |
| [`frontend/README.md`](../frontend/README.md) | Frontend overview — Bun, Vite, client generation, Playwright | Frontend developers |
| [`scripts/backup/README.md`](../scripts/backup/README.md) | Backup scripts usage and restore procedures | Operations |

---

## Reading Order (recommended)

1. **New to the project?** Start with the [root README](../README.md), then [`SYSTEM_SPECIFICATION.md`](SYSTEM_SPECIFICATION.md).
2. **Setting up locally?** See [`development.md`](../development.md) and [`backend/README.md`](../backend/README.md).
3. **Deploying?** Choose [`deployment.md`](../deployment.md) (FastAPI Cloud) or [`deployment-docker-compose.md`](../deployment-docker-compose.md) (self-hosted).
4. **Security review?** Read [`SECURITY_MEASURES.md`](SECURITY_MEASURES.md).
5. **Operations?** See [`BACKUP_RECOVERY.md`](BACKUP_RECOVERY.md) and [`scripts/backup/README.md`](../scripts/backup/README.md).
6. **Architecture diagrams?** See [`ARCHITECTURE.md`](ARCHITECTURE.md).
7. **What's done / what's next?** [`MILESTONES.md`](MILESTONES.md) for history, [`ROADMAP.md`](ROADMAP.md) for upcoming work.

---

## Source-of-Truth Hierarchy

When documentation conflicts with reality, resolve in this order:

1. Code (source files)
2. Models / migrations / schema
3. Tests
4. Runtime config (`.env`, `compose*.yml`)
5. Docker / Compose
6. Manifests / lockfiles (`pyproject.toml`, `uv.lock`, `bun.lock`)
7. CI / GitHub Actions
8. Runtime behavior (actual container output)
9. [`SYSTEM_SPECIFICATION.md`](SYSTEM_SPECIFICATION.md)
10. [`SECURITY_MEASURES.md`](SECURITY_MEASURES.md)
11. Other documentation
12. Git history
13. Comments
14. Inference / general knowledge

---

## Fact Labels Used in This Documentation

| Label | Meaning |
|-------|---------|
| **CONFIRMED FACT** | Verified against source code, runtime behavior, or authoritative config |
| **STRONG INFERENCE** | Supported by multiple evidence sources but not directly verified |
| **UNKNOWN** | Requires verification; not yet confirmed |
| **HISTORICAL FACT** | True at a specific point in time; may no longer reflect current state |
| **SPECIFICATION INTENT** | What the spec requires; implementation may differ |
| **IMPLEMENTATION REALITY** | What the code actually does; may differ from spec intent |

---

## Asset Inventory Note

All frontend visual assets (logos, images, fonts, backgrounds) are marked **UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE** throughout documentation because the auditing agent does not have access to render or inspect binary image/font files visually.
