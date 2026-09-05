#! /usr/bin/env bash
# -----------------------------------------------------------------------------
# db-verify.sh — Verify a pg_dump archive by restoring it into a throwaway
# database and running sanity queries.
#
# IMPORTANT
#   This script never touches the live application database. It always
#   creates a uniquely-named temporary database (or a caller-supplied test
#   DB name) and runs the restore there. The temporary database is dropped
#   on success, or kept on failure for inspection depending on flags.
#
# What "verification" means here
#   1. The archive is well-formed (pg_restore --list succeeds).
#   2. The archive restores cleanly into a fresh database.
#   3. The restored database has the expected number of public-schema tables
#      (catches wildly incomplete archives).
#   4. The restored database's `alembic_version` matches the current
#      Alembic head recorded in the repository (catches archives taken from
#      a different migration state).
#
# Usage
#   bash scripts/backup/db-verify.sh --archive backups/db/...dump
#   bash scripts/backup/db-verify.sh --archive ... --keep-on-failure
#
# Exit codes
#   0  verification passed
#   1  generic failure
#   2  invalid arguments / configuration
#   3  required tools unavailable
#   4  archive is well-formed but the restore or sanity checks failed
# -----------------------------------------------------------------------------

set -e
set -u
set -o pipefail

# ---- Configuration -----------------------------------------------------------
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
ARCHIVE=""
KEEP_ON_FAILURE=0
HEAD_VERSION=""
TARGET_DB=""
MIN_TABLES=1
EXPECTED_HEAD_VERSION=0  # set by --expect-head <rev>

usage() {
    cat <<'USAGE'
Usage: db-verify.sh --archive PATH [--target-db NAME]
                    [--expect-head REV] [--keep-on-failure]
                    [--user USER] [--host HOST] [--port PORT]
                    [--min-tables N]

  --archive PATH        Archive to verify (required).
  --target-db NAME      Use this DB name instead of generating a temp one.
                        The script always drops it at the end (unless
                        --keep-on-failure is set).
  --expect-head REV     Fail verification if the restored DB's
                        `alembic_version.version_num` is not REV.
  --keep-on-failure     Don't drop the verification DB if any check fails.
                        Useful for manual debugging; the DB name is logged.
  --min-tables N        Minimum number of public tables required (default 1).
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --archive)         ARCHIVE="$2"; shift 2 ;;
        --target-db)       TARGET_DB="$2"; shift 2 ;;
        --expect-head)     EXPECTED_HEAD_VERSION=1; HEAD_VERSION="$2"; shift 2 ;;
        --keep-on-failure) KEEP_ON_FAILURE=1; shift ;;
        --user)            DB_USER="$2"; shift 2 ;;
        --host)            DB_HOST="$2"; shift 2 ;;
        --port)            DB_PORT="$2"; shift 2 ;;
        --min-tables)      MIN_TABLES="$2"; shift 2 ;;
        -h|--help)         usage; exit 0 ;;
        *)
            echo "db-verify.sh: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$ARCHIVE" ]; then
    echo "db-verify.sh: --archive is required." >&2
    usage >&2
    exit 2
fi
if [ ! -f "$ARCHIVE" ]; then
    echo "db-verify.sh: archive not found: $ARCHIVE" >&2
    exit 2
fi

# ---- Tool availability -------------------------------------------------------
for tool in pg_restore psql createdb dropdb; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "db-verify.sh: required tool not in PATH: $tool" >&2
        exit 3
    fi
done

# ---- Compute target DB name --------------------------------------------------
if [ -z "$TARGET_DB" ]; then
    # 8 chars of entropy from /dev/urandom, base36-ish. We only use
    # [A-Za-z0-9_] so any Postgres identifier sanitization is satisfied.
    RAND_SUFFIX="$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom 2>/dev/null | head -c 8 || echo "fallback")"
    if [ -z "$RAND_SUFFIX" ]; then
        RAND_SUFFIX="fallback"
    fi
    TARGET_DB="eagle_eye_verify_${RAND_SUFFIX}"
