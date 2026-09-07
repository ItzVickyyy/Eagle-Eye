from __future__ import annotations

import ipaddress
import logging
import os
import threading
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.core.config import settings

if TYPE_CHECKING:
    import redis.asyncio as aioredis


logger = logging.getLogger(__name__)


_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
local count = redis.call("ZCARD", key)
if count >= limit then
    return {0, redis.call("PTTL", key)}
end
redis.call("ZADD", key, now, now .. '-' .. math.random())
redis.call("PEXPIRE", key, window)
return {1, 0}
"""


def _resolve_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    """Return the rate-limit identity for ``request``.

    The decision tree:

    * If the immediate socket peer is not in ``trusted_proxies`` (or the
      request has no peer), ``X-Forwarded-For`` is ignored entirely.  This
      prevents a direct client from choosing an arbitrary rate-limit
      identity by sending a forged forwarded header.
    * If the immediate socket peer IS a trusted proxy, ``X-Forwarded-For``
      is consulted: the leftmost value is taken (the original client
      according to the conventional append-only forwarded chain), but it
      must parse as a valid IPv4 or IPv6 address.  Anything malformed
      (non-IP, empty, garbage) is rejected and the direct peer is used.
    """
    direct_ip = request.client.host if request.client else "unknown"
    if direct_ip == "unknown" or direct_ip not in trusted_proxies:
        return direct_ip
    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return direct_ip
    candidate = forwarded_for.split(",")[0].strip()
    if not candidate:
        return direct_ip
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return direct_ip
    return candidate


def _client_key(request: Request) -> str:
    """Return a rate-limit key scoped to client IP + request path.

    Honors the operator-configured ``RATE_LIMIT_TRUSTED_PROXIES`` list; see
    :func:`_resolve_client_ip` for the trust rules.
    """
    client_ip = _resolve_client_ip(request, settings.RATE_LIMIT_TRUSTED_PROXIES)
    return f"{client_ip}:{request.url.path}"


class InMemoryRateLimiter:
    """Thread-safe in-memory rate limiter using a sliding window per client IP."""

    def __init__(self, times: int = 20, seconds: int = 60) -> None:
        self.times = times
        self.seconds = seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self.enabled = True
        self.force_enable_in_tests = False

    def _clean_old_entries(self, now: float) -> None:
        cutoff = now - self.seconds
        for key in list(self._requests.keys()):
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]
            if not self._requests[key]:
                del self._requests[key]

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()

    async def __call__(self, request: Request) -> None:
        if not self.enabled:
            return

        # In general pytest runs, avoid false-positive rate limit blocks across suite runs.
        # Dedicated rate-limiting tests can set force_enable_in_tests=True.
        if os.getenv("PYTEST_CURRENT_TEST") and not self.force_enable_in_tests:
            return

        key = _client_key(request)
        now = time.monotonic()

        with self._lock:
            cutoff = now - self.seconds
            self._requests[key] = [t for t in self._requests[key] if t > cutoff]

            if len(self._requests[key]) >= self.times:
                oldest = self._requests[key][0]
                retry_after = max(1, int(self.seconds - (now - oldest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

            self._requests[key].append(now)


class RedisRateLimiter:
    """Redis-backed sliding-window rate limiter shared across workers.

    Uses an atomic Lua script for consistency.  Falls back to returning a
    `429` only when Redis itself is reachable; if Redis is down the *caller*
    (`create_rate_limiter`) returns an ``InMemoryRateLimiter`` instead, so
    this class is never instantiated when Redis is unavailable.
    """

    def __init__(self, times: int, seconds: int, redis_url: str) -> None:
        self.times = times
        self.seconds = seconds
        self._prefix = "ratelimit"
        # Used to log the Redis-unavailable transition at most once per
        # outage per process; redis-py lazily connects so the only signal
        # we get is the first failed command.  Resetting on a successful
        # call allows a future outage to be logged again.
        self._unavailable_logged = False
        import redis.asyncio as aioredis

        self._pool: aioredis.Redis = aioredis.from_url(  # type: ignore[assignment]
            redis_url,
            decode_responses=True,
            max_connections=5,
        )
        self._script = self._pool.register_script(_SLIDING_WINDOW_SCRIPT)
        # Expose for test compatibility (not used by Redis limiter)
        self.enabled = True
        self.force_enable_in_tests = False

    def reset(self) -> None:
        """No-op. Redis state is ephemeral and TTL-managed."""
        return

    async def __call__(self, request: Request) -> None:
        if not self.enabled:
            return

        if os.getenv("PYTEST_CURRENT_TEST") and not self.force_enable_in_tests:
            return

        client_ip = _resolve_client_ip(
            request, settings.RATE_LIMIT_TRUSTED_PROXIES
        )
        key = f"{self._prefix}:{client_ip}:{request.url.path}"

        try:
            result = await self._script(  # type: ignore[misc]
                keys=[key],
                args=[self.seconds * 1000, self.times, int(time.monotonic() * 1000)],
            )
        except Exception as exc:
            # Redis unreachable / command failed.  Fail open so a single
            # dead Redis box cannot lock every backend worker; the
            # per-worker in-memory limiter (used when REDIS_URL is unset)
            # is the operator's documented fallback behaviour.
            #
            # The URL and any embedded credentials are deliberately
            # omitted from the log; only the exception type and a generic
            # message are emitted.  The warning fires once per outage
            # transition; if a later request succeeds the flag is reset
            # so the next outage is logged again.
            if not self._unavailable_logged:
                self._unavailable_logged = True
                logger.warning(
                    "Redis rate limiting unavailable; failing open. "
                    "Subsequent failures during this outage will be "
                    "suppressed until rate limiting recovers.",
                    exc_info=exc,
                )
            return

        # Successful call: clear the outage flag so a *future* failure
        # is logged as a fresh transition.
        self._unavailable_logged = False

        allowed, ttl_ms = result
        if not allowed:
            retry_after = max(1, int(ttl_ms / 1000)) if ttl_ms else self.seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def _create_limiter(
    times: int,
    seconds: int,
    *,
    redis_url: str | None = None,
) -> InMemoryRateLimiter | RedisRateLimiter:
    """Factory that returns the correct limiter for the current environment.

    When *redis_url* is provided and non-empty a ``RedisRateLimiter`` is
    returned.  Otherwise the legacy ``InMemoryRateLimiter`` is used.
    """
    if redis_url:
        return RedisRateLimiter(times=times, seconds=seconds, redis_url=redis_url)
    return InMemoryRateLimiter(times=times, seconds=seconds)


def _resolve_redis_url() -> str | None:
    """Return the configured Redis URL from application Settings.

    Reads ``settings.REDIS_URL`` (one authoritative source); ``None`` and
    the empty string are both treated as "Redis is not configured", in
    which case the factory falls back to per-worker in-memory limiting.
    """
    url = settings.REDIS_URL
    if not url:
        return None
    return url


# Pre-configured rate limiters for security-sensitive endpoints
def _make_limiters() -> dict[str, InMemoryRateLimiter | RedisRateLimiter]:
    redis_url = _resolve_redis_url()
    return {
        "login": _create_limiter(times=20, seconds=60, redis_url=redis_url),
        "password_recovery": _create_limiter(times=10, seconds=60, redis_url=redis_url),
        "password_reset": _create_limiter(times=10, seconds=60, redis_url=redis_url),
        "signup": _create_limiter(times=20, seconds=60, redis_url=redis_url),
        "contact": _create_limiter(times=15, seconds=60, redis_url=redis_url),
        "comment": _create_limiter(times=30, seconds=60, redis_url=redis_url),
        "password_change": _create_limiter(times=10, seconds=60, redis_url=redis_url),
    }


_limiters = _make_limiters()
login_rate_limiter = _limiters["login"]
password_recovery_rate_limiter = _limiters["password_recovery"]
password_reset_rate_limiter = _limiters["password_reset"]
signup_rate_limiter = _limiters["signup"]
contact_rate_limiter = _limiters["contact"]
comment_rate_limiter = _limiters["comment"]
password_change_rate_limiter = _limiters["password_change"]
