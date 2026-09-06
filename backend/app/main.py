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
from app.core.db import engine
from app.core.flags import MaintenanceModeMiddleware
from app.core.token_store import prune_revocations

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


"""
Content Security Policy for Eagle Eye.

Scope
-----
- The SPA serves its JS bundle from ``/assets/`` on the same origin as the
  API, so ``default-src 'self'`` covers the bulk of traffic.
- The rich-text editor (``RichTextEditor.tsx``) lets administrators paste
  arbitrary ``http://``, ``https://``, or root-relative URLs into article
  bodies. To keep that capability without explicitly allow-listing the open
  web in script/style contexts, ``img-src`` and ``media-src`` permit any
  HTTPS source, while ``connect-src`` and ``script-src`` stay restricted to
  the same origin.
- ``style-src 'unsafe-inline'`` is required for inline ``style={...}``
  attributes used by Radix/Sonner UI components. A future iteration can
  replace this with hashes or nonces if inline-style usage is removed.
- ``frame-src 'self'`` permits only same-origin framing; no third-party
  iframe embedding is used.
- Sentry is used server-side only; there is no browser-side Sentry
  integration.
"""

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://challenges.cloudflare.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; "
    "media-src 'self' blob: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://challenges.cloudflare.com; "
    "frame-src 'self' https://challenges.cloudflare.com; "
    "worker-src 'self' blob:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

PERMISSIONS_POLICY = (
    "camera=(), "
    "microphone=(), "
    "geolocation=(), "
    "payment=(), "
    "usb=(), "
    "interest-cohort=(), "
    "accelerometer=(), "
    "gyroscope=(), "
    "magnetometer=(), "
    "fullscreen=(self)"
)

# One year in seconds. ``includeSubDomains``/``preload`` are deliberately
# omitted: the deployment has no evidence of owning a registrable domain or
# running TLS on every subdomain, so setting them could brick unrelated
# subdomains or get the apex listed on the HSTS preload list by mistake.
HSTS_MAX_AGE_SECONDS = 31_536_000


def _is_https(request: Request) -> bool:
    """Return True when the request reached us over a TLS-protected transport.

    Honors a trusted ``X-Forwarded-Proto`` header so the value is correct
    behind a TLS-terminating reverse proxy in production. Plain-HTTP clients
    (notably the local dev server and the test client) never receive HSTS.
    """
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto is not None and forwarded_proto.split(",")[0].strip().lower() == "https":
        return True
    return False


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["Permissions-Policy"] = PERMISSIONS_POLICY
    if _is_https(request):
        response.headers["Strict-Transport-Security"] = (
            f"max-age={HSTS_MAX_AGE_SECONDS}"
        )
    return response


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def _prune_expired_token_revocations() -> None:
    """Drop stale ``token_revocations`` rows on application start.

    Rows with ``expires_at <= now()`` are no longer authoritative, but
    keeping them around bloats the table; the hot path already filters
    on ``expires_at > now()`` so this is purely a GC pass. Failures are
    logged and swallowed so a transient DB issue at startup does not
    prevent the app from booting.
    """
    import logging

    from sqlmodel import Session

    log = logging.getLogger(__name__)
    try:
        with Session(engine) as session:
            prune_revocations(session)
    except Exception:  # pragma: no cover - best-effort GC
        log.exception("Token revocation startup prune failed")

if FRONTEND_DIR.exists():
    app.frontend("/", directory=FRONTEND_DIR)
