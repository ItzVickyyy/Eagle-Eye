"""
Developer feature-flag enforcement.

This module is the single runtime enforcement boundary for the Developer
feature-flag set (P0/P1 scope of Implementation 17). It is intentionally
narrow:

- It reads the existing ``site_setting`` table. No new tables, columns, or
  migrations are introduced.
- It exposes reusable FastAPI dependencies that short-circuit a public
  submission endpoint when the corresponding flag is disabled.
- It exposes ``MaintenanceModeMiddleware``, a Starlette middleware that
  blocks public traffic when ``dev_maintenance_mode`` is enabled while
  keeping authentication, developer tooling, docs, health checks, and
  uploaded static assets reachable so internal teams can still operate the
  service during a maintenance window.
- It never allows the flag value to be overridden via query parameter; the
  only authoritative source is the database row.

The flag keys here match the constants in
``backend/app/api/routes/developer.py`` and the Developer dashboard.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.api.deps import get_db
from app.core.audit import write_audit_log
from app.models import SiteSetting

logger = logging.getLogger(__name__)


# Flag keys (must stay aligned with backend/app/api/routes/developer.py).
FLAG_MAINTENANCE_MODE = "dev_maintenance_mode"
FLAG_PUBLIC_COMMENTS_ENABLED = "dev_public_comments_enabled"
FLAG_CONTACT_FORM_ENABLED = "dev_contact_form_enabled"
FLAG_ALLOW_PUBLIC_SIGNUP = "dev_allow_public_signup"


# Public, non-sensitive default values used when the site_setting row is
# missing. They mirror the defaults in
# ``backend/app/api/routes/developer.py`` so an absent row reads as "on".
DEFAULT_FLAG_VALUES: dict[str, bool] = {
    FLAG_MAINTENANCE_MODE: False,
    FLAG_PUBLIC_COMMENTS_ENABLED: True,
    FLAG_CONTACT_FORM_ENABLED: True,
    FLAG_ALLOW_PUBLIC_SIGNUP: True,
}


# Paths that are always reachable even when maintenance mode is on. The list
# is intentionally explicit and small: anything not listed is treated as
# public traffic and blocked during maintenance.
_MAINTENANCE_ALLOWLIST_PREFIXES: tuple[str, ...] = (
    # Authentication must remain available so developers/admins can sign in
    # while the public site is offline.
    "/api/v1/login/",
    "/api/v1/password-recovery",
    "/api/v1/reset-password",
    # Developer tooling and audit surfaces.
    "/api/v1/developer/",
    # OpenAPI / docs for the operator running the deployment.
    # ``FastAPI`` is configured with ``openapi_url=f"{API_V1_STR}/openapi.json"``,
    # so the served path is ``/api/v1/openapi.json``. ``/docs`` and ``/redoc``
    # remain at the root (FastAPI defaults). Listing non-served paths would
    # silently 503 them during a maintenance window.
    "/api/v1/openapi.json",
    "/docs",
    "/redoc",
    # Health and system utilities.
    "/api/v1/utils/",
    # Public site settings (used by the SPA to render banners/feature
    # toggles). Kept reachable so the maintenance notice itself can be
    # served.
    "/api/v1/settings/",
    # Uploaded media and the static frontend (so the SPA can render the
    # operator-facing maintenance notice).
    "/uploads",
    "/assets",
    "/favicon.ico",
)


def read_flag(session: Session, key: str, default: bool) -> bool:
    """Return the current boolean value of a feature flag.

    Reads the ``site_setting`` table. The comparison is intentionally
    permissive (matches ``"true" | "1" | "yes"`` case-insensitively) so a
    human-edited row still works. On any unexpected error the function falls
    back to ``default`` so a transient DB issue does not lock public traffic
    out.
    """
    try:
        setting = session.get(SiteSetting, key)
    except Exception:  # pragma: no cover - defensive only
        logger.exception("Failed to read feature flag %s", key)
        return default
    if setting is None or setting.value is None:
        return default
    return setting.value.strip().lower() in ("true", "1", "yes")


def _is_allowed_in_maintenance(path: str) -> bool:
    """Return True when a request path may proceed during maintenance."""
    if path in _MAINTENANCE_ALLOWLIST_PREFIXES:
        return True
    for prefix in _MAINTENANCE_ALLOWLIST_PREFIXES:
        if prefix.endswith("/") and path.startswith(prefix):
            return True
    # Root path renders the SPA shell so the maintenance page can be shown.
    if path in ("/", ""):
        return True
    return False


def is_maintenance_active(session: Session) -> bool:
    """Convenience helper used by route-level enforcement deps."""
    return read_flag(session, FLAG_MAINTENANCE_MODE, False)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def enforce_public_comments_enabled(
    session: Session = Depends(get_db),
) -> None:
    """Block public comment submission when the flag is disabled."""
    if not read_flag(session, FLAG_PUBLIC_COMMENTS_ENABLED, True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public comments are temporarily disabled",
        )


def enforce_contact_form_enabled(
    session: Session = Depends(get_db),
) -> None:
    """Block public contact submissions when the flag is disabled."""
    if not read_flag(session, FLAG_CONTACT_FORM_ENABLED, True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The contact form is temporarily disabled",
        )


def enforce_public_signup_enabled(
    session: Session = Depends(get_db),
) -> None:
    """Block public account creation when the flag is disabled."""
    if not read_flag(session, FLAG_ALLOW_PUBLIC_SIGNUP, True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public sign-up is temporarily disabled",
        )


def enforce_maintenance_mode_disabled(
    session: Session = Depends(get_db),
) -> None:
    """Block public submission routes during a maintenance window.

    The maintenance middleware already blocks raw HTTP traffic for most public
    endpoints, but this dependency acts as a defense-in-depth check for any
    route that wants to refuse public writes explicitly.
    """
    if is_maintenance_active(session):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is in maintenance mode",
        )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Return 503 for public traffic when maintenance mode is on.

    Auth, developer tooling, docs, health, site settings, and uploaded
    static assets are always allowed so internal teams can still operate the
    service while the public site is offline. Public writes are also
    short-circuited at this layer so the maintenance window applies even if
    a future route forgets to opt in.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if _is_allowed_in_maintenance(path):
            return await call_next(request)

        # Open a short-lived session to read the flag. We intentionally do
        # not cache: a developer toggling the flag should take effect on the
        # next request.
        try:
            from app.core.db import engine  # local import to avoid cycles

            with Session(engine) as session:
                active = is_maintenance_active(session)
        except Exception:  # pragma: no cover - defensive only
            logger.exception("Failed to evaluate maintenance mode")
            return await call_next(request)

        if not active:
            return await call_next(request)

        # Best-effort audit trail for blocked public traffic. We swallow any
        # error: the user-facing 503 must always be returned.
        try:
            from app.core.db import engine

            with Session(engine) as session:
                write_audit_log(
                    session=session,
                    event="system.maintenance_block",
                    component="system",
                    severity="WARN",
                    success=False,
                    target_type="http",
                    target_id=path,
                    message=f"Blocked public request during maintenance: {path}",
                )
                session.commit()
        except Exception:  # pragma: no cover - defensive only
            logger.exception("Failed to audit maintenance block")

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service is in maintenance mode"},
        )
