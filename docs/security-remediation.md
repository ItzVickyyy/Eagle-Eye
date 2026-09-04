# Security Remediation — Committed Environment Secrets

This document records the repository-hygiene remediation performed in
**Implementation 12A** and the actions that remain for operators.

## What happened

The repository tracked two real environment files containing secrets:

- `.env` (backend): application signing key, first superuser credentials,
  database password, database URL, SMTP configuration.
- `frontend/.env` (frontend): Vite/API URL used by the app and a local Mailpit
  host used only by end-to-end tests.

Both were committed in the initial commit and, because the repository is hosted
at `https://github.com/ItzVickyyy/Eagle-Eye`, their contents are publicly visible
in the remote history.

## What Implementation 12A changed

- Added `.gitignore` rules so real `.env` / `.env.*` files are ignored, while
  `.env.example` templates remain trackable.
- Removed `.env` and `frontend/.env` from Git tracking (`git rm --cached`),
  preserving the local files on disk.
- Added `.env.example` and `frontend/.env.example` templates (no real secrets).
- Added a dependency-free pre-commit guard (`scripts/guard-secrets.sh` wired into
  `.pre-commit-config.yaml`) that blocks any future commit that would track a
  real `.env` file. It runs locally and in the existing `pre-commit.yml` CI.

Application behavior is unchanged: the backend still reads configuration from
environment variables (and, for local development, from the still-present local
`.env`), and deployment continues to inject secrets via GitHub Actions secrets.

## Required follow-up (operator action)

### 1. Rotate the exposed secrets

Removing the files from *tracking* does not invalidate the already-exposed
values. Every secret that was inside `.env` / `frontend/.env` **must be rotated**
because it is public in the remote history. From the Implementation 11 audit the
exposed **categories** were:

| Category | Variable            | Rotation |
|----------|---------------------|----------|
| Signing   | `SECRET_KEY`        | Required |
| Superuser | `FIRST_SUPERUSER_PASSWORD` | Required |
| Database  | `POSTGRES_PASSWORD`, `DATABASE_URL` password | Required |
| Email     | `SMTP_PASSWORD` (if set) | Required if set |

Safe procedures / notes:

- `SECRET_KEY`: generate a new random value and rotate it in the GitHub Actions
  secrets used by `.github/workflows/deploy.yml` and
  `deploy-docker-compose.yml`. Rotating it invalidates outstanding JWTs.
- `FIRST_SUPERUSER_PASSWORD`: change via the app after deployment (or reset
  `FIRST_SUPERUSER_PASSWORD`), then update the Actions secret.
- `POSTGRES_PASSWORD`: new random value; update `compose.yml` / DB password and
  the Actions secret. Requires a coordinated DB + `DATABASE_URL` rotation.
- `SMTP_PASSWORD`: only if an SMTP host with a password is configured.

Do **not** regenerate secrets inside source files or commit any newly generated
value. Configuration stays in environment variables / Actions secrets.

### 2. History remediation (separate, consequential operation)

The historical copies remain in the remote repository history. Removing them is
a **separate, destructive, force-push operation** and was explicitly NOT
performed here. If the operator wants to purge them:

- Use `git filter-repo` (recommended), `filter-branch`, or the BFG to remove
  `.env` and `frontend/.env` from all history.
- This changes every commit hash, so **coordinates/force-push** to the remote and
  requires all collaborators/clones to re-sync.
- Even after purging, treat the values as compromised and keep the rotated ones.

### 3. Verify rotation

- Confirm the new values exist only in environment variables / Actions secrets.
- Run the backend test suite and a deploy smoke test.

## Guard against recurrence

- `scripts/guard-secrets.sh` blocks committing real `.env` files.
- Keep secrets out of `.env.example` templates (they are meant to be committed
  and must contain only `change-me` placeholders).