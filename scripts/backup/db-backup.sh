#! /usr/bin/env bash
# -----------------------------------------------------------------------------
# db-backup.sh — Logical PostgreSQL backup of the Eagle Eye application DB.
#
# Strategy
#   - Uses `pg_dump` with the custom-format archive (-Fc) so output is
#     compressed by `pg_dump` itself and can be restored with `pg_restore`.
#   - The final artifact is a single `<name>-<UTC-timestamp>.dump` file. We do
#     NOT pipe through gzip on top of -Fc (the custom format is already
#     compressed); doing both wastes CPU.
#   - The timestamp is UTC ISO-8601 (compact) so files sort chronologically
#     and are unambiguous across operator timezones.
#   - Output goes under `backups/db/` (relative to the repo root by default)
#     unless `--output-dir` is supplied. The directory is created if missing.
#
# How to run
#   - Inside the compose stack (recommended for the dev DB):
#         docker compose exec -T db bash /app/scripts/backup/db-backup.sh
#     (mounting this script into the `db` service is left to the operator;
#      we do not change compose files in this implementation.)
#   - On a host that has `pg_dump` available and can reach the DB:
#         bash scripts/backup/db-backup.sh
#
# Safety
#   - Refuses to overwrite an existing file unless `--force` is passed.
#   - Refuses to write to an existing *directory* of the same name.
#   - Exits non-zero on any failure (set -e, set -u, set -o pipefail).
#   - Does NOT print the connection URL or any credential value. It may print
#     the database name and host (non-secret) and the dump filename.
#   - The `--dry-run` flag prints the resolved configuration and exits 0
#     without contacting the database. Use this to verify config first.
# -----------------------------------------------------------------------------

set -e
set -u
set -o pipefail

# ---- Defaults ----------------------------------------------------------------
DB_NAME="${POSTGRES_DB:-app}"
DB_USER="${POSTGRES_USER:-postgres}"
# PGPASSWORD is intentionally NOT read from .env by the script. The caller is
# responsible for providing it via the environment, an .pgpass file, or the
# compose service's user/role. We never echo the value.
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
OUTPUT_DIR="backups/db"
BACKUP_NAME="eagle-eye-db"
FORCE=0
DRY_RUN=0

usage() {
    cat <<'USAGE'
Usage: db-backup.sh [--db NAME] [--user USER] [--host HOST] [--port PORT]
                   [--output-dir DIR] [--name PREFIX] [--force] [--dry-run]

Environment overrides (non-secret):
  POSTGRES_DB     Database name to dump          (default: app)
  POSTGRES_USER   Role to connect as             (default: postgres)
  POSTGRES_HOST   Database host                  (default: localhost)
  POSTGRES_PORT   Database port                  (default: 5432)

Notes:
  - Provide the password via PGPASSWORD, a .pgpass entry, or the compose
    service's auth. The script never reads or prints the password.
  - The destination file is <output-dir>/<name>-<UTC-YYYYMMDDTHHMMSSZ>.dump
  - Refuses to overwrite an existing file unless --force is passed.
  - --dry-run prints the resolved config and exits without contacting the DB.
USAGE
}

# ---- Argument parsing --------------------------------------------------------
while [ "$#" -gt 0 ]; do
    case "$1" in
        --db)         DB_NAME="$2"; shift 2 ;;
        --user)       DB_USER="$2"; shift 2 ;;
        --host)       DB_HOST="$2"; shift 2 ;;
        --port)       DB_PORT="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --name)       BACKUP_NAME="$2"; shift 2 ;;
        --force)      FORCE=1; shift ;;
        --dry-run)    DRY_RUN=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)
            echo "db-backup.sh: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

# ---- Pre-flight validation ---------------------------------------------------
if [ -z "$DB_NAME" ]; then
    echo "db-backup.sh: refusing to run with empty database name." >&2
    exit 2
fi
if [ -z "$DB_USER" ]; then
    echo "db-backup.sh: refusing to run with empty database user." >&2
    exit 2
fi
if [ -z "$BACKUP_NAME" ]; then
    echo "db-backup.sh: refusing to run with empty backup name prefix." >&2
    exit 2