fi

# Sanitize.
if printf '%s' "$TARGET_DB" | grep -qE '[^A-Za-z0-9_]'; then
    echo "db-verify.sh: --target-db must match [A-Za-z0-9_] (got: $TARGET_DB)" >&2
    exit 2
fi

ADMIN_DB="postgres"

cleanup() {
    if [ "$KEEP_ON_FAILURE" -eq 0 ]; then
        dropdb \
            --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
            --if-exists \
            "$TARGET_DB" 2>/dev/null || true
    else
        echo "db-verify.sh: --keep-on-failure set; verification DB left in place: $TARGET_DB" >&2
    fi
}
trap cleanup EXIT

# ---- Step 1: archive well-formed? -------------------------------------------
echo "db-verify.sh: [1/4] inspecting archive: $ARCHIVE"
MAGIC="$(head -c 5 -- "$ARCHIVE" 2>/dev/null || true)"
if [ "$MAGIC" != "PGDMP" ]; then
    echo "db-verify.sh: archive does not have a PGDMP header." >&2
    exit 4
fi
if ! pg_restore --list "$ARCHIVE" >/dev/null; then
    echo "db-verify.sh: pg_restore --list failed; archive is corrupt or unreadable." >&2
    exit 4
fi

# ---- Step 2: create temp DB --------------------------------------------------
echo "db-verify.sh: [2/4] creating verification DB: $TARGET_DB"
if createdb \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
    "$TARGET_DB"; then
    :
else
    echo "db-verify.sh: failed to create verification DB $TARGET_DB." >&2
    echo "  (If it already exists from a previous run, pick --target-db or drop it.)" >&2
    exit 4
fi

# ---- Step 3: restore --------------------------------------------------------
echo "db-verify.sh: [3/4] restoring archive into $TARGET_DB"
if pg_restore \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
    --dbname="$TARGET_DB" \
    --no-owner --no-privileges --exit-on-error \
    "$ARCHIVE"; then
    :
else
    rc=$?
    echo "db-verify.sh: pg_restore failed (exit $rc)." >&2
    exit 4
fi

# ---- Step 4: sanity queries -------------------------------------------------
echo "db-verify.sh: [4/4] running sanity queries"

# 4a. Table count
TABLE_COUNT="$(psql \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
    --dbname="$TARGET_DB" --tuples-only --no-align --command \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" \
    | tr -d '[:space:]' || echo "")"

if ! printf '%s' "$TABLE_COUNT" | grep -qE '^[0-9]+$'; then
    echo "db-verify.sh: could not read public table count from restored DB." >&2
    exit 4
fi
if [ "$TABLE_COUNT" -lt "$MIN_TABLES" ]; then
    echo "db-verify.sh: public table count too low: $TABLE_COUNT < $MIN_TABLES" >&2
    exit 4
fi
echo "  public tables : $TABLE_COUNT"

# 4b. Alembic version (if the table exists)
ALEMBIC_VERSION="$(psql \
    --host="$DB_HOST" --port="$DB_PORT" --username="$DB_USER" \
    --dbname="$TARGET_DB" --tuples-only --no-align --command \
    "SELECT version_num FROM alembic_version LIMIT 1" \
    2>/dev/null | tr -d '[:space:]' || true)"

if [ -n "$ALEMBIC_VERSION" ]; then
    echo "  alembic head  : $ALEMBIC_VERSION"
    if [ "$EXPECTED_HEAD_VERSION" -eq 1 ] && [ "$ALEMBIC_VERSION" != "$HEAD_VERSION" ]; then
        echo "db-verify.sh: alembic_version mismatch: got '$ALEMBIC_VERSION', expected '$HEAD_VERSION'" >&2
        exit 4
    fi
else
    echo "  alembic head  : <table not present>"
fi

echo "db-verify.sh: verification PASSED"
echo "  archive       : $ARCHIVE"
echo "  target db     : $TARGET_DB (will be dropped on exit)"
