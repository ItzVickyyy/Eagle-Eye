#! /usr/bin/env bash
# -----------------------------------------------------------------------------
# db-restore.sh — Restore a logical pg_dump custom-format backup.
#
# This script is INTENTIONALLY conservative. A restore can irreversibly
# destroy data. The default behavior is:
#
#   1. NEVER touch the live application database (`$POSTGRES_DB`, default `app`).
#   2. NEVER drop a target database without an explicit opt-in flag.
#   3. NEVER overwrite a destination file (backups are precious).
#   4. DEFAULT is to perform a real restore (--list opts out into a dry-run
#      that prints the archive TOC via `pg_restore --list` and exits 0).
#
# Modes
#   default                : perform a real restore. Requires --target-db.
#   --list                 : print the archive TOC and exit (no DB changes).
#                            Does NOT require --target-db.
#   --target-db NAME       : restore into the named DB. The DB must already
#                            exist unless --create-target is also given.
#   --create-target        : create the target DB if it does not exist
#                            (uses `createdb`; requires CREATEDB privilege).
#   --force                : acknowledge that the target DB may be dropped
#                            before restore. Without this flag, the script
#                            refuses to drop any database. NEVER allowed
#                            against the live app DB (see below).
#   --clean-before         : emit DROP ... statements before each CREATE
#                            (so the restore is idempotent inside the target).
#
# Safety recap
#   - Refuses to drop the live dev DB (POSTGRES_DB / `app` by default).
#   - Refuses to proceed in restore mode without --target-db.
#   - Refuses to restore into the live dev DB unless BOTH --force AND
#     ALLOW_LIVE_DB_RESTORE=1 are set.
#   - Does NOT print the password.
# -----------------------------------------------------------------------------

set -e
set -u
set -o pipefail

DB_NAME="${POSTGRES_DB:-app}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
TARGET_DB=""
ARCHIVE=""
FORCE=0
CREATE_TARGET=0
CLEAN_BEFORE=0
LIST_ONLY=0   # default: perform a real restore; pass --list to only print TOC

usage() {
    cat <<'USAGE'
Usage: db-restore.sh --archive PATH [--target-db NAME]
                    [--create-target] [--clean-before] [--force]
                    [--db NAME] [--user USER] [--host HOST] [--port PORT]

Defaults to RESTORE (perform a real restore). Pass --list to only print
the archive TOC and exit without touching any database.

  --archive PATH       Path to a *.dump file produced by db-backup.sh
                       (or any pg_dump -Fc archive).
  --list               Print the archive table of contents and exit.
                       Does NOT require --target-db.
  --target-db NAME     Database to restore into. MUST differ from the live
                       application DB unless --force is also given.
  --create-target      Create --target-db if it does not exist (uses createdb).
  --clean-before       Pass --clean to pg_restore (DROP before CREATE).
                       Useful when restoring over an existing test DB.
  --force              Allow drop-and-recreate of the target DB before
                       restore. NEVER allowed against the live app DB
                       unless ALLOW_LIVE_DB_RESTORE=1 is also set.

Environment overrides (non-secret):
  POSTGRES_DB          Live app DB name to protect (default: app)
  POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT: connection target for
                       the *server* (we connect to `postgres` to admin DBs).
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --archive)        ARCHIVE="$2"; shift 2 ;;
        --target-db)      TARGET_DB="$2"; shift 2 ;;
        --db)             DB_NAME="$2"; shift 2 ;;
        --user)           DB_USER="$2"; shift 2 ;;
        --host)           DB_HOST="$2"; shift 2 ;;
        --port)           DB_PORT="$2"; shift 2 ;;
        --create-target)  CREATE_TARGET=1; shift ;;
        --clean-before)   CLEAN_BEFORE=1; shift ;;
        --force)          FORCE=1; shift ;;
        --list)           LIST_ONLY=1; shift ;;
        -h|--help)        usage; exit 0 ;;
        *)
            echo "db-restore.sh: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

# ---- Pre-flight --------------------------------------------------------------
if [ -z "$ARCHIVE" ]; then
    echo "db-restore.sh: --archive is required." >&2
    usage >&2
    exit 2
fi
if [ ! -f "$ARCHIVE" ]; then
    echo "db-restore.sh: archive not found: $ARCHIVE" >&2
    exit 2
fi

# Verify it's actually a pg_dump custom-format archive by reading the magic
# header. This catches "I pointed at a stale or wrong file" early.
MAGIC="$(head -c 5 -- "$ARCHIVE" 2>/dev/null || true)"
if [ "$MAGIC" != "PGDMP" ]; then
    echo "db-restore.sh: file does not look like a pg_dump archive (no PGDMP header): $ARCHIVE" >&2
    exit 2
fi

# In list-only mode we don't need a target DB.
if [ "$LIST_ONLY" -eq 1 ]; then
    if ! command -v pg_restore >/dev/null 2>&1; then
        echo "db-restore.sh: pg_restore not found in PATH." >&2
        exit 127
    fi
    echo "db-restore.sh: listing archive contents (no DB changes)"
    pg_restore --list "$ARCHIVE"
    exit 0
fi

# Restore mode requires an explicit target.
if [ -z "$TARGET_DB" ]; then
    echo "db-restore.sh: --target-db is required for an actual restore." >&2
    usage >&2
    exit 2
fi