fi

# Sanitize the prefix: alnum, dash, underscore, dot only. This avoids path
# traversal and shell-metacharacter surprises when the name is interpolated.
if printf '%s' "$BACKUP_NAME" | grep -qE '[^A-Za-z0-9._-]'; then
    echo "db-backup.sh: --name must match [A-Za-z0-9._-] (got: $BACKUP_NAME)" >&2
    exit 2
fi

# Resolve output directory to an absolute path so error messages are
# unambiguous and to ensure we don't accidentally follow a symlink elsewhere.
case "$OUTPUT_DIR" in
    /*) OUTPUT_DIR_ABS="$OUTPUT_DIR" ;;
    *)  OUTPUT_DIR_ABS="$(pwd)/$OUTPUT_DIR" ;;
esac

if [ -e "$OUTPUT_DIR_ABS" ] && [ ! -d "$OUTPUT_DIR_ABS" ]; then
    echo "db-backup.sh: output path exists and is not a directory: $OUTPUT_DIR_ABS" >&2
    exit 2
fi

# Generate the timestamp and the final file path.
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$OUTPUT_DIR_ABS/${BACKUP_NAME}-${TS}.dump"

if [ -e "$DEST" ] && [ "$FORCE" -ne 1 ]; then
    echo "db-backup.sh: destination already exists, refusing to overwrite: $DEST" >&2
    echo "db-backup.sh: re-run with --force to overwrite." >&2
    exit 1
fi

# ---- Dry-run -----------------------------------------------------------------
if [ "$DRY_RUN" -eq 1 ]; then
    cat <<EOF
db-backup.sh: dry-run
  DB host     : $DB_HOST
  DB port     : $DB_PORT
  DB name     : $DB_NAME
  DB user     : $DB_USER
  Output dir  : $OUTPUT_DIR_ABS
  Output file : $DEST
  Force       : $FORCE
  pg_dump     : $(command -v pg_dump || echo '<not found in PATH>')
EOF
    exit 0
fi

# ---- Pre-flight: is pg_dump available? ---------------------------------------
if ! command -v pg_dump >/dev/null 2>&1; then
    echo "db-backup.sh: pg_dump is not installed or not in PATH." >&2
    echo "db-backup.sh: install PostgreSQL client tools, or run this script" >&2
    echo "db-backup.sh: from inside the compose 'db' service (image: postgres:18)." >&2
    exit 127
fi

# ---- Run ---------------------------------------------------------------------
mkdir -p "$OUTPUT_DIR_ABS"

echo "db-backup.sh: starting logical backup"
echo "  db     : $DB_NAME"
echo "  host   : $DB_HOST:$DB_PORT"
echo "  user   : $DB_USER"
echo "  output : $DEST"

# We deliberately do NOT pass --no-password: we want pg_dump to fail loudly
# if no usable auth method is configured (env, .pgpass, peer, etc.) rather
# than silently producing an empty dump.
#
# -Fc : custom archive format (compressed by pg_dump; restore with pg_restore)
# -Z 0: disable the additional zlib layer; -Fc is already compressed. This
#        keeps CPU usage low without inflating the output size.
pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --dbname="$DB_NAME" \
    --format=custom \
    --compress=0 \
    --no-owner \
    --no-privileges \
    --file="$DEST"

# Verify the artifact is non-empty. `pg_dump` exits non-zero on failure
# (set -e), so reaching this line is a good sign — but an empty file would
# still be a silent failure if the output was truncated.
if [ ! -s "$DEST" ]; then
    echo "db-backup.sh: backup file is empty or missing after pg_dump: $DEST" >&2
    rm -f "$DEST"
    exit 1
fi

SIZE_BYTES="$(wc -c <"$DEST" | tr -d '[:space:]')"
echo "db-backup.sh: backup complete"
echo "  file  : $DEST"
echo "  bytes : $SIZE_BYTES"

# Tighten permissions on the artifact. Backups may contain PII (user
# emails, password hashes, contact messages); default umask is too permissive.
chmod 600 "$DEST" 2>/dev/null || true
