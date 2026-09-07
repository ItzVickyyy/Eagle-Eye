import asyncio
import logging
import os
from typing import Any
from unittest import mock

import pytest
from fastapi import HTTPException, Request

from app.core import rate_limit
from app.core.config import settings
from app.core.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    _client_key,
    _create_limiter,
    _limiters,
    _resolve_client_ip,
    _resolve_redis_url,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    host: str = "127.0.0.1",
    path: str = "/api/v1/articles/",
    headers: dict[str, str] | None = None,
) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (host, 12345),
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# _client_key (now honors RATE_LIMIT_TRUSTED_PROXIES)
# ---------------------------------------------------------------------------

class TestClientKey:
    def test_returns_ip_and_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])
        req = _make_request(host="10.0.0.1", path="/api/v1/login/")
        assert _client_key(req) == "10.0.0.1:/api/v1/login/"

    def test_ignores_forwarded_for_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With no trusted proxies, a forged X-Forwarded-For is ignored.

        This is the secure-by-default behavior: the operator must opt in
        to trusting forwarded headers by listing the upstream proxy in
        RATE_LIMIT_TRUSTED_PROXIES.
        """
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])
        req = _make_request(
            host="10.0.0.1",
            path="/",
            headers={"X-Forwarded-For": "203.0.113.5, 70.41.3.18"},
        )
        assert _client_key(req) == "10.0.0.1:/"

    def test_unknown_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])
        scope: dict[str, Any] = {"type": "http", "path": "/test", "headers": [], "client": None}
        request = Request(scope)
        assert _client_key(request) == "unknown:/test"


# ---------------------------------------------------------------------------
# InMemoryRateLimiter — sync internals
# ---------------------------------------------------------------------------

class TestInMemorySync:
    def test_reset(self) -> None:
        limiter = InMemoryRateLimiter(times=5, seconds=60)
        limiter._requests["k"] = [1.0, 2.0]
        limiter.reset()
        assert dict(limiter._requests) == {}

    def test_clean_old_entries(self) -> None:
        limiter = InMemoryRateLimiter(times=5, seconds=5)
        limiter._requests["k"] = [1.0, 5.0, 9.0]
        limiter._clean_old_entries(6.0)  # cutoff = 1.0, keeps > 1.0
        assert limiter._requests["k"] == [5.0, 9.0]

    def test_clean_removes_empty_keys(self) -> None:
        limiter = InMemoryRateLimiter(times=5, seconds=10)
        limiter._requests["k"] = [1.0]
        limiter._clean_old_entries(20.0)
        assert "k" not in limiter._requests


# ---------------------------------------------------------------------------
# InMemoryRateLimiter.__call__ (async, via asyncio.run)
# ---------------------------------------------------------------------------

class TestInMemoryAsync:
    def test_allows_requests_within_limit(self) -> None:
        limiter = InMemoryRateLimiter(times=3, seconds=60)
        limiter.force_enable_in_tests = True

        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}):
            for i in range(3):
                request = _make_request(host="10.0.0.1", path="/")
                with mock.patch("app.core.rate_limit.time") as time_mock:
                    time_mock.monotonic.return_value = float(i)
                    asyncio.run(limiter(request))

        assert len(limiter._requests["10.0.0.1:/"]) == 3

    def test_rejects_when_limit_exceeded(self) -> None:
        limiter = InMemoryRateLimiter(times=2, seconds=60)
        limiter.force_enable_in_tests = True

        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}):
            for i in range(2):
                request = _make_request(host="10.0.0.1", path="/")
                with mock.patch("app.core.rate_limit.time") as time_mock:
                    time_mock.monotonic.return_value = float(i)
                    asyncio.run(limiter(request))

            request = _make_request(host="10.0.0.1", path="/")
            with mock.patch("app.core.rate_limit.time") as time_mock:
                time_mock.monotonic.return_value = 2.0
                with pytest.raises(HTTPException) as exc:
                    asyncio.run(limiter(request))
            assert exc.value.status_code == 429

    def test_bypasses_when_disabled(self) -> None:
        limiter = InMemoryRateLimiter(times=1, seconds=60)
        limiter.enabled = False
        limiter.force_enable_in_tests = True

        request = _make_request(host="10.0.0.1", path="/")
        asyncio.run(limiter(request))
        asyncio.run(limiter(request))
        assert len(limiter._requests) == 0

    def test_bypasses_when_pytest_and_not_force_enabled(self) -> None:
        limiter = InMemoryRateLimiter(times=1, seconds=60)

        with mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test_something"}):
            request = _make_request(host="10.0.0.1", path="/")
            asyncio.run(limiter(request))
            asyncio.run(limiter(request))
            assert len(limiter._requests) == 0


# ---------------------------------------------------------------------------
# _create_limiter factory
# ---------------------------------------------------------------------------

class TestCreateLimiter:
    def test_returns_inmemory_when_no_redis(self) -> None:
        limiter = _create_limiter(times=10, seconds=30)
        assert isinstance(limiter, InMemoryRateLimiter)
        assert limiter.times == 10

    def test_returns_redis_when_url_provided(self) -> None:
        with mock.patch.dict(
            "sys.modules", {"redis": mock.MagicMock(), "redis.asyncio": mock.MagicMock()}
        ):
            limiter = _create_limiter(
                times=10, seconds=30, redis_url="redis://localhost:6379"
            )
        assert isinstance(limiter, RedisRateLimiter)


# ---------------------------------------------------------------------------
# Module-level pre-configured limiters
# ---------------------------------------------------------------------------

class TestModuleLimiters:
    def test_limiters_dict_keys(self) -> None:
        expected = {
            "login",
            "password_recovery",
            "password_reset",
            "signup",
            "contact",
            "comment",
        }
        assert set(_limiters.keys()) == expected

    def test_all_limiters_have_callable(self) -> None:
        for limiter in _limiters.values():
            assert callable(limiter)


# ---------------------------------------------------------------------------
# _resolve_client_ip — trusted-proxy decision tree
# ---------------------------------------------------------------------------

class TestResolveClientIp:
    def test_direct_ip_when_trust_list_empty(self) -> None:
        req = _make_request(host="10.0.0.1", headers={"X-Forwarded-For": "1.2.3.4"})
        assert _resolve_client_ip(req, []) == "10.0.0.1"

    def test_direct_ip_when_peer_not_trusted(self) -> None:
        req = _make_request(host="10.0.0.1", headers={"X-Forwarded-For": "1.2.3.4"})
        assert _resolve_client_ip(req, ["172.18.0.2"]) == "10.0.0.1"

    def test_uses_leftmost_when_peer_trusted(self) -> None:
        req = _make_request(
            host="172.18.0.2",
            headers={"X-Forwarded-For": "203.0.113.5, 70.41.3.18"},
        )
        assert _resolve_client_ip(req, ["172.18.0.2"]) == "203.0.113.5"

    def test_trims_whitespace_around_forwarded_value(self) -> None:
        req = _make_request(
            host="172.18.0.2",
            headers={"X-Forwarded-For": "  203.0.113.5  , 70.41.3.18"},
        )
        assert _resolve_client_ip(req, ["172.18.0.2"]) == "203.0.113.5"

    def test_falls_back_to_direct_ip_when_header_missing(self) -> None:
        req = _make_request(host="172.18.0.2")
        assert _resolve_client_ip(req, ["172.18.0.2"]) == "172.18.0.2"

    def test_falls_back_when_leftmost_not_an_ip(self) -> None:
        """A non-IP leftmost forwarded value must not be used as identity."""
        req = _make_request(
            host="172.18.0.2",
            headers={"X-Forwarded-For": "evil-client, 1.2.3.4"},
        )
        assert _resolve_client_ip(req, ["172.18.0.2"]) == "172.18.0.2"

    def test_falls_back_when_leftmost_empty(self) -> None:
        req = _make_request(
            host="172.18.0.2",
            headers={"X-Forwarded-For": ", 1.2.3.4"},
        )
        assert _resolve_client_ip(req, ["172.18.0.2"]) == "172.18.0.2"

    def test_accepts_ipv6_trusted_proxy(self) -> None:
        """Trusted-proxy match must work for IPv6 peers (and an IPv6 client)."""
        req = _make_request(
            host="::1",
            headers={"X-Forwarded-For": "2001:db8::1"},
        )
        assert _resolve_client_ip(req, ["::1"]) == "2001:db8::1"

    def test_unknown_client_never_trusts_header(self) -> None:
        scope: dict[str, Any] = {
            "type": "http",
            "path": "/",
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
            "client": None,
        }
        request = Request(scope)
        assert _resolve_client_ip(request, ["anything"]) == "unknown"


# ---------------------------------------------------------------------------
# _resolve_redis_url — Settings-driven, no env detour
# ---------------------------------------------------------------------------

class TestResolveRedisUrl:
    def test_none_when_settings_url_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", None)
        assert _resolve_redis_url() is None

    def test_none_when_settings_url_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "")
        assert _resolve_redis_url() is None

    def test_returns_settings_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "redis://redis:6379/0")
        assert _resolve_redis_url() == "redis://redis:6379/0"

    def test_uses_settings_object_not_os_environ(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An env var alone must not be enough; Settings is authoritative.

        This guards against the previous bug where the helper bypassed
        ``Settings.REDIS_URL`` and read ``os.environ`` directly.  If
        pydantic-settings had filtered/stripped a value out of the env,
        the helper would have silently used a different source of truth.
        """
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setattr(settings, "REDIS_URL", None)
        with mock.patch.dict(os.environ, {"REDIS_URL": "redis://spoofed:6379/0"}):
            assert _resolve_redis_url() is None


