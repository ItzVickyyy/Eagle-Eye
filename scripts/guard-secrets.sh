#!/usr/bin/env bash
# Guard against tracking environment/secret files.
#
# Runs as a pre-commit local hook. Exits non-zero (blocking the commit) if any
# secret-bearing environment file is, or is being, added to Git tracking.
#
# Invariant: no real .env file should ever be tracked. Safe templates such as
# .env.example, .env.example.<env>, and .env.sample are allowed.
#
# Dependency-free by design: uses only core git + POSIX shell.

set -u

# A tracked file is a "secret env file" if:
#   - its basename is exactly ".env", OR
#   - its basename starts with ".env." and is NOT a known-safe template
#     (.env.example, .env.example.*, .env.sample).
is_bad_env() {
  local base
  base=$(basename "$1") || return 0
  case "$base" in
    .env) return 0 ;;                                        # real file, any dir
    .env.example|.env.example.*|.env.sample) return 1 ;;     # safe templates
    .env.*) return 0 ;;                                      # other real .env.*
    *) return 1 ;;
  esac
}

bad=0

# 1) Any already-tracked secret env file (independent of staged diffs).
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if is_bad_env "$f"; then
    echo "guard-secrets: tracked secret env file found: $f" >&2
    bad=1
  fi
done < <(git ls-files)

# 2) Secret env files force-added into the index (gitignored files can be staged
#    with `git add -f`, so check the index against HEAD as well).
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if is_bad_env "$f"; then
    echo "guard-secrets: staged addition of secret env file: $f" >&2
    bad=1
  fi
done < <(git diff --cached --name-only --diff-filter=A 2>/dev/null)

if [ "$bad" -ne 0 ]; then
  echo "guard-secrets: remove from tracking with 'git rm --cached <file>'." >&2
  echo "guard-secrets: keep only the .env.example templates (no real secrets)." >&2
  exit 1
fi

exit 0