# Sanitize: only alnum + underscore (Postgres identifier rules + safety).
if printf '%s' "$TARGET_DB" | grep -qE '[^A-Za-z0-9_]'; then
    echo "db-restore.sh: --target-db must match [A-Za-z0-9_] (got: $TARGET_DB)" >&2
    exit 2
fi

# Refuse to operate on the live app DB unless --force is given, AND even
# then require an explicit operator override marker via an env var. This is
# belt-and-suspenders: a stale shell history or a copy-paste mistake must
# never silently destroy the working dev database.
if [ "$TARGET_DB" = "$DB_NAME" ]; then
    if [ "$FORCE" -ne 1 ]; then
        echo "db-restore.sh: refusing to restore into the live app DB ($DB_NAME)" >&2
        echo "  without --force. Use --target-db to pick a different database." >&2
        exit 1
    fi
    if [ "${ALLOW_LIVE_DB_RESTORE:-0}" != "1" ]; then
        echo "db-restore.sh: --force is set but the target is the live app DB." >&2
        echo "  Refusing to continue. Set ALLOW_LIVE_DB_RESTORE=1 only if you" >&2
        echo "  really mean to overwrite $DB_NAME." >&2
        exit 1
    fi
    echo "db-restore.sh: WARNING: --force + ALLOW_LIVE_DB_RESTORE=1 set; proceeding" >&2
    echo "  to restore into the live app DB. This will destroy its data." >&2
fi

if ! command -v pg_restore >/dev/null 2>&1; then
    echo "db-restore.sh: pg_restore not found in PATH." >&2
    exit 127
fi
if [ "$CREATE_TARGET" -eq 1 ] && ! command -v createdb >/dev/null 2>&1; then
    echo "db-restore.sh: --create-target requested but createdb is not in PATH." >&2
    exit 127
fi

# Connect to the maintenance DB (`postgres`) to enumerate / create / drop
# target DBs. Using the app DB itself for that is fragile.
ADMIN_DB="postgres"

# Helper: does the target DB exist?
db_exists() {
    psql \
        --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
        --dbname="$ADMIN_DB" --tuples-only --no-align --command \
        "SELECT 1 FROM pg_database WHERE datname = '$TARGET_DB'" \
        | grep -q '^1$'
}

# ---- Create target if requested ---------------------------------------------
if [ "$CREATE_TARGET" -eq 1 ]; then
    if db_exists; then
        echo "db-restore.sh: target DB already exists: $TARGET_DB (skipping create)"
    else
        echo "db-restore.sh: creating target DB: $TARGET_DB"
        createdb \
            --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
            "$TARGET_DB"
    fi
fi

# ---- Drop target if --force --------------------------------------------------
# Two paths reach here:
#   (a) --create-target was given: the target DB is now guaranteed to exist
#       and was created/claimed in this invocation. We restore into it as-is.
#   (b) --create-target was NOT given: the target DB may or may not exist.
#       If it exists, --force is required to drop-and-recreate; otherwise we
#       refuse (so an operator can't accidentally restore over a populated DB
#       they didn't mean to touch).
if [ "$CREATE_TARGET" -ne 1 ]; then
    if db_exists; then
        if [ "$FORCE" -ne 1 ]; then
            echo "db-restore.sh: target DB already exists: $TARGET_DB" >&2
            echo "  Pass --force to drop and recreate, --create-target to claim" >&2
            echo "  it, or pick a different name." >&2
            exit 1
        fi
        echo "db-restore.sh: --force: dropping target DB: $TARGET_DB"
        psql \
            --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
            --dbname="$ADMIN_DB" --command \
            "DROP DATABASE \"$TARGET_DB\""
        # Recreate it empty so pg_restore can populate it.
        createdb \
            --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
            "$TARGET_DB"
    elif [ "$FORCE" -eq 1 ]; then
        # --force with a non-existent DB is fine; we'll create it.
        echo "db-restore.sh: --force: target DB does not exist; creating: $TARGET_DB"
        createdb \
            --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
            "$TARGET_DB"
    fi
fi

# ---- Restore -----------------------------------------------------------------
EXTRA_ARGS=()
if [ "$CLEAN_BEFORE" -eq 1 ]; then
    EXTRA_ARGS+=(--clean)
fi

echo "db-restore.sh: restoring archive into $TARGET_DB"
echo "  archive : $ARCHIVE"
echo "  host    : $DB_HOST:$DB_PORT"
echo "  user    : $DB_USER"

# --no-owner / --no-privileges match what db-backup.sh emits. They make the
# restore succeed even when the source role doesn't exist on the target.
# Exit codes from pg_restore are tricky: a non-zero exit can mean warnings,
# not just failures. We treat a non-zero exit as a hard failure for the
# operator's safety.
set +e
pg_restore \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
    --dbname="$TARGET_DB" \
    --no-owner --no-privileges --exit-on-error \
    "${EXTRA_ARGS[@]}" \
    "$ARCHIVE"
rc=$?
set -e

if [ "$rc" -ne 0 ]; then
    echo "db-restore.sh: pg_restore exited with code $rc" >&2
    exit "$rc"
fi

# Sanity check: can we read something from the restored DB?
COUNT="$(psql \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
    --dbname="$TARGET_DB" --tuples-only --no-align --command \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" \
    | tr -d '[:space:]')"

if ! printf '%s' "$COUNT" | grep -qE '^[0-9]+$'; then
    echo "db-restore.sh: post-restore sanity check failed (could not count tables)." >&2
    exit 1
fi
echo "db-restore.sh: restore complete"
echo "  target : $TARGET_DB"
echo "  public tables : $COUNT"
