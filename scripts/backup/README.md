# Backup Scripts (Eagle Eye)

Operator-facing shell scripts for backing up and restoring the Eagle Eye
**database** and **local media directory**. They wrap the standard
PostgreSQL client tools (`pg_dump`, `pg_restore`, `psql`) and `tar` — no
extra dependencies, no Python code, no in-app UI.

> **Full procedure, retention guidance, and security notes live in
> [`docs/BACKUP_RECOVERY.md`](../../docs/BACKUP_RECOVERY.md).** This README
> is a quick usage reference.

## Scripts

| Script | Purpose |
| --- | --- |
| `db-backup.sh` | Logical backup of the application database to a `.dump` file |
| `db-restore.sh` | Restore a `.dump` archive into a target DB (refuses to touch the live app DB without an explicit override) |
| `db-verify.sh` | Restore an archive into a throwaway DB, run sanity queries, drop the DB on exit |
| `media-backup.sh` | Tarball the local `uploads/` directory |
| `media-restore.sh` | Extract a media tarball into a target directory (refuses to write into the live `uploads/` without an explicit override) |

## Common conventions

- All scripts are POSIX-ish bash. They use `set -e`, `set -u`, `set -o pipefail`.
- Timestamps are UTC ISO-8601 (`YYYYMMDDTHHMMSSZ`) so files sort chronologically.
- Default output directory is `backups/db/` or `backups/media/` (relative to the
  working directory the script is invoked from, typically the repo root).
- Backups are never overwritten silently — re-run with `--force` to allow it.
- Scripts never print the database password.
- Successful artifacts are `chmod 600`'d (operator may need to run as the file owner).

## Quick start

```bash
# 1. Back up the dev database
bash scripts/backup/db-backup.sh

# 2. Verify the dump without touching the live DB
bash scripts/backup/db-verify.sh --archive backups/db/eagle-eye-db-<TS>.dump

# 3. Back up local media
bash scripts/backup/media-backup.sh
```

## Running against the compose-managed DB

Two patterns work:

1. **Run the script on the host** with the compose DB reachable at
   `localhost:<published-port>`. The default `POSTGRES_HOST=localhost` works
   when the DB port is published to the host (`compose.override.yml` does this
   in dev).

2. **Run the script inside the `db` service** so `pg_dump` connects over the
   compose network. Example:

   ```bash
   docker compose exec -T db bash /app/scripts/backup/db-backup.sh
   ```

   To do this, mount `scripts/backup/` into the `db` service. This
   implementation intentionally does not modify `compose.yml`; the operator
   decides whether to add a volume mount for their environment.

## Verifying a backup

`db-verify.sh` never touches the live database. It:

1. Reads the archive TOC via `pg_restore --list`.
2. Creates a uniquely-named temp DB.
3. Restores the archive into it.
4. Counts public tables and reads `alembic_version` (if the table is present).
5. Drops the temp DB (unless `--keep-on-failure` is passed).

If the script cannot find `pg_restore`/`psql`/`createdb`/`dropdb` in `PATH`,
it exits with code `3` and does **not** silently report success.

## Safety recap

- `db-restore.sh` refuses to drop or restore into the live app DB unless
  both `--force` and `ALLOW_LIVE_DB_RESTORE=1` are set.
- `db-restore.sh` defaults to **restore mode** (performs a real restore when
  `--target-db` is given). Pass `--list` explicitly to print the archive
  TOC and exit without touching any database.
- `media-restore.sh` refuses to extract into the live `uploads/` unless
  both `--force` and `ALLOW_LIVE_MEDIA_RESTORE=1` are set.
- `media-restore.sh` defaults to **restore mode** as well. Pass `--list`
  explicitly to print the archive TOC and exit without touching the
  filesystem.
- All scripts exit non-zero on missing tools, missing config, or any error.
