"""
Cloudflare Turnstile CAPTCHA verification for public submission endpoints.

This module is the single verification boundary for the four public submission
endpoints that must demonstrate a human presence (signup, password recovery,
password reset, and contact form). It is intentionally narrow:

- It uses Cloudflare Turnstile exclusively. The verify URL is hard-coded to
  the public Cloudflare endpoint and never derived from caller input, so
  there is no SSRF surface from user-supplied URLs.
- ``verify_captcha`` is a FastAPI dependency intended to run AFTER the
  per-endpoint rate limiter. This order is important: a rate limiter must
  reject burst traffic before any external network call, and the
  Turnstile provider will rate-limit a noisy IP at its own discretion, so
  pre-filtering at our edge keeps verifier load bounded.
- The dependency fails CLOSED in production: if ``CAPTCHA_ENABLED`` is
  true but the secret is missing, or the provider call errors out, the
  request is rejected with a 403. The test suite (and developers) keep
  ``CAPTCHA_ENABLED`` false to bypass verification entirely.
- Tokens and secrets are never logged. The dependency is wired so that
  caller-side errors do not propagate the raw token to client responses
  or to the audit log.

Configuration (see ``app.core.config``):
    CAPTCHA_ENABLED        - operator-facing on/off switch (default False).
    TURNSTILE_SITE_KEY    - public widget key, safe to expose to the SPA.
    TURNSTILE_SECRET_KEY  - server-side secret, never expose.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Hard-coded Turnstile verify endpoint. Never derive from caller input to
# eliminate SSRF. Documented at
# https://developers.cloudflare.com/turnstile/get-started/server-side-validation/.
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

# Conservative network budget. A real-world siteverify call typically
# completes in under a second; we leave a small buffer for transient
# slowness while keeping an upper bound that prevents a slow Turnstile
# outage from holding user requests open for many seconds.
_VERIFY_TIMEOUT_SECONDS = 5.0


def _is_required_now() -> bool:
    """Return whether the dependency must actively verify a token.

    Honors the runtime override ``settings._captcha_runtime_required`` so
    tests can force the verification path on without flipping the global
    ``CAPTCHA_ENABLED`` flag.
    """
    return bool(getattr(settings, "captcha_required", False))


def _client_ip(request: Request) -> str:
    """Mirror the rate-limiter keying so CAPTCHA failures can be audited."""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    return client_ip


async def _verify_with_turnstile(
    *,
    token: str,
    secret: str,
    remote_ip: str,
) -> tuple[bool, str | None]:
    """Call the Turnstile siteverify endpoint.

    Returns ``(ok, error_code)`` where ``error_code`` is one of the
    provider's error codes (``"timeout"``, ``"network"``, ``"invalid"``)
    or a normalized string we generated. The raw provider response is
    intentionally not returned; callers must not log it because it
    can contain diagnostic metadata we do not want to persist.
    """
    payload = {
        "secret": secret,
        "response": token,
        "remoteip": remote_ip,
    }
    try:
        async with httpx.AsyncClient(timeout=_VERIFY_TIMEOUT_SECONDS) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
    except httpx.TimeoutException:
        logger.warning("Turnstile verification timed out")
        return False, "timeout"
    except httpx.HTTPError:
        logger.warning("Turnstile verification transport error")
        return False, "network"

    if resp.status_code != 200:
        logger.warning(
            "Turnstile siteverify returned non-200 status: %s",
            resp.status_code,
        )
        return False, "provider_status"

    try:
        data = resp.json()
    except ValueError:
        logger.warning("Turnstile siteverify returned non-JSON body")
        return False, "invalid_response"

    if not isinstance(data, dict) or not data.get("success"):
        # Provider returns a list of error codes; we surface the first
        # one for the audit event but never the raw token.
        codes = data.get("error-codes") if isinstance(data, dict) else None
        if isinstance(codes, list) and codes:
            return False, str(codes[0])
        return False, "invalid"
    return True, None


async def verify_captcha(request: Request) -> None:
    """FastAPI dependency that enforces Cloudflare Turnstile verification.

    The dependency is intentionally permissive when CAPTCHA is disabled
    (default in test/dev) and is fail-closed when CAPTCHA is enabled but
    the secret is missing or the provider call fails. The token is
    expected in the JSON request body as ``captcha_token`` (preferred)
    or ``cf-turnstile-response`` (legacy Turnstile field name).
    """
    if not _is_required_now():
        return

    secret = settings.TURNSTILE_SECRET_KEY
    if not secret:
        # Fail closed: a deployment that opted in to CAPTCHA but forgot
        # to set the secret must NOT silently let traffic through.
        logger.error(
            "CAPTCHA_ENABLED but TURNSTILE_SECRET_KEY is not configured; "
            "rejecting request %s",
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA verification is misconfigured",
        )

    # Extract the token from the parsed body. FastAPI may or may not have
    # already parsed ``request.json()`` for the route's body model; the
    # value is cached on the request after the first read, so we can safely
    # call ``request.json()`` here. If a body model has not been declared
    # and the request has no body, we treat the token as missing.
    token: str | None = None
    try:
        body = await request.json()
    except Exception:
        body = None
    if isinstance(body, dict):
        for key in ("captcha_token", "cf-turnstile-response"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                token = value.strip()
                break

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA token is required",
        )

    remote_ip = _client_ip(request)
    ok, error_code = await _verify_with_turnstile(
        token=token,
        secret=secret,
        remote_ip=remote_ip,
    )
    if not ok:
        logger.info(
            "CAPTCHA verification failed for path=%s code=%s",
            request.url.path,
            error_code,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CAPTCHA verification failed",
        )