# ---------------------------------------------------------------------------
# RedisRateLimiter — fail-open logging on Redis outage
# ---------------------------------------------------------------------------

class TestRedisFailOpen:
    @pytest.fixture
    def redis_limiter(self) -> RedisRateLimiter:
        """Build a RedisRateLimiter with redis-py mocked.

        The constructor calls ``redis.asyncio.from_url`` and
        ``register_script``; both must be stubbed so the limiter can be
        instantiated without a real Redis server.  ``force_enable_in_tests``
        is set so the PYTEST_CURRENT_TEST guard does not short-circuit
        the limiter and the actual script / fail-open branch is exercised.
        """
        with mock.patch.dict(
            "sys.modules", {"redis": mock.MagicMock(), "redis.asyncio": mock.MagicMock()}
        ):
            limiter = RedisRateLimiter(
                times=5, seconds=60, redis_url="redis://localhost:6379/0"
            )
        limiter.force_enable_in_tests = True
        return limiter

    async def _raise(self, *_args: Any, **_kwargs: Any) -> Any:
        raise ConnectionError("simulated redis outage")

    async def _ok(self, *_args: Any, **_kwargs: Any) -> Any:
        return (1, 0)

    def test_logs_once_then_stays_silent_during_outage(
        self,
        redis_limiter: RedisRateLimiter,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """First failure logs; subsequent failures during the same outage do not."""
        request = _make_request(host="10.0.0.1", path="/")
        with (
            mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}),
            mock.patch.object(redis_limiter, "_script", new=self._raise),
            caplog.at_level(logging.WARNING, logger="app.core.rate_limit"),
        ):
            asyncio.run(redis_limiter(request))
            asyncio.run(redis_limiter(request))
            asyncio.run(redis_limiter(request))

        warnings = [
            r for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warnings) == 1
        assert "Redis rate limiting unavailable" in warnings[0].getMessage()

    def test_log_resets_on_recovery(
        self,
        redis_limiter: RedisRateLimiter,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A successful call clears the outage flag so a *new* failure logs again."""
        request = _make_request(host="10.0.0.1", path="/")
        with (
            mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}),
            caplog.at_level(logging.WARNING, logger="app.core.rate_limit"),
        ):
            # First outage: one warning.
            with mock.patch.object(redis_limiter, "_script", new=self._raise):
                asyncio.run(redis_limiter(request))
            # Recovery.
            with mock.patch.object(redis_limiter, "_script", new=self._ok):
                asyncio.run(redis_limiter(request))
            # Second outage: another warning.
            with mock.patch.object(redis_limiter, "_script", new=self._raise):
                asyncio.run(redis_limiter(request))

        warnings = [
            r for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warnings) == 2
        for record in warnings:
            assert "Redis rate limiting unavailable" in record.getMessage()

    def test_log_does_not_leak_redis_url_or_credentials(
        self,
        redis_limiter: RedisRateLimiter,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The warning must never include the URL or any embedded password."""
        request = _make_request(host="10.0.0.1", path="/")
        with (
            mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}),
            mock.patch.object(
                redis_limiter, "_script", new=self._raise
            ),
            caplog.at_level(logging.WARNING, logger="app.core.rate_limit"),
        ):
            asyncio.run(redis_limiter(request))

        # The literal string the limiter was constructed with.
        forbidden = "redis://localhost:6379/0"
        # The exception's repr (the URL won't appear here because
        # ConnectionError() didn't carry it, but assert defensively).
        for record in caplog.records:
            assert forbidden not in record.getMessage()
            assert forbidden not in str(record.exc_info)

    def test_failing_open_does_not_raise(
        self,
        redis_limiter: RedisRateLimiter,
    ) -> None:
        """When Redis is down the limiter must allow the request through."""
        request = _make_request(host="10.0.0.1", path="/")
        with (
            mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}),
            mock.patch.object(redis_limiter, "_script", new=self._raise),
        ):
            # No exception expected — the call returns None on failure.
            assert asyncio.run(redis_limiter(request)) is None

    def test_redis_limiter_uses_resolve_client_ip(
        self,
        redis_limiter: RedisRateLimiter,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The Redis key must be derived via the trusted-proxy resolver."""
        monkeypatch.setattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])
        captured: dict[str, Any] = {}

        async def _capture(keys: list[str], _args: list[int]) -> tuple[int, int]:
            captured["key"] = keys[0]
            return (1, 0)

        request = _make_request(
            host="10.0.0.1",
            path="/api/v1/login/",
            headers={"X-Forwarded-For": "203.0.113.5"},
        )
        with (
            mock.patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}),
            mock.patch.object(redis_limiter, "_script", new=_capture),
        ):
            asyncio.run(redis_limiter(request))

        # Trust list is empty, so the forged forwarded header is ignored.
        assert captured["key"] == "ratelimit:10.0.0.1:/api/v1/login/"


# ---------------------------------------------------------------------------
# Module-level _make_limiters honors Settings
# ---------------------------------------------------------------------------

class TestMakeLimitersUsesSettings:
    def test_in_memory_when_settings_redis_url_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", None)
        with mock.patch.dict(
            "sys.modules", {"redis": mock.MagicMock(), "redis.asyncio": mock.MagicMock()}
        ):
            limiters = rate_limit._make_limiters()
        assert type(limiters["login"]).__name__ == "InMemoryRateLimiter"

    def test_redis_when_settings_redis_url_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "REDIS_URL", "redis://redis:6379/0")
        with mock.patch.dict(
            "sys.modules", {"redis": mock.MagicMock(), "redis.asyncio": mock.MagicMock()}
        ):
            limiters = rate_limit._make_limiters()
        assert isinstance(limiters["login"], RedisRateLimiter)
