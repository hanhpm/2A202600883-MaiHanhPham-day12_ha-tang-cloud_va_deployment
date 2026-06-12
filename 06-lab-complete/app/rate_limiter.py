"""Sliding-window rate limiter with Redis storage and in-memory fallback."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings

try:
    import redis
except ImportError:  # pragma: no cover - exercised only before dependencies are installed
    redis = None


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._memory_windows: dict[str, deque] = defaultdict(deque)
        self._redis = None
        if redis and settings.redis_url:
            try:
                self._redis = redis.Redis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                    decode_responses=True,
                )
                self._redis.ping()
            except redis.RedisError:
                self._redis = None

    @property
    def backend_name(self) -> str:
        return "redis" if self._redis else "memory"

    def ping(self) -> bool:
        if not self._redis:
            return True
        try:
            return bool(self._redis.ping())
        except redis.RedisError:
            return False

    def check(self, key: str) -> dict:
        if self._redis:
            return self._check_redis(key)
        return self._check_memory(key)

    def _check_redis(self, key: str) -> dict:
        now_ms = int(time.time() * 1000)
        window_start = now_ms - self.window_seconds * 1000
        redis_key = f"rate:{key}"
        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            _, current = pipe.execute()
            if current >= self.max_requests:
                raise self._limit_error(0)
            pipe = self._redis.pipeline()
            pipe.zadd(redis_key, {str(now_ms): now_ms})
            pipe.expire(redis_key, self.window_seconds)
            pipe.execute()
            return {"limit": self.max_requests, "remaining": self.max_requests - current - 1}
        except redis.RedisError:
            self._redis = None
            return self._check_memory(key)

    def _check_memory(self, key: str) -> dict:
        now = time.time()
        window = self._memory_windows[key]
        while window and window[0] < now - self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            retry_after = int(window[0] + self.window_seconds - now) + 1
            raise self._limit_error(retry_after)
        window.append(now)
        return {"limit": self.max_requests, "remaining": self.max_requests - len(window)}

    def _limit_error(self, retry_after: int) -> HTTPException:
        return HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {self.max_requests} req/min",
            headers={
                "X-RateLimit-Limit": str(self.max_requests),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(max(retry_after, 1)),
            },
        )


rate_limiter = RateLimiter(max_requests=settings.rate_limit_per_minute)
