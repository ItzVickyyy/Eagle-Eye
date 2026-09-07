"""CAPTCHA client-IP resolution tests.

Mirrors the ``TestResolveClientIp`` suite for the rate limiter, but exercises
the CAPTCHA ``_client_ip`` → ``verify_captcha`` path.  Every test calls the
provider mock directly (``_verify_with_turnstile``) so no real Cloudflare
traffic is ever generated.

The primary regression under test is that an *untrusted* client who sends a
forged ``X-Forwarded-For`` header cannot influence the ``remoteip`` value
sent to Turnstile (previously at ``captcha.py:62-68``, unconditional XFF trust).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from fastapi import Request

from app.core.config import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _captcha_request(
    *,
    host: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
    token: str = "test-token-123",
) -> Request:
    """Build a ``fastapi.Request`` scoped for CAPTCHA verification.

    Unlike the rate-limiter helpers, the request carries a JSON body so that
    ``verify_captcha`` can extract the token from it.
    """
    scope: dict[str, Any] = {
        "type": "http",
        "path": "/api/v1/users/signup",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": (host, 12345),
    }

    async def _receive() -> dict[str, Any]:
        return {
            "type": "http.request",
            "body": json.dumps({"captcha_token": token}).encode(),
            "more_body": False,
        }

    return Request(scope, receive=_receive)


@pytest.fixture
def captcha_runtime() -> object:
    """Enable CAPTCHA verification for one test and restore on teardown.

    Uses direct attribute assignment (not ``monkeypatch.setattr``) because
    the pydantic Settings model raises ``AttributeError`` on ``getattr``
    for undeclared attributes, which monkeypatch relies on to save the old
    value.  This mirrors the ``captcha_enabled`` fixture in
    ``test_security_hardening.py``.
    """
    original_runtime = getattr(settings, "_captcha_runtime_required", False)
    original_secret = settings.TURNSTILE_SECRET_KEY
    settings._captcha_runtime_required = True  # type: ignore[attr-defined]
    if not settings.TURNSTILE_SECRET_KEY:
        settings.TURNSTILE_SECRET_KEY = "dummy-test-secret"
    try:
        yield
    finally:
        settings._captcha_runtime_required = original_runtime  # type: ignore[attr-defined]
        settings.TURNSTILE_SECRET_KEY = original_secret


def _capture_verification() -> tuple[dict[str, Any], Any]:
    """Return ``(store, fake_fn)``; ``store`` accumulates call kwargs."""
    store: dict[str, Any] = {}

    async def _fake(
        *, token: str, secret: str, remote_ip: str
    ) -> tuple[bool, None]:
        store["token"] = token
        store["secret"] = secret
        store["remote_ip"] = remote_ip
        return True, None

    return store, _fake


# ---------------------------------------------------------------------------
# Core spoofing regression
# ---------------------------------------------------------------------------


class TestCaptchaClientIp:
    """Verify ``captcha._client_ip`` delegates to the shared trusted-proxy model."""

    def test_untrusted_forged_xff_uses_direct_peer(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PRIMARY REGRESSION: an untrusted client must NOT be able to choose
        ``remoteip`` via a forged ``X-Forwarded-For`` header."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        req = _captcha_request(host="9.9.9.9", headers={"X-Forwarded-For": "1.2.3.4"})
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "9.9.9.9"

    def test_untrusted_peer_ignored_even_with_proxy_configured(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A client whose peer address is NOT in the trust list must have its
        ``X-Forwarded-For`` header ignored regardless of configuration."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["172.18.0.2"])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        req = _captcha_request(host="9.9.9.9", headers={"X-Forwarded-For": "1.2.3.4"})
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "9.9.9.9"

    # ------------------------------------------------------------------
    # Trusted-proxy cases
    # ------------------------------------------------------------------

    def test_trusted_proxy_uses_leftmost_valid_ip(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the direct peer IS trusted, the leftmost ``X-Forwarded-For``
        value is used as ``remoteip``."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["172.18.0.2"])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        req = _captcha_request(
            host="172.18.0.2",
            headers={"X-Forwarded-For": "203.0.113.5, 70.41.3.18"},
        )
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "203.0.113.5"

    def test_trusted_proxy_malformed_xff_falls_back_to_peer(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-IP leftmost forwarded value must be rejected."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["172.18.0.2"])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        req = _captcha_request(
            host="172.18.0.2",
            headers={"X-Forwarded-For": "evil-client, 1.2.3.4"},
        )
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "172.18.0.2"

    def test_trusted_proxy_missing_xff_uses_direct_peer(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the direct peer is trusted but no ``X-Forwarded-For`` is present
        the direct peer must be used."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["172.18.0.2"])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        req = _captcha_request(host="172.18.0.2")
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "172.18.0.2"

    def test_trusted_proxy_ipv6_peer_and_client(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IPv6 peer and client must both resolve correctly."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["::1"])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        req = _captcha_request(
            host="::1",
            headers={"X-Forwarded-For": "2001:db8::1"},
        )
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "2001:db8::1"

    def test_unknown_client_never_trusts_header(
        self, captcha_runtime: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``request.client`` is ``None``, ``remoteip`` must be
        ``"unknown"`` and no header must be honoured."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["anything"])
        from app.core.captcha import verify_captcha

        store, fake = _capture_verification()
        monkeypatch.setattr("app.core.captcha._verify_with_turnstile", fake)

        scope: dict[str, Any] = {
            "type": "http",
            "path": "/api/v1/users/signup",
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
            "client": None,
        }

        async def _receive() -> dict[str, Any]:
            return {
                "type": "http.request",
                "body": json.dumps({"captcha_token": "tok"}).encode(),
                "more_body": False,
            }

        req = Request(scope, receive=_receive)
        asyncio.run(verify_captcha(req))

        assert store["remote_ip"] == "unknown"

    # ------------------------------------------------------------------
    # Consistency: CAPTCHA and rate limiter agree
    # ------------------------------------------------------------------

    def test_captcha_ip_matches_rate_limit_identity(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``_client_ip`` must return the same value as ``_resolve_client_ip``
        for identical inputs, confirming the two subsystems agree."""
        from app.core.captcha import _client_ip
        from app.core.rate_limit import _resolve_client_ip

        req = _captcha_request(
            host="10.0.0.1",
            headers={"X-Forwarded-For": "5.5.5.5"},
        )

        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])
        assert _client_ip(req) == _resolve_client_ip(
            req, settings.RATE_LIMIT_TRUSTED_PROXIES
        )

        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", ["172.18.0.2"])
        assert _client_ip(req) == _resolve_client_ip(
            req, settings.RATE_LIMIT_TRUSTED_PROXIES
        )
