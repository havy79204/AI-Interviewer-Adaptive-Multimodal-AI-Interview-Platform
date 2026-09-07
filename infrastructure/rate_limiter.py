from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque


class RateLimitExceeded(RuntimeError):
    """Raised when a caller exceeds the configured per-window limit."""


class RateLimiter:
    def allow(self, key: str) -> bool:
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    def __init__(self, limit: int = 10, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets[key]
        while bucket and (now - bucket[0]) > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise RateLimitExceeded(f"Rate limit exceeded for {key}")
        bucket.append(now)
        return True


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis_client, limit: int = 10, window_seconds: int = 60, namespace: str = "ratelimit") -> None:
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds
        self.namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self.namespace}:{key}"

    def allow(self, key: str) -> bool:
        redis_key = self._key(key)
        current = self.redis.incr(redis_key)
        if current == 1:
            self.redis.client.expire(redis_key, self.window_seconds)
        if current > self.limit:
            raise RateLimitExceeded(f"Rate limit exceeded for {key}")
        return True
