from __future__ import annotations

import time
import secrets
from typing import Any


class RedisUnavailableError(RuntimeError):
    """Raised when Redis cannot be reached for a lock operation."""


class LockAcquisitionTimeout(TimeoutError):
    """Raised when a bounded lock acquisition wait expires."""


class DistributedLock:
    """Redis-backed lock for short-lived critical sections.

    Ownership semantics are explicit and TTL-bound to avoid stuck locks.
    """

    _RELEASE_SCRIPT = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    end
    return 0
    """
    _EXTEND_SCRIPT = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('pexpire', KEYS[1], ARGV[2])
    end
    return 0
    """

    def __init__(
        self,
        redis_client: Any,
        lock_name: str,
        ttl_seconds: int = 30,
        owner: str | None = None,
        acquire_timeout_seconds: float = 0.0,
        retry_interval_seconds: float = 0.05,
    ) -> None:
        self.redis = redis_client
        self.lock_name = lock_name
        self.ttl_seconds = ttl_seconds
        self.owner = owner or f"lock:{secrets.token_urlsafe(32)}"
        self.acquire_timeout_seconds = acquire_timeout_seconds
        self.retry_interval_seconds = retry_interval_seconds

    def acquire(self, timeout_seconds: float | None = None) -> bool:
        timeout = self.acquire_timeout_seconds if timeout_seconds is None else timeout_seconds
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                acquired = bool(self.redis.set(self.lock_name, self.owner, ex=self.ttl_seconds, nx=True))
            except Exception as exc:
                raise RedisUnavailableError(f"Redis lock operation failed for {self.lock_name}") from exc
            if acquired:
                return True
            if timeout <= 0 or time.monotonic() >= deadline:
                if timeout > 0:
                    raise LockAcquisitionTimeout(f"Timed out acquiring {self.lock_name}")
                return False
            time.sleep(min(self.retry_interval_seconds, max(0.0, deadline - time.monotonic())))

    def release(self) -> bool:
        try:
            return bool(self.redis.eval(self._RELEASE_SCRIPT, 1, self.lock_name, self.owner))
        except Exception as exc:
            raise RedisUnavailableError(f"Redis lock release failed for {self.lock_name}") from exc

    def extend(self, ttl_seconds: int | None = None) -> bool:
        ttl = ttl_seconds or self.ttl_seconds
        try:
            return bool(self.redis.eval(self._EXTEND_SCRIPT, 1, self.lock_name, self.owner, ttl * 1000))
        except Exception as exc:
            raise RedisUnavailableError(f"Redis lock extension failed for {self.lock_name}") from exc
