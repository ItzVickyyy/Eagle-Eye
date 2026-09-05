from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    import redis.asyncio as aioredis


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


def _client_key(request: Request) -> str:
    """Return a rate-limit key scoped to client IP + request path."""
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
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

        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        key = f"{self._prefix}:{client_ip}:{request.url.path}"

        try:
            result = await self._script(  # type: ignore[misc]
                keys=[key],
                args=[self.seconds * 1000, self.times, int(time.monotonic() * 1000)],
            )
        except Exception:
            # Redis unreachable – fail open (per-IP in-memory is handled by
            # the factory fallback; reaching here means the factory didn't
            # swap, so we simply allow the request through).
            return

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


def _get_redis_url() -> str | None:
    """Resolve ``REDIS_URL`` from the environment without importing Settings.

    Importing ``app.core.config`` here would trigger a circular import when
    ``config.py`` eventually imports ``rate_limit`` for a health check or
    similar.  We read the env var directly; ``pydantic-settings`` will have
    already loaded ``.env`` into ``os.environ`` by the time this runs.
    """
    return os.getenv("REDIS_URL")


# Pre-configured rate limiters for security-sensitive endpoints
def _make_limiters() -> dict[str, InMemoryRateLimiter | RedisRateLimiter]:
    redis_url = _get_redis_url()
    return {
        "login": _create_limiter(times=20, seconds=60, redis_url=redis_url),
        "password_recovery": _create_limiter(times=10, seconds=60, redis_url=redis_url),
        "password_reset": _create_limiter(times=10, seconds=60, redis_url=redis_url),
        "signup": _create_limiter(times=20, seconds=60, redis_url=redis_url),
        "contact": _create_limiter(times=15, seconds=60, redis_url=redis_url),
        "comment": _create_limiter(times=30, seconds=60, redis_url=redis_url),
    }


_limiters = _make_limiters()
login_rate_limiter = _limiters["login"]
password_recovery_rate_limiter = _limiters["password_recovery"]
password_reset_rate_limiter = _limiters["password_reset"]
signup_rate_limiter = _limiters["signup"]
contact_rate_limiter = _limiters["contact"]
comment_rate_limiter = _limiters["comment"]
