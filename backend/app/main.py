from collections.abc import Awaitable, Callable
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

from app.api.main import api_router
from app.core.config import settings
from app.core.flags import MaintenanceModeMiddleware

FRONTEND_DIR = Path(__file__).parent / "frontend"
# Local upload directory. Resolved to an absolute path under the
# backend/ folder (Path(__file__).parent.parent == /app/backend/ in
# the container) so that a production deployment can mount a named
# volume at this exact path. See compose.deploy.yml: backend volume
# `app-uploads-data` mounted at /app/backend/uploads. The previous
# CWD-relative `uploads` was rejected because `docker compose run`
# and the long-running app container can have different CWDs
# depending on entrypoint behaviour, which silently split writes
# across container filesystems.
UPLOAD_DIR = Path(__file__).parent.parent / settings.MEDIA_STORAGE_LOCAL_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.FASTAPI_ENV != "development":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_HOST],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MaintenanceModeMiddleware)


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.include_router(api_router, prefix=settings.API_V1_STR)

if FRONTEND_DIR.exists():
    app.frontend("/", directory=FRONTEND_DIR)
