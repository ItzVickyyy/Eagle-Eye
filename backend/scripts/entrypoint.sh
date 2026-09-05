#!/usr/bin/env bash
# Container entrypoint for the FastAPI backend.
#
# Goal: guarantee that the long-running app container never starts serving
# HTTP traffic before database migrations have been applied. The previous
# setup relied on the `deploy-docker-compose.yml` workflow running
# `docker compose run --rm backend bash scripts/prestart.sh` as a separate
# one-shot container before `up -d`, which left a window where a manual
# `docker compose up -d` (or any non-CI deploy) could boot the app against
# an unmigrated schema.
#
# This entrypoint runs prestart in-process, then exec's the CMD so it
# becomes PID 1 and receives signals (SIGTERM) from the orchestrator.
#
# Skip with `SKIP_PRESTART=1` for CI runs that already ran prestart
# explicitly (e.g. test-docker-compose, deploy-docker-compose).

set -e
set -x

if [[ "${SKIP_PRESTART:-0}" != "1" ]]; then
    echo "[entrypoint] running prestart: alembic upgrade head + initial data"
    bash "$(dirname "$0")/prestart.sh"
else
    echo "[entrypoint] SKIP_PRESTART=1, skipping prestart"
fi

echo "[entrypoint] starting: $*"
exec "$@"
