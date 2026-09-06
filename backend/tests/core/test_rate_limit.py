import asyncio
import os
from typing import Any
from unittest import mock

import pytest
from fastapi import HTTPException, Request

from app.core.rate_limit import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    _client_key,
    _create_limiter,
    _limiters,
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
# _client_key
# ---------------------------------------------------------------------------

class TestClientKey:
    def test_returns_ip_and_path(self) -> None:
        req = _make_request(host="10.0.0.1", path="/api/v1/login/")
        assert _client_key(req) == "10.0.0.1:/api/v1/login/"

    def test_uses_forwarded_for(self) -> None:
        req = _make_request(
            host="10.0.0.1",
            path="/",
            headers={"X-Forwarded-For": "203.0.113.5, 70.41.3.18"},
        )
        assert _client_key(req) == "203.0.113.5:/"

    def test_unknown_client(self) -> None:
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
