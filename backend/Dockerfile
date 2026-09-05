FROM oven/bun:1 AS frontend-build

WORKDIR /app

COPY package.json bun.lock /app/
COPY frontend/package.json /app/frontend/

WORKDIR /app/frontend

RUN bun install

COPY ./frontend /app/frontend

ARG VITE_API_URL=

RUN bun run build


FROM python:3.14

ENV PYTHONUNBUFFERED=1

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

WORKDIR /app/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --package app

COPY ./backend/scripts /app/backend/scripts

COPY ./backend/pyproject.toml ./backend/alembic.ini /app/backend/

COPY ./backend/app /app/backend/app

COPY --from=frontend-build /app/backend/app/frontend /app/backend/app/frontend

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --package app

WORKDIR /app/backend/

# Container-level healthcheck. Mirrors the `healthcheck:` block in
# compose.yml so plain `docker run` and non-compose orchestrators also get
# a real readiness signal (not just TCP port 8000). Uses the same endpoint
# the app exposes for this purpose: /api/v1/utils/health-check/. Uses
# python (already in the image) rather than installing curl, to keep the
# image lean.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/utils/health-check/', timeout=3).status == 200 else 1)"

# Entrypoint runs prestart (alembic upgrade head + initial data) before
# exec'ing the CMD. This closes the migration-race window for any deploy
# path (manual docker compose up, VPS cold start, fresh VPS rebuild).
# CI workflows that already invoke `docker compose run --rm backend bash
# scripts/prestart.sh` can opt out with SKIP_PRESTART=1.
COPY ./backend/scripts/entrypoint.sh /app/backend/scripts/entrypoint.sh
RUN chmod +x /app/backend/scripts/entrypoint.sh

ENTRYPOINT ["/app/backend/scripts/entrypoint.sh"]

CMD ["fastapi", "run", "--workers", "4"]
