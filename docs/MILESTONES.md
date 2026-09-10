# Eagle Eye — Milestones

Historical record of completed achievements, in order from earliest to most recent.
All commit hashes are verified against the repository git log.

---

## Foundation

**`f8dd2e6`** — Foundation (initial commit)

Bootstrapped the repository from a Full Stack FastAPI Template base. Established the project skeleton: backend (FastAPI + SQLModel), frontend (React + TypeScript + Vite), Docker Compose dev environment, and GitHub Actions CI.

---

## Core Feature Implementation

**`288946e`** — Add models and routes for comments, categories, club members, media, and settings

Introduced the core domain models and API routes that define Eagle Eye's content system: `Comment`, `Category`, `ClubMember`, `Media`, and `SiteSetting`. These established the editorial and CMS foundation on top of the base template's `User` and `Article` scaffolding.

**`704e997`** — feat: implement environment file safeguards and add example templates

Added `.env.example` template files and a `scripts/guard-secrets.sh` pre-commit guard to prevent accidental secret exposure.

---

## Public Website

**`6f39776`** — feat: add public Eagle Eye media club website

Shipped the public-facing frontend: article listing, article detail, categories, club member roster (About Us), contact form, and supporting pages. The website became a real, navigable product for CDLB Media Club readers.

---

## Documentation Baseline

**`dd766bd`** — Update system specification to v4 and enhance project overview

Formalized the system specification document and updated the project overview, producing the first substantial documentation baseline.

---

## Release Readiness Audit — Phase 1

**`c8bf3c6`** — docs: record final release readiness audit phase 2

Completed the first documented release readiness audit pass, capturing implementation status across all major system areas.

**`d967664`** — chore: clean post-audit development artifacts

Cleaned up development artifacts surfaced during the audit.

---

## Security Hardening Sprint

The following commits represent a deliberate, systematic hardening of the entire application security surface, completed in sequence:

| Commit | Description |
|--------|-------------|
| `0ce8fb2` | Add HTTP security headers (CSP, HSTS, X-Content-Type-Options, etc.) |
| `804d6fd` | Add optional Redis-backed sliding-window rate limiting for cross-worker enforcement |
| `d13f420` | Add Cloudflare Turnstile CAPTCHA protection on sensitive endpoints |
| `337b76d` | Close CAPTCHA CSP production blocker |
| `b643c75` | Add JWT token revocation and session invalidation (`token_revocations` table, `jti`, `token_version`) |
| `e45bfa6` | Gate admin shell access by role |
| `cbc3725` | Harden Traefik Docker socket access via SHA-pinned Tecnativa socket proxy |
| `1728cad` | Force `noopener` on `target=_blank` links |
| `342e2b1` | Expand backend route and core test coverage |
| `1bc34d6` | Isolate per-invocation SQLite test DB and centralize middleware engine alignment |
| `fc5093c` | Allow `/uploads/` and `/assets/` descendants during maintenance mode |
| `fcf527c` | Map `TokenRevocation` to correct `token_revocations` table |
| `9f570cf` | Allow password recovery/reset during maintenance mode |
| `c186f76` | Add COOP and CORP headers |
| `be5c169` | Harden Redis rate limiting |
| `dda77d6` | Harden CAPTCHA client IP handling |
| `4e78c20` | Validate media file URLs |
| `fc232de` | Validate article cover image URLs |
| `3c483ee` | Validate club member photo URLs |
| `6b72470` | Harden authentication brute-force protection |
| `280fdab` | Remove production Adminer exposure |
| `fa33199` | Enforce comment moderation governance |
| `25ac9e2` | Proxy frontend API requests through Vite |
| `15d080f` | Harden article and admin workflows |

By the end of this sprint, no P0 or P1 security findings remained open. All audited spec sections passed at the MUST level.

---

## Template Artifact Cleanup

**`d70d047`** — chore: remove inherited template artifacts

**`792c43c`** — docs: correct documentation inaccuracies

**`fff9c0f`** — docs: finalize repository documentation

**`4e03e97`** — chore: remove remaining inherited template artifacts

**`da88200`** — chore: remove remaining template artifacts

Systematic removal of all Full Stack FastAPI Template boilerplate that did not apply to Eagle Eye: placeholder content, irrelevant routes, stale documentation, and development artifacts. The repository now reflects only what Eagle Eye actually is.

---

## Security Remediation — Implementation 12A

Added preventive environment-file safeguards (repo audit confirmed `.env` and `frontend/.env` were never committed to Git):

- Added `.gitignore` rules for `.env` / `.env.*` files
- Added `.env.example` template files (placeholders only)
- Added `scripts/guard-secrets.sh` pre-commit guard

No secrets were exposed through the repository's history, so no rotation is required — see [`docs/security-remediation.md`](./security-remediation.md).

---

## Authoritative Documentation

**`1d629c2`** — docs: rewrite SYSTEM_SPEC.md as authoritative current-system specification

Rewrote `docs/SYSTEM_SPEC.md` from a design proposal into a verified, evidence-based specification of the system as it actually exists. Covers architecture, all API routes, security posture, RBAC, rate limiting, feature flags, media handling, CI/CD, and data model. This document now serves as the single authoritative technical reference for Eagle Eye.

---

> For remaining and planned work, see [`docs/TO-DO.md`](./TO-DO.md).
