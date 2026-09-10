# Eagle Eye — Roadmap

Actionable remaining work. Completed history lives in [`docs/MILESTONES.md`](./MILESTONES.md).

Status markers: `[ ]` not started · `[~]` in progress · `[x]` done

---

## NOW — Blocking or High-Value

These items should be resolved before any production release is considered complete.

- [ ] **Verify production deployment.** CI has a `deploy` workflow targeting FastAPI Cloud and a `deploy-docker-compose` workflow targeting a self-hosted runner. Confirm these are connected to a real environment, the domain is configured, and the application is reachable end-to-end.

- [ ] **Schedule and verify operational backups.** The backup scripts (`scripts/backup/`) have been locally verified — `db-backup.sh`, `db-verify.sh`, `db-restore.sh`, `media-backup.sh`, and `media-restore.sh` all pass. The operator must schedule automated `pg_dump` and uploads-directory backups, configure off-host storage, and verify production restore procedures. See [`docs/BACKUP_RECOVERY.md`](./BACKUP_RECOVERY.md).

---

## NEXT — Important but Not Immediately Blocking

- [ ] **Resolve legacy API client directory.** `sdk.gen.ts` still imports from the legacy `client/client/` directory alongside the current `@hey-api` generated client. Consolidate to a single client path to remove the dead reference.

- [ ] **Comprehensive accessibility audit.** No structured a11y audit has been performed. Review keyboard navigation, screen-reader semantics, focus management, and color-contrast across public-facing pages.

- [ ] **Add reading-time estimates to articles.** Calculate and display estimated read time on article detail and listing pages.

- [ ] **Add related articles.** Surface contextually related articles at the bottom of article detail pages (by category or tags).

- [ ] **Add social sharing.** Provide share links/buttons on article detail pages (copy-link, or Open Graph meta for social preview).

- [ ] **Review archive-management UX.** Confirm the admin archive workflow (archive/restore) is fully surfaced in the admin UI and that archived articles are handled correctly in public listing filters.

- [ ] **Address remaining P3 / SHOULD-level security observations.** No open vulnerabilities exist, but the security audit surfaced P3 observations and SHOULD-level hardening items that are not yet resolved. See [`docs/SECURITY_MEASURES.md`](./SECURITY_MEASURES.md).

---

## DEFERRED — Not Needed for Release

- [ ] **Reactions on articles/comments.** Emoji-reaction system was considered and deferred; not in scope for the initial release.

- [ ] **Newsletter / email subscription.** Subscriber list and newsletter dispatch are not implemented and not currently planned.

---

## OPTIONAL — Nice-to-Have

- [ ] **Dark mode.** The frontend uses Tailwind CSS and shadcn/ui, which both support dark mode. Not implemented; no current requirement.

- [ ] **S3/R2/B2/MinIO automated backup.** Object-storage backup is listed as provider-responsibility in the runbook. An operator-side automation script would reduce manual burden but is not in-scope for this project.

---

> Work already completed is recorded in [`docs/MILESTONES.md`](./MILESTONES.md).
> Technical system details live in [`docs/SYSTEM_SPECIFICATION.md`](./SYSTEM_SPECIFICATION.md).
