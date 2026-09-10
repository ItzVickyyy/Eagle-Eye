# Eagle Eye — Documentation Index

> **Personal rebuild of the CDLB Media Club news website.**
> Originally a Grade 12 Practical Research project (Dumagco, Reboton, Salen — "Development of News Website for the Schools Publication of Colegio de Los Baños"). This is a personal rebuild, **not** a capstone.

---

## Documentation Map

| Document | Purpose | Audience |
|---|---|---|
| [`SYSTEM_SPEC.md`](SYSTEM_SPEC.md) | Full system specification (v5) — scope, roles, features, data model, sitemap, acceptance criteria, legacy parity rules | All |
| [`SECURITY_AUDIT_REPORT.md`](SECURITY_AUDIT_REPORT.md) | 2026-09-08 security audit — 20 requirements evaluated, all PASS (no open P0/P1) | Security reviewers |
| [`security-remediation.md`](security-remediation.md) | Secrets safeguard record — verified `.env` never committed, `.env.example` templates, `guard-secrets.sh` | Security / DevOps |
| [`backup-recovery.md`](backup-recovery.md) | Backup & recovery runbook — `pg_dump` database backups, `uploads/` file backups, restore procedures | Operations |
| [Root `README.md`](../README.md) | Project overview, stack, quick start, domain models | Developers, contributors |
| [`development.md`](../development.md) | Local development setup — Docker Compose, FastAPI, Vite, Mailpit | Developers |
| [`deployment.md`](../deployment.md) | FastAPI Cloud deployment guide | Deployers |
| [`deployment-docker-compose.md`](../deployment-docker-compose.md) | Self-hosted Docker Compose deployment (Traefik HTTPS) | Deployers / sysadmins |
| [`backend/README.md`](../backend/README.md) | Backend overview — local dev, VS Code debugger, testing, API | Backend developers |
| [`frontend/README.md`](../frontend/README.md) | Frontend overview — Bun, Vite, client generation, Playwright | Frontend developers |
| [`scripts/backup/README.md`](../scripts/backup/README.md) | Backup scripts usage and restore procedures | Operations |

---

## Reading Order (recommended)

1. **New to the project?** Start with the [root README](../README.md), then [`SYSTEM_SPEC.md`](SYSTEM_SPEC.md).
2. **Setting up locally?** See [`development.md`](../development.md) and [`backend/README.md`](../backend/README.md).
3. **Deploying?** Choose [`deployment.md`](../deployment.md) (FastAPI Cloud) or [`deployment-docker-compose.md`](../deployment-docker-compose.md) (self-hosted).
4. **Security review?** Read [`SECURITY_AUDIT_REPORT.md`](SECURITY_AUDIT_REPORT.md) then [`security-remediation.md`](security-remediation.md).
5. **Operations?** See [`backup-recovery.md`](backup-recovery.md) and [`scripts/backup/README.md`](../scripts/backup/README.md).

---

## Cross-Reference: Stale Audit Baselines (Archived)

The two release-readiness audit documents were deleted as part of the current documentation audit (uncommitted working-tree changes). They contained stale baselines (`d32fa60` and `d967664`) with outdated stack claims (React 19 + Mantine 7). The live truth for security posture is `SECURITY_AUDIT_REPORT.md` (2026-09-08, HEAD `792c43c`).

---

## Documentation Gaps Identified (Phase C)

These gaps were identified during the cross-reference phase and are addressed by the docs in this directory:

| Gap | Resolution |
|---|---|
| No `docs/README.md` master index | **This file** |
| No current-state document | [`CURRENT_STATE.md`](CURRENT_STATE.md) |
| No master matrices | [`MASTER_MATRICES.md`](MASTER_MATRICES.md) |
| No architecture diagrams | [`ARCHITECTURE_DIAGRAMS.md`](ARCHITECTURE_DIAGRAMS.md) |
| No definition-of-done checklist | [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) |

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
9. `SYSTEM_SPEC.md`
10. Security audit reports
11. Other documentation
12. Git history
13. Comments
14. Inference / general knowledge

---

## Fact Labels Used in This Documentation

| Label | Meaning |
|---|---|
| **CONFIRMED FACT** | Verified against source code, runtime behavior, or authoritative config |
| **STRONG INFERENCE** | Supported by multiple evidence sources but not directly verified |
| **UNKNOWN** | Requires verification; not yet confirmed |
| **HISTORICAL FACT** | True at a specific point in time; may no longer reflect current state |
| **SPECIFICATION INTENT** | What the spec requires; implementation may differ |
| **IMPLEMENTATION REALITY** | What the code actually does; may differ from spec intent |

---

## Asset Inventory Note

All frontend visual assets (logos, images, fonts, backgrounds) are marked **UNKNOWN — VISUAL VERIFICATION NOT AVAILABLE** throughout documentation because the auditing agent does not have access to render or inspect binary image/font files visually.
