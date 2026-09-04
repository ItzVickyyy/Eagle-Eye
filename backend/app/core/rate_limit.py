import os
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """
    Lightweight, thread-safe in-memory rate limiter using sliding window counters per client IP.
    """

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

        # In general pytest runs, avoid false-positive rate limit blocks across suite runs
        # Dedicated rate-limiting tests can set force_enable_in_tests=True
        if os.getenv("PYTEST_CURRENT_TEST") and not self.force_enable_in_tests:
            return

        client_ip = request.client.host if request.client else "unknown"
        # Support test headers or forwarded headers if present
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        key = f"{client_ip}:{request.url.path}"
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


# Pre-configured rate limiters for security-sensitive endpoints
login_rate_limiter = InMemoryRateLimiter(times=20, seconds=60)
password_recovery_rate_limiter = InMemoryRateLimiter(times=10, seconds=60)
password_reset_rate_limiter = InMemoryRateLimiter(times=10, seconds=60)
signup_rate_limiter = InMemoryRateLimiter(times=20, seconds=60)
contact_rate_limiter = InMemoryRateLimiter(times=15, seconds=60)
comment_rate_limiter = InMemoryRateLimiter(times=30, seconds=60)
