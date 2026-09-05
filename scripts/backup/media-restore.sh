#! /usr/bin/env bash
# -----------------------------------------------------------------------------
# media-restore.sh — Extract a media-backup.sh tar.gz into a target directory.
#
# Safety
#   - Refuses to extract into the live MEDIA_STORAGE_LOCAL_DIR (uploads/) by
#     default. Use --target-dir to pick a different path, or pass --force
#     AND set ALLOW_LIVE_MEDIA_RESTORE=1 to override.
#   - Refuses to overwrite existing files unless --force is passed.
#   - The default mode is --list: prints the archive contents and exits 0.
# -----------------------------------------------------------------------------

set -e
set -u
set -o pipefail

SOURCE_DIR="${MEDIA_STORAGE_LOCAL_DIR:-uploads}"
ARCHIVE=""
TARGET_DIR=""
FORCE=0
LIST_ONLY=0

usage() {
    cat <<'USAGE'
Usage: media-restore.sh --archive PATH [--target-dir DIR]
                        [--source DIR] [--force] [--list]

Defaults to --list (print archive contents, no file changes).

  --archive PATH       Path to a *.tar.gz produced by media-backup.sh.
  --target-dir DIR     Directory to extract into. MUST differ from the
                       live media directory (MEDIA_STORAGE_LOCAL_DIR /
                       `uploads`) unless --force is given.
  --source DIR         Reference path for the live media dir, used to
                       compute the "live dir" guard. Default: uploads
  --force              Allow overwriting existing files AND allow writing
                       into the live media directory. The latter still
                       requires ALLOW_LIVE_MEDIA_RESTORE=1.
  --list               Print archive contents and exit (default).
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --archive)    ARCHIVE="$2"; shift 2 ;;
        --target-dir) TARGET_DIR="$2"; shift 2 ;;
        --source)     SOURCE_DIR="$2"; shift 2 ;;
        --force)      FORCE=1; shift ;;
        --list)       LIST_ONLY=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *)
            echo "media-restore.sh: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$ARCHIVE" ]; then
    echo "media-restore.sh: --archive is required." >&2
    usage >&2
    exit 2
fi
if [ ! -f "$ARCHIVE" ]; then
    echo "media-restore.sh: archive not found: $ARCHIVE" >&2
    exit 2
fi

# Resolve the "live" media dir to an absolute path for comparison.
case "$SOURCE_DIR" in
    /*) LIVE_DIR_ABS="$SOURCE_DIR" ;;
    *)  LIVE_DIR_ABS="$(pwd)/$SOURCE_DIR" ;;
esac

# Default mode: list.
if [ "$LIST_ONLY" -eq 0 ] && [ -z "$TARGET_DIR" ]; then
    LIST_ONLY=1
fi

if [ "$LIST_ONLY" -eq 1 ]; then
    echo "media-restore.sh: listing archive contents (no file changes)"
    tar -tzf "$ARCHIVE"
    exit 0
fi

# Resolve target to absolute path.
case "$TARGET_DIR" in
    /*) TARGET_DIR_ABS="$TARGET_DIR" ;;
    *)  TARGET_DIR_ABS="$(pwd)/$TARGET_DIR" ;;
esac

# Guard: don't write into the live media dir unless explicitly overridden.
if [ "$TARGET_DIR_ABS" = "$LIVE_DIR_ABS" ]; then
    if [ "$FORCE" -ne 1 ] || [ "${ALLOW_LIVE_MEDIA_RESTORE:-0}" != "1" ]; then
        echo "media-restore.sh: refusing to extract into the live media dir: $LIVE_DIR_ABS" >&2
        echo "  Pass --target-dir to pick a different path, or use --force and" >&2
        echo "  ALLOW_LIVE_MEDIA_RESTORE=1 to override (this will overwrite live media)." >&2
        exit 1
    fi
    echo "media-restore.sh: WARNING: extracting into the live media dir: $LIVE_DIR_ABS" >&2
fi

# Refuse to overwrite without --force.
TAR_FLAGS=()
if [ "$FORCE" -ne 1 ]; then
    TAR_FLAGS+=(--keep-old-files)
fi

if [ ! -d "$TARGET_DIR_ABS" ]; then
    mkdir -p "$TARGET_DIR_ABS"
fi

echo "media-restore.sh: extracting archive"
echo "  archive : $ARCHIVE"
echo "  target  : $TARGET_DIR_ABS"

tar -xzf "$ARCHIVE" "${TAR_FLAGS[@]}" -C "$TARGET_DIR_ABS"

# Tally what we extracted.
FILE_COUNT="$(tar -tzf "$ARCHIVE" 2>/dev/null | wc -l | tr -d '[:space:]')"
echo "media-restore.sh: extract complete (entries: $FILE_COUNT)"
