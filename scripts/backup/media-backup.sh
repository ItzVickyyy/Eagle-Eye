#! /usr/bin/env bash
# -----------------------------------------------------------------------------
# media-backup.sh — Archive the local media directory (uploads) into a single
# .tar.gz file.
#
# What this covers
#   - Local filesystem media backend only.
#   - Default path: `<repo>/uploads/` (matching the dev default in compose).
#   - Configurable via --source DIR, --output-dir DIR, --name PREFIX.
#
# What this does NOT cover
#   - S3-compatible object storage. Those backups are the responsibility of
#     the storage provider (R2, B2, S3, MinIO). See docs/BACKUP_RECOVERY.md.
#
# Safety
#   - Refuses to overwrite an existing file unless --force is passed.
#   - Verifies the resulting archive is non-empty.
#   - Tightens permissions on the artifact (chmod 600).
# -----------------------------------------------------------------------------

set -e
set -u
set -o pipefail

SOURCE_DIR="${MEDIA_STORAGE_LOCAL_DIR:-uploads}"
OUTPUT_DIR="backups/media"
BACKUP_NAME="eagle-eye-media"
FORCE=0
DRY_RUN=0

usage() {
    cat <<'USAGE'
Usage: media-backup.sh [--source DIR] [--output-dir DIR] [--name PREFIX]
                       [--force] [--dry-run]

Environment overrides:
  MEDIA_STORAGE_LOCAL_DIR   Source directory (default: uploads)

Notes:
  - Output file: <output-dir>/<name>-<UTC-YYYYMMDDTHHMMSSZ>.tar.gz
  - Refuses to overwrite an existing file unless --force is passed.
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --source)     SOURCE_DIR="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --name)       BACKUP_NAME="$2"; shift 2 ;;
        --force)      FORCE=1; shift ;;
        --dry-run)    DRY_RUN=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)
            echo "media-backup.sh: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

# Sanitize the prefix.
if printf '%s' "$BACKUP_NAME" | grep -qE '[^A-Za-z0-9._-]'; then
    echo "media-backup.sh: --name must match [A-Za-z0-9._-] (got: $BACKUP_NAME)" >&2
    exit 2
fi

# Resolve source dir to an absolute path so error messages are unambiguous.
case "$SOURCE_DIR" in
    /*) SOURCE_DIR_ABS="$SOURCE_DIR" ;;
    *)  SOURCE_DIR_ABS="$(pwd)/$SOURCE_DIR" ;;
esac

if [ ! -d "$SOURCE_DIR_ABS" ]; then
    echo "media-backup.sh: source directory not found: $SOURCE_DIR_ABS" >&2
    exit 2
fi

# Resolve output dir.
case "$OUTPUT_DIR" in
    /*) OUTPUT_DIR_ABS="$OUTPUT_DIR" ;;
    *)  OUTPUT_DIR_ABS="$(pwd)/$OUTPUT_DIR" ;;
esac

if [ -e "$OUTPUT_DIR_ABS" ] && [ ! -d "$OUTPUT_DIR_ABS" ]; then
    echo "media-backup.sh: output path exists and is not a directory: $OUTPUT_DIR_ABS" >&2
    exit 2
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$OUTPUT_DIR_ABS/${BACKUP_NAME}-${TS}.tar.gz"

if [ -e "$DEST" ] && [ "$FORCE" -ne 1 ]; then
    echo "media-backup.sh: destination already exists, refusing to overwrite: $DEST" >&2
    echo "media-backup.sh: re-run with --force to overwrite." >&2
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
    cat <<EOF
media-backup.sh: dry-run
  source    : $SOURCE_DIR_ABS
  output dir: $OUTPUT_DIR_ABS
  output    : $DEST
  force     : $FORCE
  tar       : $(command -v tar || echo '<not found in PATH>')
EOF
    exit 0
fi

if ! command -v tar >/dev/null 2>&1; then
    echo "media-backup.sh: tar not found in PATH." >&2
    exit 127
fi

mkdir -p "$OUTPUT_DIR_ABS"

echo "media-backup.sh: archiving local media"
echo "  source : $SOURCE_DIR_ABS"
echo "  output : $DEST"

# We use -C so the archive is rooted at the basename of the source directory
# (typically `uploads/`), keeping paths short and portable across hosts.
SOURCE_BASENAME="$(basename "$SOURCE_DIR_ABS")"
SOURCE_PARENT="$(dirname "$SOURCE_DIR_ABS")"

tar -czf "$DEST" -C "$SOURCE_PARENT" "$SOURCE_BASENAME"

if [ ! -s "$DEST" ]; then
    echo "media-backup.sh: resulting archive is empty or missing: $DEST" >&2
    rm -f "$DEST"
    exit 1
fi

# Count files in the archive (informational).
FILE_COUNT="$(tar -tzf "$DEST" 2>/dev/null | wc -l | tr -d '[:space:]')"
SIZE_BYTES="$(wc -c <"$DEST" | tr -d '[:space:]')"

echo "media-backup.sh: backup complete"
echo "  file       : $DEST"
echo "  bytes      : $SIZE_BYTES"
echo "  file count : $FILE_COUNT"

chmod 600 "$DEST" 2>/dev/null || true
